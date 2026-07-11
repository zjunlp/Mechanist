---
name: auto-iteration-loop
description: Autonomous research review loop that consumes /auto-verify's four-state output (PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS / deferred) and routes each claim to the right back-edge — brief audit, two-phase FAIL handling (variant-integrity fix then optional claim-stage re-entry), main-experiment-script fix, or variant-only fix — under a unified iteration budget. Configure the reviewer LLM via llm-chat MCP server or environment variables. Trigger with "auto review loop llm" or "llm review".
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, WebSearch, WebFetch, Agent, AskUserQuestion, Skill, mcp__llm-chat__chat
---

# Auto Iteration Loop: Adversarial Review with Bounded Back-Edges

Autonomously iterate over `/auto-verify`'s per-claim verdicts: review → implement fixes (variant-integrity, main-experiment-script, or claim-stage rewrite) → re-review, until the external reviewer gives a positive assessment with all FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS claims resolved, or the iteration budget is exhausted.

## Context: $ARGUMENTS

## Constants

- **MAX_ITERATIONS = 6** — Hard upper bound on total back-edge actions across the whole loop. **Each of the following consumes 1 iteration**, regardless of which Phase A→E cycle they fall in:
  - ① variant-only fix → re-run `/auto-verify <claim-id> — resume: true`
  - ② main-experiment-script / `EXPERIMENT_PLAN.md` fix → re-run `/auto-experiment` (optionally followed by `/auto-verify` chain)
  - ③ claim-stage re-entry → rewrite claim (full `/auto-claim` invocation OR lightweight in-loop rewrite) → re-run downstream stages

  Pure reviewer cycles that change nothing on disk (no new experiments, no claim changes) do **not** consume iterations. PASS-claim consistency checks and deferred-claim recording do not consume iterations. **New claims produced by ③ inherit the same budget — they do not get a fresh `MAX_ITERATIONS` of their own.** Override via `MAX_ITERATIONS:` arg from `agents/iteration.md`.

  > **Resource-Fidelity invariant (all back-edges).** If `refine-logs/FINAL_PROPOSAL.md` / `refine-logs/EXPERIMENT_PLAN.md` carry a `resource_fidelity: strict` marker (the reproduction combination — `behavior-source:given` + `mechanism:given`), every back-edge MUST preserve it: when editing `EXPERIMENT_PLAN.md` (type ②) or any claim rewrite (type ③), keep the top-of-file `resource_fidelity:` line **verbatim** — never drop, comment out, or change it. Dropping the marker silently **disables the harness**, re-opening the door to smaller-model swaps and data subsetting the harness exists to prevent. For type-③ full re-entry, detect the original run's axes from `idea-stage/IDEA_REPORT.md`'s `**Behavior-source**:` / `**Mechanism**:` headers (or directly from the `resource_fidelity: strict` marker) and pass **both** `behavior_source` and `mechanism` into the queued `auto-claim` call so a reproduction-combo re-entry stays `given`+`given` (the new run re-stamps the `resource_fidelity: strict` marker automatically — it is marker-driven, not a flag).

- **MAX_CLAIM_REENTRIES = 2** — Sub-budget within `MAX_ITERATIONS` for action type ③ (claim-stage re-entry). Prevents the failure mode where the reviewer keeps asking "rewrite the claim" without anyone actually fixing the experiments behind it. When `claim_reentries_consumed >= MAX_CLAIM_REENTRIES`, the loop refuses further ③ actions even if iterations remain — at that point the only legal back-edges are ① and ②, and if those are also exhausted the loop terminates and writes the final report.

- **TARGET_SCORE = 6** — Stop when reviewer score >= this AND verdict matches a `POSITIVE_VERDICT_TERMS` entry AND no claim is still in FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS (three-dimensional STOP rule — see Phase B).

- **POSITIVE_VERDICT_TERMS = [ready, almost]** — Case-insensitive substrings that count the verdict as positive. Phase B canonicalizes the reviewer's free-form verdict to one of `{ready, almost, not ready}` before this check, so any reviewer-supplied synonym (e.g., `accept`, `sufficient`, `good enough`) must be mapped to `ready` / `almost` by Phase B's parser — see Phase B's STOP rule for the canonical check.

- **REVIEW_DOC = `review-stage/AUTO_REVIEW.md`** — Per-iteration append-only audit log (fall back to `./AUTO_REVIEW.md` for legacy projects). This is the raw audit trail; the narrative report is `FINAL_REPORT_DOC` below.

- **REVIEWER_MEMORY_DOC = `review-stage/REVIEWER_MEMORY.md`** — Reviewer's persistent suspicion log across iterations. Append-only: each iteration's Phase B.5 adds a section under `## Iteration N`, never deletes prior iterations (audit trail). Phase A of iteration 2+ prepends the full file to the reviewer prompt so the reviewer can check whether prior-iteration suspicions were genuinely addressed or sidestepped. Counters the failure mode where Claude curates a comfortable subset of context for the reviewer each iteration.

- **FINAL_REPORT_DOC = `review-stage/AUTO_ITERATION_FINAL_REPORT.md`** — Narrative final report written **once** in Termination (after the loop ends for any reason). Organized per-claim by their original `/auto-verify` category (PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS / DEFERRED), with the per-claim iteration journey, experiment/script diffs, and any claim rewrites laid out inside each claim's section. Distinct from `REVIEW_DOC` (which is the chronological audit log). See "Final Report" section below for the full template.

- **GPU_ID = `auto`** — GPU device(s) to pin every Phase-C `/run-experiment` dispatch to. `auto` lets the launcher / environment decide (no extra export). A single id (`0`) or comma-list (`4,5,6,7`) causes this skill to **pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional arg to every `/run-experiment` invocation** (the run-experiment skill exports it internally; do not treat as a shell prefix), and record the effective `CUDA_VISIBLE_DEVICES` in each run's `run.sh`. Forwarded from `agents/iteration.md`'s `gpu_id:` arg (which the orchestrator forwards from `/auto`'s `GPU_ID`).

- **RESUME = false** — When `true`, read `review-stage/REVIEW_STATE.json` and pick up from `iterations_consumed + 1` instead of starting fresh. Append new iterations to the existing `AUTO_REVIEW.md` rather than overwriting it. Iteration budget and claim-reentry sub-budget are **inherited** across resume — they are never reset. If `REVIEW_STATE.json` already shows `status: completed` (positive verdict, iterations exhausted, or claim-reentry budget exhausted), return immediately without running another iteration. If `status: awaiting_upstream`, the orchestrator (see `auto/SKILL.md`) is expected to run the pending upstream calls first, then resume this loop. Default `false` = always start fresh and overwrite prior review state. Resume never deletes pre-existing review state. Schema fields read here: `iterations_consumed`, `claim_reentries_consumed`, `status`, `last_verdict`, `last_score` — see "State Persistence" below.


## Reviewer LLM Configuration (mandatory, read first)

This skill calls an external LLM reviewer. **Never hardcode a model name and never read the reviewer model from `task.md` / project READMEs / source comments.** Project-level files may list available API keys for unrelated purposes (e.g., LLM-as-judge inside experiment code); those are *not* the reviewer config.

Resolve `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` strictly in this priority order before any reviewer call:

1. **Project MCP config** — `${PROJECT_ROOT}/.mcp.json`, field `mcpServers["llm-chat"].env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}`.
2. **User MCP config** — `~/.claude/settings.json`, same field.
3. **Shell environment** — `$LLM_MODEL`, `$LLM_BASE_URL`, `$LLM_API_KEY`.

### Pre-flight check (run before Phase A of every iteration, mandatory)

```bash
LLM_MODEL_SRC=""
if [ -f .mcp.json ] && jq -e '.mcpServers["llm-chat"].env.LLM_MODEL' .mcp.json >/dev/null 2>&1 ; then
  export LLM_MODEL=$(jq -r '.mcpServers["llm-chat"].env.LLM_MODEL' .mcp.json)
  export LLM_BASE_URL=$(jq -r '.mcpServers["llm-chat"].env.LLM_BASE_URL' .mcp.json)
  export LLM_API_KEY=$(jq -r '.mcpServers["llm-chat"].env.LLM_API_KEY' .mcp.json)
  LLM_MODEL_SRC="project .mcp.json"
elif [ -f ~/.claude/settings.json ] && jq -e '.mcpServers["llm-chat"].env.LLM_MODEL' ~/.claude/settings.json >/dev/null 2>&1 ; then
  export LLM_MODEL=$(jq -r '.mcpServers["llm-chat"].env.LLM_MODEL' ~/.claude/settings.json)
  export LLM_BASE_URL=$(jq -r '.mcpServers["llm-chat"].env.LLM_BASE_URL' ~/.claude/settings.json)
  export LLM_API_KEY=$(jq -r '.mcpServers["llm-chat"].env.LLM_API_KEY' ~/.claude/settings.json)
  LLM_MODEL_SRC="user ~/.claude/settings.json"
elif [ -n "$LLM_MODEL" ] && [ -n "$LLM_BASE_URL" ] && [ -n "$LLM_API_KEY" ] ; then
  LLM_MODEL_SRC="shell env"
fi
echo "[reviewer-config] LLM_MODEL=$LLM_MODEL  LLM_BASE_URL=$LLM_BASE_URL  source=$LLM_MODEL_SRC"
```

**Hard-fail rule**: If `LLM_MODEL` is empty after this resolution (none of the three sources provides it), the skill MUST abort with:
> "Reviewer model not configured. Add `mcpServers.llm-chat.env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}` to `.mcp.json` (project) or `~/.claude/settings.json` (user)."

Do not guess a default. Do not fall back to a model name read from `task.md` or any other project file.

> The earlier `## LLM Configuration` example block in older versions of this skill (which duplicated the same `llm-chat` MCP setup) has been removed — the authoritative config resolution is the priority order above. For a worked `.mcp.json` example, see `mcp-servers/llm-chat/` in the project repo.

## API Call Method

**Primary: MCP Tool**

```
mcp__llm-chat__chat:
  prompt: |
    [Review prompt content]
  model: "${LLM_MODEL}"   # resolved per "Reviewer LLM Configuration" priority order above — never hardcode
  system: "You are a senior ML reviewer..."
```

**Fallback: curl**

```bash
curl -s "${LLM_BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LLM_API_KEY}" \
  -d '{
    "model": "${LLM_MODEL}",
    "messages": [
      {"role": "system", "content": "You are a senior ML reviewer..."},
      {"role": "user", "content": "[review prompt]"}
    ],
    "max_tokens": 4096
  }'
```

## State Persistence (Compact Recovery)

Persist state to `review-stage/REVIEW_STATE.json` after each iteration (i.e., every Phase E):

```json
{
  "iterations_consumed": 2,
  "claim_reentries_consumed": 1,
  "status": "in_progress",
  "last_score": 5.0,
  "last_verdict": "not ready",
  "consecutive_noop_count": 0,
  "iteration_breakdown": [
    {"i": 1, "type": "variant_fix",       "target_claims": ["C1"], "produced_claims": []},
    {"i": 2, "type": "claim_reentry",     "target_claims": ["C2"], "produced_claims": ["C2_v2"]}
  ],
  "claim_stage_reentries": ["C2"],
  "pending_upstream_calls": [],
  "runs_total": 5,
  "gpu_hours_total": 12.4,
  "thread_id": "th_01ABC123def456",
  "timestamp": "2026-03-15T10:00:00"
}
```

- `iterations_consumed` is the cumulative count of back-edge actions (types ①/②/③) since iteration 1 — what's compared against `MAX_ITERATIONS`.
- `claim_reentries_consumed` is the cumulative count of type ③ actions only — what's compared against `MAX_CLAIM_REENTRIES`.
- `iteration_breakdown` records each iteration's action type, the claim(s) it targeted, and any new claim ids produced by claim-stage re-entry (so the final report can attribute new claims to the right ancestor).
- `claim_stage_reentries` is the flat list of claim ids that triggered ③ — surfaced to `agents/iteration.md` so the orchestrator can record which original claims got rewritten in the Ledger's `journey_summary.iteration` line and `open_items[]`.
- `pending_upstream_calls` is non-empty only when `status = awaiting_upstream`: a list of `{skill, args}` calls the orchestrator must execute before resuming this loop.
- `runs_total` / `gpu_hours_total` are cumulative across all iterations; they monotonically increase and are the canonical budget source `agents/iteration.md` reports back to the orchestrator.

**Field consumer map** (so future maintainers know which fields are external API vs internal state):

| Field | Written by | Read by | Notes |
|---|---|---|---|
| `iterations_consumed` | this skill | `auto/SKILL.md` (inherits on resume), `agents/iteration.md` | external; compared against `MAX_ITERATIONS` |
| `claim_reentries_consumed` | this skill | `auto/SKILL.md` (inherits on resume), `agents/iteration.md` | external; compared against `MAX_CLAIM_REENTRIES` |
| `status` | this skill | `auto/SKILL.md` resume check, `agents/iteration.md` | external; values `in_progress` / `awaiting_upstream` / `completed` |
| `last_verdict` | this skill | `auto/SKILL.md` resume check | external; matched against `POSITIVE_VERDICT_TERMS` |
| `last_score` | this skill | `auto/SKILL.md` resume check | external; numeric 1–10 |
| `iteration_breakdown` | this skill | this skill (Termination, final-report assembly); `agents/iteration.md` summary | external; ordered list, append-only |
| `claim_stage_reentries` | this skill | `auto/SKILL.md` (for `CLAIMS_LEDGER.md` `journey_summary` + `open_items[]`), Termination | external |
| `pending_upstream_calls` | this skill | `auto/SKILL.md` orchestrator only | external; consumed (cleared) by orchestrator before resuming this skill |
| `runs_total` | this skill | `agents/iteration.md` summary, `auto/SKILL.md` budget tracking | external |
| `gpu_hours_total` | this skill | `agents/iteration.md` summary, `auto/SKILL.md` budget tracking | external |
| `timestamp` | this skill | this skill's resume gate (24h staleness check — see Workflow Initialization) | internal — drives the stale-state cutoff; archive instead of delete on age-out |
| `thread_id` | this skill (Phase A iteration 1) | this skill (Phase A iteration 2+) | **internal** — opaque conversation handle returned by `mcp__llm-chat__chat` after iteration 1's call. Phase A iteration 2+ passes it back to the MCP server so the reviewer keeps the same conversation thread (cheaper context + better cross-iteration coherence than re-pasting summaries). Absent / `null` when the iteration-1 reviewer call used the curl fallback (curl doesn't return a thread handle), or when the MCP server rejected thread continuation — in either case Phase A iteration 2+ silently falls back to the paste-summary path. |

**Write this file at the end of every Phase E** (after documenting the iteration).

**On completion**, set `"status": "completed"` and continue to Termination (which generates `FINAL_REPORT_DOC`).

**On back-edge handoff to orchestrator** (Phase C decided a fix requires upstream skills the iteration loop cannot run inline — e.g., full `/auto-claim` re-invocation), set `"status": "awaiting_upstream"`, populate `pending_upstream_calls`, and return. The orchestrator runs them, then resumes this skill with `RESUME=true`.

## Workflow

### Upstream artifacts pre-flight (mandatory, run first)

This skill **iterates over existing artifacts** produced by upstream stages — it does not generate them from scratch. `$ARGUMENTS` (the optional research-direction string) is treated as reviewer context only, never as a starting point.

Before doing anything else, verify the project root contains **at least one** of:

- `idea-stage/IDEA_REPORT.md`
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_RESULTS.md`
- `verify/VERIFY_REPORT.md`

If **none** of these exist, abort with:

```
[pre-flight] no upstream artifacts found at idea-stage/ refine-logs/ verify/.
            /auto-iteration-loop reviews existing work — it does not start from a topic.
            Run /auto (or at minimum /auto-claim then /auto-experiment) first.
            Aborting.
```

Do not invoke the reviewer, do not write `review-stage/AUTO_REVIEW.md`. Abort cleanly.

#### Build five disjoint claim buckets from `verify/VERIFY_REPORT.md`

If `verify/VERIFY_REPORT.md` is present, read it once at the top of every iteration alongside `verify/INTEGRITY_AUDIT.md` and build **five disjoint claim buckets** that drive Phase A's reviewer prompt. The five states mirror `/auto-verify`'s terminal states exactly (see `auto-verify/SKILL.md` Phase 11 column glossary):

- **`verify_passed`** — claim ids whose state is `PASS`. Main-experiment verdict is robust under swaps. Routing: **brief consistency check only** (see below). No experiments fired.
- **`verify_failed`** — claim ids whose state is `FAIL` (`robustness < ROBUSTNESS_THRESHOLD` over enough eligible variants; the main experiment was fragile). Routing: **two-phase** (variant-integrity fix → optional claim-stage re-entry).
- **`verify_inconclusive`** — claim ids whose state is `INCONCLUSIVE` (Phase 2 main-experiment-integrity FAIL; variants never ran, or were policy-skipped under audit-only mode — semantics identical). Routing: **fix the main experiment only** (`EXPERIMENT_PLAN.md` step or main-experiment script).
- **`verify_zero_eligible_variants`** — claim ids whose state is `ZERO_ELIGIBLE_VARIANTS` (Phase 2 the main experiment was clean, but every Phase 9 variant FAILed integrity). Routing: **fix variant scripts only** (do not touch the main experiment).
- **`verify_integrity_only`** — claim ids whose state is `INTEGRITY_ONLY` (Phase 2 pass/warn, Stage 2 intentionally skipped). Two producers, distinguished per-claim by `stage2_skip_reason` in `ROBUSTNESS.md`: `swap_variants_false` (global audit-only mode) or `max_verify_claims_cap` (this claim was admitted by Stage 1 but not the top-K picked at Phase 3 step 0). Routing: **no back-edge action** — record in Open Items with per-`stage2_skip_reason` upgrade suggestion. See per-bucket contract below.

Plus the orthogonal (legacy):

- **`deferred_claims`** — **Legacy bucket, always empty under the current architecture.** Verify no longer cuts claims before audit; claims that would have been cut by `MAX_VERIFY_CLAIMS` in the old design now land in `verify_integrity_only` with `stage2_skip_reason: max_verify_claims_cap`. Retained as an empty placeholder for backward compatibility with older `VERIFY_REPORT.md` files. New runs never populate it.

The five state buckets are disjoint by construction (a claim has exactly one `/auto-verify` state); the legacy `deferred_claims` bucket is empty in new runs, so no overlap concerns arise. Under `SWAP_VARIANTS=false`, only two buckets can be non-empty: `verify_inconclusive` and `verify_integrity_only` (with `stage2_skip_reason: swap_variants_false`) — `verify_passed` / `verify_failed` / `verify_zero_eligible_variants` all require Phase 9 to have run and are always empty.

#### Per-bucket routing contract

**`verify_passed` — brief consistency check.** For each claim id in `verify_passed`, the reviewer does narrative + numeric consistency only:
- Does the claim wording match the supporting numbers in `refine-logs/EXPERIMENT_RESULTS.md` and `verify/<claim_dir>/ROBUSTNESS.md`?
- Are there caveats (main-experiment-WARN tag) that need to surface in the final paper but not in the iteration loop's actions?

Record one line per claim under the iteration's `### Verify-Passed Claims (brief audit)` section in `AUTO_REVIEW.md`. **Does NOT consume an iteration** — the reviewer's consistency check is part of the same Phase A reviewer call.

**`verify_failed` — two-phase routing.** For each claim id in `verify_failed`:
- **Phase 1 — Variant integrity check.** Read this claim's `verify/<claim_dir>/variant_audit/{EXPERIMENT,MECHANISM}_AUDIT.md` and each surviving variant's `verdict.json.integrity_breakdown`. If any surviving variant had a WARN/FAIL that could have biased the consistency check, that's the lead — fix that variant's script (deletion + targeted re-run is fine; full sweep is not required) and re-invoke `/auto-verify <claim-id> — resume: true`. Consumes **1 iteration** (type ①).
- **Phase 2 — Claim-stage re-entry.** If Phase 1 was clean (or Phase 1 was already executed in a prior iteration and the claim still came back FAIL with clean variants), the divergence is real and the claim itself needs work. Choose one of:
  - **Lightweight in-loop rewrite** (preferred when the reviewer has a concrete narrower claim in mind): write the new claim text directly into a `claim_rewrite:` block in `AUTO_REVIEW.md`, then chain `/auto-experiment` + `/auto-verify` targeted to the rewritten claim only. No `/auto-claim` invocation.
  - **Full claim-stage re-entry**: set `status = awaiting_upstream` and queue `pending_upstream_calls = [{skill: "auto-claim", args: {focus: "<claim-id> — verify-failed context: ...", behavior_source: "<inherit original>", mechanism: "<inherit original>"}}, {skill: "auto-experiment", args: {target_claims: ["<new-id>"]}}, {skill: "auto-verify", args: {target_claims: ["<new-id>"]}}]`. Carry the original run's `behavior_source` + `mechanism` into the `auto-claim` args so a reproduction-combo (`given`+`given`) re-entry re-stamps `resource_fidelity: strict` automatically (marker-driven — per the invariant above). The orchestrator runs them and resumes this loop with the new claim's `/auto-verify` result.

  Either form consumes **1 iteration** (type ③) AND **1 claim-reentry sub-budget**. The new claim id (when produced) is recorded in `iteration_breakdown[i].produced_claims` so the final report attributes it to the original claim's section, not a fresh top-level entry.

  Crucially: when `claim_reentries_consumed >= MAX_CLAIM_REENTRIES`, Phase 2 is **not allowed** even if the reviewer requests it — record the request, decline it in the iteration's writeup, and either return to Phase 1 (if there are still dirty variants left to fix) or terminate with the claim still in FAIL state (it gets surfaced in the final report's `Open Items` section).

  The reviewer may NOT choose "narrow scope" or "pivot" as standalone local actions — those are subsumed by Phase 2's claim rewrite.

**`verify_inconclusive` — main-experiment-only fix.** For each claim id in `verify_inconclusive`:
- Read this claim's `verify/<claim_dir>/main_experiment_audit/{EXPERIMENT,MECHANISM}_AUDIT.md` to identify which sub-audit FAILed (the `ROBUSTNESS.md` stub's `inconclusive_reason` field summarizes this).
- Fix the failing main-experiment surface: edit the relevant step in `refine-logs/EXPERIMENT_PLAN.md` (**preserving the top-of-file `resource_fidelity:` marker verbatim** — see the Resource-Fidelity invariant above), modify the main-experiment script (`experiments/<name>/`), then re-invoke `/auto-experiment` (with `target_claims: [<id>]` so only this claim's runs re-execute, if supported by the upstream skill) followed by `/auto-verify`. Consumes **1 iteration** (type ②).
- The reviewer is **not** allowed to "narrow scope", "pivot", or rewrite the claim for an INCONCLUSIVE — the main-experiment methodology is what's broken, not the claim's framing. To rewrite the claim, the claim must first become FAIL (i.e., the main experiment must be fixed so a robustness verdict is computable).
- **Per-claim ② cap (mirror of `MAX_CLAIM_REENTRIES` for ③).** A stubborn INCONCLUSIVE main experiment must not monopolise the shared `MAX_ITERATIONS` budget and starve other claims. Count this claim's prior type-② actions in `iteration_breakdown` (no separate counter needed). **If it has already had 2 ② attempts and is still INCONCLUSIVE, do not attempt a 3rd**: record the reviewer's request, decline it in the iteration writeup, and leave the claim INCONCLUSIVE in the final report's `Open Items` (`requires manual main-experiment repair`). This frees the remaining budget for other claims; if no other claim has an actionable fix, terminate. (The cap is on iteration-loop ② attempts — at most 2 — not on the original original /auto-experiment run.)

**`verify_zero_eligible_variants` — variant-only fix.** For each claim id in `verify_zero_eligible_variants`:
- Read this claim's `verify/<claim_dir>/variant_audit/{EXPERIMENT,MECHANISM}_AUDIT.md` and the `zero_eligible_reason` field in `ROBUSTNESS.md`.
- Fix each failing variant's script (variant `eval.py`, mechanism harness, etc.), delete the failed variant directories under `verify/<claim_dir>/variants/`, then re-invoke `/auto-verify <claim-id> — resume: true` standalone (Phase 1's argument parser and Phase 2's main-experiment audit will skip on resume; only variant phases re-execute). Consumes **1 iteration** (type ①, same as FAIL Phase 1).
- Do NOT invoke `/auto-experiment` — the the main experiment already passed Phase 2; rerunning it wastes compute and risks main-experiment drift.

**`verify_integrity_only` — no-action-with-upgrade-suggestion contract.** For each claim id in `verify_integrity_only` the reviewer must NOT propose any back-edge action — main-experiment integrity was validated at Phase 2 (`main_experiment_integrity ∈ {pass, warn}` in `ROBUSTNESS.md`) and the swap stress test was intentionally skipped. Read the per-claim `stage2_skip_reason` field to pick the right upgrade string:

- `stage2_skip_reason: swap_variants_false` (global audit-only mode) → upgrade suggestion: `to stress-test under method/dataset/model swaps: /auto-verify <id> — swap-variants: true, resume: true (Phase 2 audits reused via RESUME; only Stages 2–3 run)`
- `stage2_skip_reason: max_verify_claims_cap` (Stage 1 admitted but not top-K picked) → upgrade suggestion: `to stress-test this admitted claim: /auto-verify <id> — resume: true (single-claim mode; Phase 2 audit reused via RESUME; only Stages 2–3 run for this claim)`

Three requirements: (a) record each claim under `### Open Items — Unverified Under Swaps` in `AUTO_REVIEW.md` with its `stage2_skip_reason` and the matching upgrade suggestion; (b) when `main_experiment_integrity: warn`, surface `warn_source` on the same line so the paper text can carry the caveat; (c) exclude from score-weighting reasoning — neither a positive nor a negative signal, just unfinished. The iteration agent's final return message surfaces this list to the orchestrator so it lands in `CLAIMS_LEDGER.md`'s `open_items[]`. **Does NOT consume an iteration.**

**`deferred_claims` — legacy no-op.** New verify runs never populate this bucket (cap-cut claims land in `verify_integrity_only` with `stage2_skip_reason: max_verify_claims_cap`). On a legacy `VERIFY_REPORT.md` that still carries a `## Deferred Claims` section, treat each id under the same no-action contract as `verify_integrity_only` (record under `### Open Items — Unverified Under Swaps` with `requires standalone /auto-verify <id> before this claim can enter the iteration loop`; exclude from score-weighting). **Does NOT consume an iteration.**

#### Phase A reviewer prompt — explicit bucket list

When constructing Phase A's reviewer prompt, include all five state buckets explicitly so the reviewer can address them separately. Empty buckets are stated as `none`, not omitted (the reviewer needs to know "no claims FAILed" is different from "I forgot to tell you"):

```
verify_passed:                  [<comma-separated claim ids, or "none">]   # brief consistency check only, no experiment action
verify_failed:                  [<comma-separated claim ids, or "none">]   # two-phase routing — see contract
verify_inconclusive:            [<comma-separated claim ids, or "none">]   # main-experiment-only fix
verify_zero_eligible_variants:  [<comma-separated claim ids, or "none">]   # variant-only fix
verify_integrity_only:          [<comma-separated claim ids, or "none">]   # NO back-edge; record in Open Items with stage2_skip_reason-dispatched upgrade suggestion
```

`deferred_claims` is a legacy empty bucket in new runs and is not part of the reviewer prompt.

#### Flexibility note on upstream back-edges

When this loop triggers a back-edge (variant re-run, main-experiment re-run, or claim-stage re-entry), the iteration agent **may** choose to run a lightweight subset rather than the full upstream skill:
- For `/auto-experiment`: only the runs corresponding to the target claim need re-execute. If `target_claims` is honored by the upstream skill, pass it; if not, the lightweight path is to manually re-run the specific experiment scripts and update the corresponding `runs/iteration_round_<N>/<run-id>/` directory.
- For `/auto-verify`: pass `— resume: true` so completed phases skip. (Iteration-loop invocations are always single-claim — `/auto-verify <claim-id>` — so the claim scoping is already implicit.)
- For `/auto-claim`: lightweight path is to write the rewritten claim text directly into `AUTO_REVIEW.md` and bypass the `/auto-claim` call entirely.

Each lightweight or full variant of these actions consumes **the same** iteration count (and the same claim-reentry sub-budget when applicable). The agent is given the choice for compute efficiency, not for budget gaming.

### Initialization

0. **Run the Pre-flight check** in the "Reviewer LLM Configuration" section above. Abort with the hard-fail message if `LLM_MODEL` cannot be resolved. Log the resolved values and source.
1. **Check `review-stage/REVIEW_STATE.json`** for recovery *(fall back to `./REVIEW_STATE.json` if not found — legacy path)*
2. **Resume gate (only when `RESUME = true`)**. Read fields from the schema documented under "State Persistence" above (`iterations_consumed`, `claim_reentries_consumed`, `status`, `last_verdict`, `last_score`, `timestamp`):
   - If `REVIEW_STATE.json` is missing or empty → start fresh (`iterations_consumed = 0`, `claim_reentries_consumed = 0`), log `[resume] no prior state — starting fresh`.
   - **Staleness check (first, before any other branch — but exempt `awaiting_upstream`)**: parse `timestamp` as ISO 8601. **Skip this check entirely when `status == "awaiting_upstream"`** — that is a *deliberate, live handoff* waiting on orchestrator-run upstream calls (a type-③ claim re-entry's `/auto-claim → /auto-experiment → /auto-verify`, which routinely exceeds 24h on GPU experiments). Ageing it out would discard the just-produced upstream results and reset the inherited budget counters, orphaning live work; the long elapsed time is expected and the upstream calls produced *fresh* results, so the drift rationale does not apply. For any **other** status, if `now - timestamp > 24h` (86400 seconds), the prior state is too old to safely resume — log `[resume] state older than 24h (timestamp=<ts>, age=<H>h) — treating as stale, ignoring REVIEW_STATE.json and starting fresh`, archive the stale file as `REVIEW_STATE.<ts>.stale.json` (so the audit trail survives — don't delete it), and proceed as if `RESUME=false`. Rationale: beyond a day the codebase, results files, and reviewer model versions have likely drifted enough that "picking up from iteration N" would conflate stale context with fresh work — a concern that applies to an interrupted `in_progress` run, not to a deliberate `awaiting_upstream` handoff. If the `timestamp` field is absent (legacy state files), skip the staleness check and continue to the branches below — the caller accepts the risk.
   - If `status == "completed"` AND `last_verdict` matches a `POSITIVE_VERDICT_TERMS` entry AND `last_score >= TARGET_SCORE` → log `[resume] prior run already satisfied target (score=<last_score>, verdict=<last_verdict>) — returning without invoking reviewer` and return immediately with the existing state. (Termination should already have produced `FINAL_REPORT_DOC` in this case; if missing, re-run Termination's report-assembly step before returning.)
   - Else if `status == "completed"` AND `iterations_consumed >= MAX_ITERATIONS` → log `[resume] prior run exhausted MAX_ITERATIONS (iterations_consumed=<n>) — returning without invoking reviewer` and return.
   - Else if `status == "completed"` AND `claim_reentries_consumed >= MAX_CLAIM_REENTRIES` AND the only remaining unresolved claims would require action type ③ → log `[resume] prior run exhausted MAX_CLAIM_REENTRIES — returning without invoking reviewer` and return.
   - Else if `status == "awaiting_upstream"` → the orchestrator should have run `pending_upstream_calls` before resuming. Verify they completed (all expected output artifacts present on disk per the upstream skills' own contracts). If they did, clear `pending_upstream_calls`, flip `status` to `"in_progress"`, and continue into Phase A of the next iteration with `iterations_consumed` and `claim_reentries_consumed` already incremented (Phase C of the prior iteration incremented them when it queued the upstream calls). If they did not, abort with `[resume] awaiting_upstream but pending_upstream_calls outputs missing — orchestrator did not complete upstream work; aborting`. Do not silently retry — the orchestrator failure must be visible.
   - Else if `status == "in_progress"` AND `iterations_consumed >= MAX_ITERATIONS` → no iterations left; flip `status` to `"completed"`, log `[resume] in-progress at MAX_ITERATIONS — closing out without new iteration`, run Termination, and return.
   - Otherwise (`status == "in_progress"` AND `iterations_consumed < MAX_ITERATIONS`) → the next iteration's display number is `iterations_consumed + 1` (this is a working value for logs / Phase E heading only — it is **never** persisted; the only persistent counter is `iterations_consumed`, which Phase C increments at its **end** after a real ①/②/③ action). Open `AUTO_REVIEW.md` in append mode and continue. Log `[resume] picking up from iteration <iterations_consumed+1>/<MAX_ITERATIONS> (claim-reentry sub-budget: <claim_reentries_consumed>/<MAX_CLAIM_REENTRIES>)`.
3. Read project context and prior reviews
4. Initialize iteration counter (skip if step 2 already set it)

### Loop (up to MAX_ITERATIONS)

Each cycle below is one Phase A→E iteration. The iteration counter (`iterations_consumed`) is incremented at the **end** of Phase C, only if Phase C actually queued or executed a back-edge action of type ① / ② / ③. A pure-review iteration whose only action is type ⓪ (narrative-only) or has no action at all does not consume budget. **Stall guard against ⓪-only spin.** Because ⓪ is free (it does not consume budget and runs no experiment), a reviewer that keeps proposing narrative-only fixes for a still-unresolved weakness would loop forever — burning a reviewer call each round while neither the STOP rule (score below target) nor the budget exit (`iterations_consumed` frozen) ever fires. The `consecutive_noop_count` field in `REVIEW_STATE.json` closes this: at Phase E, **increment** it when this iteration was ⓪-only (or had no action) **and** `last_score` + `last_verdict` are unchanged from the prior persisted state; **reset it to 0** whenever a real ①/②/③ action ran **or** the score/verdict changed. When it reaches **2** (two consecutive non-converging no-op iterations), the loop is stalled on the reviewer side — terminate it (see Phase B's STOP conditions). The common legitimate case for a ⓪-only iteration is the **final** one that confirms a positive verdict after a real ①/②/③ in the prior iteration — that single ⓪ is fine; only an unchanged-score *repeat* trips the guard.

#### Phase A: Review

**Iteration 1** uses the prompt shape below (no Reviewer Memory yet — file is created at the end of iteration 1 by Phase B.5). The budget line at the top of the prompt reads `0/<MAX> used` for both budgets on iteration 1; that is correct and expected, not an error.
**Iteration 2+** prepends the contents of `REVIEWER_MEMORY_DOC` plus a "Previous Review Summary" block before the body — see "Prompt Template for Iteration 2+" near the end of this file for the full shape. The memory block is **mandatory** from iteration 2 onward and is what gives this loop adversarial continuity across iterations.

The reviewer prompt must include the five state buckets explicitly per the contract in "Build five disjoint claim buckets" above. The reviewer is told which routing options are available per bucket and which are forbidden (e.g., no claim rewrite for INCONCLUSIVE; no action for INTEGRITY_ONLY).

**If MCP available:**
```
mcp__llm-chat__chat:
  system: "You are a senior ML reviewer (NeurIPS/ICML level)."
  prompt: |
    [Iteration N/MAX_ITERATIONS of autonomous review loop]
    [Iteration budget: <iterations_consumed>/<MAX_ITERATIONS> used; claim-reentry sub-budget: <claim_reentries_consumed>/<MAX_CLAIM_REENTRIES> used]

    [Full research context: claims, methods, results, known weaknesses]
    [Changes since last iteration, if any]

    ## Per-claim verify state (from /auto-verify)
    verify_passed:                  [<ids or "none">]   # brief consistency check only
    verify_failed:                  [<ids or "none">]   # two-phase: variant-integrity check, then optional claim rewrite
    verify_inconclusive:            [<ids or "none">]   # main-experiment-only fix; you may NOT rewrite the claim
    verify_zero_eligible_variants:  [<ids or "none">]   # variant-only fix; do NOT touch the main experiment
    verify_integrity_only:          [<ids or "none">]   # NO back-edge action; record in Open Items with stage2_skip_reason-dispatched upgrade suggestion

    Tasks:
    1. Score this work 1-10 for a top venue.
    2. For each FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS claim, name the MINIMUM
       fix and tag it with the routing type (①/②/③). If you want to use ③ (claim rewrite)
       on a FAIL claim, also provide the proposed new claim text — verify that the
       claim-reentry sub-budget has remaining capacity before recommending ③.
       Do NOT propose fixes or ①/②/③ actions for INTEGRITY_ONLY claims — those are
       swap-test-skipped outputs (audit passed) with no robustness data to fix; iteration
       records them as unfinished stress-tests, not as findings that need repair.
    3. For each PASS claim, do a brief narrative + numeric consistency check.
       Flag any caveat (main-experiment-WARN) that should surface in the final paper.
    4. State clearly: is this READY for submission? Yes/No/Almost. READY requires all
       FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS claims to be resolved.
       INTEGRITY_ONLY claims do NOT block READY (they are outside the stress-test
       scope by policy or cap) — but note their presence as a caveat in the assessment.
    5. (Iteration 1 only) Record any initial suspicions or concerns you want to
       track in future iterations — output as a `## Memory update` section so
       Phase B.5 can seed `REVIEWER_MEMORY.md` with them.

    Be brutally honest. If the work is ready, say so clearly.
```

**Iteration 1 — save `thread_id`.** When the MCP call returns, capture the response's `thread_id` (or equivalent conversation handle the MCP server uses) and persist it to `REVIEW_STATE.json`'s `thread_id` field. This is what iteration 2+ uses to continue the same reviewer thread instead of pasting summaries. If the MCP server does not return a thread handle (some configurations don't), or the call used the curl fallback, write `null` and let iteration 2+ fall back to the paste-summary path.

**Iteration 2+ — pass `thread_id` back when present.** If `REVIEW_STATE.json` has a non-null `thread_id`, pass it as the `thread_id` arg on the `mcp__llm-chat__chat` call. The iteration-2+ prompt body becomes shorter (no need to re-paste prior reviews — the thread already has them), but the **Reviewer Memory** prepend block is still mandatory (it carries the structured suspicion account that the thread itself doesn't make queryable). On any error indicating the thread is unknown / expired (server returns 4xx with a thread-related message), clear `thread_id` to `null` in state and retry once without it — falling back to the paste-summary template at the end of this file.

**If MCP NOT available:**
```bash
curl -s "${LLM_BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LLM_API_KEY}" \
  -d '{
    "model": "${LLM_MODEL}",
    "messages": [
      {"role": "system", "content": "You are a senior ML reviewer (NeurIPS/ICML level)."},
      {"role": "user", "content": "[Full review prompt with all four buckets explicit]"}
    ],
    "max_tokens": 4096
  }'
```

#### Phase B: Parse Assessment

**CRITICAL: Save the FULL raw response** verbatim. Then extract:
- **Score** (numeric 1-10)
- **Verdict** — canonicalize the reviewer's free-form verdict to one of `{ready, almost, not ready}`. Map synonyms: `accept` / `sufficient` / `good enough` / `looks ready` → `ready`; `nearly ready` / `close` / `minor revision` → `almost`; everything else (incl. `revise`, `weak`, `reject`, `needs major work`) → `not ready`. This canonical value is what gets written to `REVIEW_STATE.json` as `last_verdict` and is what the agent's output contract promises.
- **Per-claim action items** — for each claim id in `verify_failed` / `verify_inconclusive` / `verify_zero_eligible_variants`, the reviewer's chosen routing type (①/②/③) and the minimum fix. Reject the reviewer's choice and substitute `none — pending budget` if the request violates the routing contract (e.g., ③ on an INCONCLUSIVE claim, or ③ when `claim_reentries_consumed >= MAX_CLAIM_REENTRIES`). Reviewer proposals for `verify_integrity_only` action items are always rejected as contract violations (no-action by design); log `[verify] rejected reviewer action on verify_integrity_only claim <id> — bucket is no-action-only` and record no action.

**STOP (three-dimensional)**: Terminate the loop when **all** of the following hold:
1. `score >= TARGET_SCORE`
2. canonical verdict ∈ `POSITIVE_VERDICT_TERMS` (i.e., `ready` or `almost`)
3. `verify_failed`, `verify_inconclusive`, and `verify_zero_eligible_variants` are all empty (every claim is either PASS or INTEGRITY_ONLY). `verify_integrity_only` does NOT block STOP — it is a no-action bucket carried forward as Open Items.

The third condition is critical — without it the loop would terminate with the reviewer giving high marks while some claim is still officially FAIL/INCONCLUSIVE/ZERO_ELIGIBLE_VARIANTS, leaving an inconsistent record. If the reviewer scores high but a non-PASS claim remains, log `[stop] reviewer says ready (score=<X>, verdict=<V>) but <K> claim(s) still unresolved (<bucket=ids>) — continuing loop` and proceed to Phase C.

Two further termination paths (not satisfaction-based — budget-exhaustion):
- `iterations_consumed >= MAX_ITERATIONS` after this iteration's Phase C increment → terminate, write final report with status "exhausted iterations".
- `claim_reentries_consumed >= MAX_CLAIM_REENTRIES` AND the only unresolved claims would require type ③ → terminate, write final report with status "exhausted claim-reentry budget".
- `consecutive_noop_count >= 2` → terminate (the reviewer kept proposing narrative-only fixes with no score/verdict change — non-converging on the reviewer side; see the stall guard in the Loop header). Log `[loop] two consecutive no-op iterations — stalled, returning`, set `status = "completed"`, write final report with status "stalled — two consecutive no-op iterations".

#### Phase B.5: Reviewer Memory Update

After Phase B, append a new section to `REVIEWER_MEMORY_DOC` (`review-stage/REVIEWER_MEMORY.md`). This file is the reviewer's persistent brain across iterations; Phase A of the next iteration prepends it to the prompt.

**If the reviewer's raw response included a `## Memory update` (or similar) section, copy it verbatim.** Otherwise, infer the four sub-sections below from the parsed weaknesses + canonical verdict — be conservative, only record what the reviewer actually flagged (do not invent suspicions).

Append shape (iteration N, where the file already contains iterations 1..N-1):

```markdown
## Iteration N — Score: <X>/10, Verdict: <canonical>

- **New suspicions**: <bullets — concerns the reviewer raised this iteration for the first time>
- **Previous suspicions addressed?**: <yes/no per item, with the reviewer's judgment if stated; on iteration 1 write `n/a (first iteration)`>
- **Unresolved (carried forward)**: <bullets — prior suspicions still open + any new ones not yet acted on>
- **Patterns**: <recurring issues across iterations, if any — e.g. "metrics keep being computed against model output, not GT">
```

**Rules**:
- **Append-only.** Never rewrite or delete prior iterations — the audit trail must survive even after the loop terminates.
- **Iteration 1**: the file does not yet exist; create it with a top-level `# Reviewer Memory` header and the iteration-1 section.
- **Iteration 2+**: open the existing file and append; do not touch prior iteration sections.
- **Resume**: if `RESUME=true` and the iteration being re-run already has its `## Iteration N` section in the file (e.g., crashed during Phase C of iteration N after Phase B.5 completed), do **not** append a duplicate — log `[reviewer-memory] iteration N section already present — skipping append` and continue.
- **Honesty constraint**: this file is for the reviewer's perspective. Do not edit it on Claude's behalf to soften criticism; if a suspicion is later resolved, that gets recorded in the **next** iteration's `Previous suspicions addressed?` line, not by rewriting history.

If the LLM call in Phase A failed entirely (no raw response to parse), skip Phase B.5 for this iteration — there is nothing to record. Log `[reviewer-memory] skipped — no reviewer response this iteration`.

#### Phase C: Implement Fixes (dispatch by action type)

Each unresolved claim's reviewer-chosen routing type from Phase B dispatches to one of the three back-edge action types:

##### Action type ① — variant-only fix (FAIL Phase 1, or any ZERO_ELIGIBLE_VARIANTS)

For each claim id needing ①:
1. Read `verify/<claim_dir>/variant_audit/{EXPERIMENT,MECHANISM}_AUDIT.md` and each failed variant's `verdict.json.integrity_breakdown`.
2. For each variant whose fix is targeted, edit the variant's `eval.py` / mechanism harness in `verify/<claim_dir>/variants/<variant-tag>/` (or delete the variant directory if the fix is "this variant is unsalvageable, re-pick"). Record a Before/After summary of the change.
3. Re-invoke `/auto-verify <claim-id> — resume: true`. With `resume: true`, Phase 1 argument parsing and Phase 2 main-experiment audit skip (main experiment already passed); only variant-side phases re-execute.
4. Wait for `/auto-verify` to complete; the new per-claim `ROBUSTNESS.md` becomes this claim's input for the next iteration.

##### Action type ② — main-experiment-script / plan fix (INCONCLUSIVE only)

For each claim id needing ②:
1. Read `verify/<claim_dir>/main_experiment_audit/{EXPERIMENT,MECHANISM}_AUDIT.md` to find the broken methodology line(s).
2. Edit the affected step in `refine-logs/EXPERIMENT_PLAN.md` and the corresponding main-experiment script under `experiments/<name>/`. Record Before/After diffs for both.
3. **Choose lightweight or full path** (same iteration cost either way; pick by compute efficiency):
   - **Lightweight**: manually re-run only the affected `runs/<run-id>/` for this claim, then re-invoke `/auto-verify <claim-id>`. Use this when only one or two main-experiment runs need redoing.
   - **Full**: re-invoke `/auto-experiment` (with `target_claims: [<id>]` if supported) followed by `/auto-verify <claim-id>`. Use this when the plan diff cascades across runs.
4. Wait for completion; the new `ROBUSTNESS.md` is this claim's next-iteration input.

##### Action type ③ — claim-stage re-entry (FAIL Phase 2 only)

For each claim id needing ③:
1. **Pre-flight budget check**: if `claim_reentries_consumed >= MAX_CLAIM_REENTRIES`, refuse — record `[claim-reentry] declined — sub-budget exhausted (<n>/<MAX_CLAIM_REENTRIES>)` under this iteration's `### Actions Taken`, and either fall back to ① (if Phase 1 still has unfixed variants for this claim) or leave the claim unresolved for the final report.
2. **Choose lightweight or full path** (same iteration cost AND same claim-reentry sub-budget cost):
   - **Lightweight in-loop rewrite**: the reviewer must already have provided proposed new claim text in Phase A. Write the new claim text into `AUTO_REVIEW.md` under the iteration's `### Claim Rewrites` section (also assign a new claim id, by convention `<original-id>_v2` / `_v3` / …). Then dispatch `/auto-experiment` and `/auto-verify` scoped to the new id, in-loop. The orchestrator is not involved.
   - **Full claim-stage re-entry**: set `status = "awaiting_upstream"`, populate `pending_upstream_calls` with `[{skill: "auto-claim", args: {focus: "<claim-id> — verify-failed context: <summary>"}}, {skill: "auto-experiment", args: {target_claims: ["<new-id>"]}}, {skill: "auto-verify", args: {target_claims: ["<new-id>"]}}]`, increment `iterations_consumed` and `claim_reentries_consumed`, write Phase E (state + AUTO_REVIEW append) including the queued calls, and return. The orchestrator runs the calls, then resumes this skill with `RESUME=true`.
3. Record the new claim id under `iteration_breakdown[i].produced_claims` so the final report attributes the new claim to the original claim's journey section.

##### Counter increment + bookkeeping (after ① / ② / ③ — skipped for ⓪)

After the dispatched action completes (lightweight path) OR after queuing it for the orchestrator (③ full path), increment:
- `iterations_consumed += 1`
- `claim_reentries_consumed += 1` (only if the action was type ③)
- `runs_total += <K>` where `K` is the total number of `/run-experiment` calls newly fired this iteration, **counted across all three cost-manifest surfaces**:
  - **Surface A — variant re-runs (action ①)**: `verify/<claim_dir>/variants/<v>/cost.json` (written by `/auto-verify`'s downstream `/run-experiment` calls). Iterate the variants this iteration re-ran and read each `cost.json`.
  - **Surface B — main-experiment runs from full `/auto-experiment` (action ② full path)**: `runs/<run-id>/cost.json` (the standard auto-experiment surface). Read the `runs_total_delta` from auto-experiment's return summary, or enumerate the run-ids it produced.
  - **Surface C — iteration-local ad-hoc or lightweight ② re-runs**: `runs/iteration_round_<N>/<run-id>/cost.json` (this skill's convention, where `<N>` is the iteration number — see below).
- `gpu_hours_total += <H>` where `H` is the sum of `gpu_hours` from every `cost.json` enumerated above. If any `cost.json` is missing or has `status: running`, block on `/monitor-experiment` to finalize it before reading — do not guess from deploy logs.
- Append a new entry to `iteration_breakdown` with `{i, type, target_claims, produced_claims}`. For type ⓪, this section is **not** executed at all: `iteration_breakdown` does not get a new entry, and none of the counters change — the only persistent trace of a ⓪ action is the `### Actions Taken` line in `AUTO_REVIEW.md` for that iteration.

##### Output directories

**New experiments deployed in iteration N go under**:

```
runs/iteration_round_<N>/
```

(The legacy directory name remains `iteration_round_<N>` for compatibility with prior tooling, even though we now count "iterations" rather than "review rounds". `<N>` is the **1-indexed iteration number** the run belongs to — i.e., `iterations_consumed + 1` at the moment the run is launched mid-Phase-C, equivalently `iterations_consumed` after Phase C's end-of-iteration increment runs. Both expressions name the same iteration; pick whichever is clearer at the call site.)

Do **not** mix new runs into the original `runs/<run_id>_<short_purpose>/` directories (those are frozen artifacts from `/auto-experiment`). Inside `iteration_round_<N>/`, name files by what they produce (e.g., `bootstrap_layer_sweep.json`, `cross_seed_function.json`) rather than synthetic IDs — these are reviewer-driven one-offs, not plan-tracked runs.

**Iteration runs are NOT added to `refine-logs/EXPERIMENT_TRACKER.md`.** The tracker is frozen the moment `/auto-experiment` returns — it represents the plan-driven runs. Iteration runs are tracked here in `review-stage/AUTO_REVIEW.md` under the iteration's `### Results` section and in `review-stage/REVIEW_STATE.json` (`runs_total`, `gpu_hours_total`, `iteration_breakdown`). When you cite an iteration result in `AUTO_REVIEW.md`, use the path `runs/iteration_round_<N>/<file>` directly — do **not** retro-add a synthetic Run-ID and append to the tracker. This keeps the experiment-stage and iteration-stage audit trails separable.

##### GPU pinning + cost manifest read

**GPU pinning.** If `GPU_ID` is anything other than `auto`, pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional arg to every `/run-experiment` invocation dispatched above (the run-experiment skill exports it in the experiment subprocess; do **not** treat as a shell prefix — `/run-experiment` is a Skill, not a shell command). Record the effective `CUDA_VISIBLE_DEVICES` in each run's `run.sh` so reproductions land on the same devices. This mirrors the `GPU_ID` handling in `/auto-experiment` Phase 3.

Each new experiment is typically launched through `/run-experiment` — one call per logical run. **Queue path (rare).** If a single iteration's fix requires ≥ 10 runs (e.g., reviewer asks for a 21-seed × 4-size grid), prefer `/experiment-queue` with a one-phase manifest instead — it brings the same OOM retry / stale-screen / GPU-gate protections as the experiment-stage Phase 4.B. The iteration output directory `runs/iteration_round_<N>/` still applies; `queue_state.json` lives next to it under the local run dir per `/experiment-queue` convention. After the queue batch completes, invoke `/monitor-experiment` per job to finalize each `runs/iteration_round_<N>/<job-id>/cost.json`, then continue with bookkeeping.

After each run completes (confirmed via `/monitor-experiment`, which finalizes the cost manifest in its Step 3.6), read its `gpu_hours` from `runs/iteration_round_<N>/<run-id>/cost.json` — this is the **canonical** source written by `/run-experiment` Step 5.5 (initial stub) and finalized by `/monitor-experiment` Step 3.6. Do **not** parse free-form deploy logs as a substitute; if `cost.json` is missing or has `status: running` (run not yet finalized), wait for `/monitor-experiment` to complete the finalization rather than guessing. Append one line to `AUTO_REVIEW.md` under the iteration's `### Results` section:

```
[run-experiment] iteration=N runs_this_iteration=K gpu_hours_this_iteration=X cumulative_gpu_hours=Y
```

If the iteration's fixes are purely reviewer-narrative (no back-edge action of any type — e.g., the reviewer asked only for a clarifying caveat in the paper), Phase C is a no-op and `iterations_consumed` is NOT incremented (see the Loop header note).

#### Phase D: Wait for Results

Monitor remote experiments via `/monitor-experiment`. For type ③ full claim-stage re-entry, the orchestrator handles waiting — this skill does not block; it sets `awaiting_upstream` and returns.

#### Phase E: Document Iteration

Append to `review-stage/AUTO_REVIEW.md`. The template is **per-category-structured** (not flat) so the Termination step can assemble `FINAL_REPORT_DOC` by reading these sections directly — keep each subsection self-contained:

```markdown
## Iteration N (timestamp)

### Assessment (Summary)
- Score: X/10
- Verdict: [ready/almost/not ready]
- Budget after this iteration: iterations <iterations_consumed>/<MAX_ITERATIONS>, claim-reentries <claim_reentries_consumed>/<MAX_CLAIM_REENTRIES>
- Key criticisms: [bullet list]

### Reviewer Raw Response

<details>
<summary>Click to expand full reviewer response</summary>

[Paste the COMPLETE raw response here — verbatim, unedited.]

</details>

### Verify-Passed Claims (brief audit)
- <claim-id>: <one-line consistency check result, or caveat for the paper>
- [or "none" when the iteration's verify_passed bucket was empty]

### Actions Taken (per claim, per type)
Format each entry as: `<claim-id> — type <⓪|①|②|③> — <one-line summary>`. The four types:

- **⓪ narrative-only** — reviewer asked for a paper-side caveat / reframing only, no script or data changes. Does NOT consume an iteration; the entry still exists for audit (so the final report can attribute the caveat to a claim). Allowed only as the **sole** action of an iteration if the loop is otherwise converged.
- **① variant-only fix** — dispatched into the variant-script surface (`verify/<claim_dir>/variants/<v>/`); consumes 1 iteration.
- **② main-experiment-script / plan fix** — dispatched into `refine-logs/EXPERIMENT_PLAN.md` + `experiments/<name>/`; consumes 1 iteration.
- **③ claim-stage re-entry** — claim rewrite (lightweight or full path); consumes 1 iteration + 1 claim-reentry sub-budget.

Include the Before/After diffs of any experiment_plan / script / variant changes under nested bullets:

- <claim-id> — type ① — fixed variant `model-swap-X` (mechanism integrity FAIL)
  - **Variant script Before/After** (`verify/<claim_dir>/variants/model-swap-X/eval.py:L42`):
    - Before: `score / scores.max()`
    - After:  `score / train_stats.max`
  - Re-invoked: `/auto-verify <claim-id> — resume: true`
- <claim-id> — type ② — fixed main-experiment plan step 3.2 + main-experiment `eval.py`
  - **Plan Before/After** (`refine-logs/EXPERIMENT_PLAN.md:L87`):
    - Before: "evaluate on val"
    - After:  "evaluate on held-out test, normalize with train stats only"
  - **Main-experiment script Before/After** (`experiments/<name>/eval.py:L120`): ...
  - Re-invoked: `/auto-experiment — target_claims: [<id>]` then `/auto-verify <claim-id>`
- <claim-id> — type ⓪ — added paper-side caveat "within-domain only"; no scripts touched, no runs fired

### Claim Rewrites (type ③ — empty when no rewrite this iteration)
- Original claim id: `<original-id>` — text: "<original claim text>"
- New claim id:      `<new-id>` — text: "<new claim text>"
- Path: lightweight in-loop | full claim-stage re-entry (awaiting_upstream)
- Reason: <one paragraph — why narrow / why pivot / why rewrite>
- Claim-reentry sub-budget consumed: 1 (now <claim_reentries_consumed>/<MAX_CLAIM_REENTRIES>)

### Claim-Stage Re-entries Triggered (orchestrator handoff — empty unless type ③ full path used this iteration)
- <claim-id>: queued `pending_upstream_calls = [/auto-claim, /auto-experiment, /auto-verify]`; reason: <variants clean, main experiment still not robust>
- [or "none"]

### Open Items — Unverified Under Swaps (from verify_integrity_only)
- <claim-id> [stage2_skip_reason: swap_variants_false | max_verify_claims_cap]:
  * `swap_variants_false` → `/auto-verify <id> — swap-variants: true, resume: true` (Phase 2 audits reused via RESUME; only Stages 2–3 run)
  * `max_verify_claims_cap` → `/auto-verify <id> — resume: true` (single-claim mode; Phase 2 audit reused via RESUME; only Stages 2–3 run)
  [main-experiment integrity: <pass|warn>[; warn_source: <experiment|mechanism|experiment+mechanism>]]
- [or "none" when the iteration's verify_integrity_only context list was empty]

### Results
- [run-experiment] iteration=N runs_this_iteration=K gpu_hours_this_iteration=X cumulative_gpu_hours=Y
- [per-claim outcome lines — e.g. "C1 → /auto-verify rerun → PASS (robustness=0.67)"]

### Status
- [continuing to iteration N+1 / awaiting_upstream / completed]
```

> **Per-category contract.** Every iteration's Phase E writeup must include **all nine** subsections in this exact order: Assessment, Reviewer Raw Response, Verify-Passed Claims, Actions Taken, Claim Rewrites, Claim-Stage Re-entries Triggered, Open Items — Unverified Under Swaps, Results, Status. Empty subsections write `none` rather than being omitted — Termination's final-report assembly reads them by header and silently skipped headers would drop claims from the final report.

**Write `review-stage/REVIEW_STATE.json`** with current state (status, all counters, iteration_breakdown, etc.).

### Termination

Triggered by any of:
- **Positive verdict** — Phase B's three-dimensional STOP fired this iteration.
- **Iterations exhausted** — `iterations_consumed >= MAX_ITERATIONS` after this iteration's Phase C.
- **Claim-reentry budget exhausted** — `claim_reentries_consumed >= MAX_CLAIM_REENTRIES` AND the only remaining unresolved claims would require type ③.

Steps:
1. Set `review-stage/REVIEW_STATE.json` `status` to `"completed"`.
2. Record the termination reason as a top-level field `"termination_reason"` ∈ `{positive_verdict, iterations_exhausted, claim_reentry_exhausted}`.
3. **Assemble `FINAL_REPORT_DOC` = `review-stage/AUTO_ITERATION_FINAL_REPORT.md`** by reading every iteration's per-category Phase E sections and folding them into the per-claim narrative structure described in "Final Report" below. The iteration agent (this skill) synthesizes the Executive Summary itself — do **not** invoke the reviewer for it.
4. Return to the caller (orchestrator or user). The agent's return message includes `termination_reason`, the five per-category claim counts (PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS / INTEGRITY_ONLY), `iterations_consumed / MAX_ITERATIONS`, `claim_reentries_consumed / MAX_CLAIM_REENTRIES`, and the paths to `AUTO_REVIEW.md` + `FINAL_REPORT_DOC` + `REVIEWER_MEMORY.md`.

## Final Report

`FINAL_REPORT_DOC = review-stage/AUTO_ITERATION_FINAL_REPORT.md` is the narrative output of the whole loop. It is **not** an append log (that's `AUTO_REVIEW.md`); it is a one-shot synthesis written at Termination from material already on disk.

### Source mapping

| Section | Source(s) |
|---|---|
| Header & disposition overview | `REVIEW_STATE.json` (counters, termination_reason, last_score, last_verdict); count claim ids per bucket from `verify/VERIFY_REPORT.md` + each iteration's `Verify-Passed Claims` / `Actions Taken` |
| Per-category claim sections | Per-iteration `Actions Taken` / `Claim Rewrites` / `Results` from `AUTO_REVIEW.md`, joined by claim id |
| Per-claim journey tables | `iteration_breakdown[]` filtered to each claim's id (and to any `_v2` / `_v3` descendants from claim rewrites) |
| Experiment & script modifications (FAIL/INCONCLUSIVE/ZERO_ELIGIBLE_VARIANTS sections) | Before/After bullets inside `### Actions Taken` of the iteration that fixed the claim |
| Cross-cutting patterns | `- **Patterns**:` bullets inside each `## Iteration N` block of `REVIEWER_MEMORY.md`, deduped across iterations |
| Iteration budget & pipeline (per-iteration table) | `iteration_breakdown[]` + per-iteration `### Results` |
| Open items | Union of per-iteration `### Open Items — Unverified Under Swaps` (deduped) + any FAIL/INCONCLUSIVE/ZERO_ELIGIBLE_VARIANTS claims still unresolved at termination. INTEGRITY_ONLY claims are always listed here (they never resolve within the iteration loop). |

### Report skeleton

```markdown
# Auto Iteration Final Report — <project name>

- **Generated**: <ISO timestamp>
- **Iterations consumed**: <iterations_consumed> / <MAX_ITERATIONS>
- **Claim-reentries consumed**: <claim_reentries_consumed> / <MAX_CLAIM_REENTRIES>
- **Final reviewer score**: <last_score> / 10
- **Final canonical verdict**: <ready | almost | not ready>
- **Termination reason**: <positive_verdict | iterations_exhausted | claim_reentry_exhausted>
- **Cumulative cost**: runs_total=<K>, gpu_hours_total=<H>
- **Source audit trail**: [`AUTO_REVIEW.md`](./AUTO_REVIEW.md), [`REVIEWER_MEMORY.md`](./REVIEWER_MEMORY.md)

---

## Executive Summary

<2–4 sentences synthesized by the iteration agent itself (no extra reviewer call). What the loop addressed, which claims converged, which were rewritten, which remain open.>

### Claim Disposition Overview

| Original state | # Claims | Final status after iteration |
|---|---|---|
| PASS                     | a | a PASS (held) |
| FAIL                     | b | b₁ PASS (variant fix) / b₂ PASS (new claim via ③) / b₃ still FAIL |
| INCONCLUSIVE             | c | c₁ PASS / c₂ FAIL / c₃ still INCONCLUSIVE |
| ZERO_ELIGIBLE_VARIANTS   | d | d₁ PASS / d₂ FAIL / d₃ still ZERO_ELIGIBLE_VARIANTS |
| DEFERRED                 | e | e queued for standalone `/auto-verify` |

---

## Section 1 — PASS Claims (brief audit)

For each claim id in the original `verify_passed` bucket:

### 1.x `<claim-id>` — <one-line statement>
- **Original robustness signal**: robustness=<r>, variants_passed=<x>/<y>
- **Reviewer consistency check**: <one-line — narrative / numeric / caveat>
- **Touched in iterations**: <[1] or [1,3]>
- **Final status**: PASS (held)
- **Notes for downstream**: <any paper-side caveat, or "none">

---

## Section 2 — FAIL Claims (full journey)

For each claim id in the original `verify_failed` bucket:

### 2.x `<claim-id>` — <one-line statement>

**Original FAIL signal**
- robustness=<r> (threshold=<θ>)
- Inconsistent dimensions: <e.g. "seed sensitivity, scale generalization">
- Variant integrity at entry: <"all clean" | "k of n had integrity issues">

**Iteration journey**

| Iter | Type | Reviewer flag | Action | Outcome |
|---|---|---|---|---|
| 1 | ① | variant `vN` mechanism-FAIL | rewrote `verify/<dir>/variants/vN/eval.py:L42`; reran `/auto-verify <id> — resume: true` | variant `vN` integrity clean; robustness <r₀>→<r₁> |
| 2 | ③ | clean variants, still below threshold | claim rewrite (lightweight, narrowed to "within-domain"); chained `/auto-experiment` + `/auto-verify` | new claim `<id>_v2` produced; `/auto-verify` PASS at <r₂> |

**Path taken (summary)**: variant-integrity fix → claim-stage re-entry (1 hop) — claim-reentry sub-budget used: 1

**Experiment & script modifications** (cumulative across all iterations on this claim)

| Iter | Component | Before | After |
|---|---|---|---|
| 1 | `verify/<dir>/variants/vN/eval.py:L42` | `scores / scores.max()` | `scores / train_stats.max` |
| 2 | (lightweight rewrite — no script edits beyond rerunning the rewritten claim's pipeline) | — | — |

**Claim modifications** (mandatory subsection — write `none — variant fix path only` if no rewrite happened)
- Original claim id `<id>`: "<original text>"
- After iteration 2 → new claim id `<id>_v2`: "<new text>"
- Scope change: <e.g. "removed cross-domain assertion, kept within-domain">

**Final experiment summary**
- New runs cited: `runs/iteration_round_1/<file>`, `runs/iteration_round_2/<file>`
- Final robustness: <r₂>
- Final variant pass rate: <x>/<y>
- Final status: **PASS (under new claim `<id>_v2`)** | **still FAIL — flagged in Open Items**

**Reviewer memory thread** (cross-iteration suspicions filtered to this claim's pattern)
- <verbatim bullets from REVIEWER_MEMORY.md>
- Resolved: <yes/no per item>

---

## Section 3 — INCONCLUSIVE Claims (main-experiment-fix journey)

For each claim id in the original `verify_inconclusive` bucket:

### 3.x `<claim-id>` — <one-line statement>

**Original INCONCLUSIVE reason** (from `verify/<dir>/ROBUSTNESS.md`'s `inconclusive_reason`):
- <verbatim, e.g. "main-experiment integrity broken — see verify/<dir>/main_experiment_audit/EXPERIMENT_AUDIT.md">

**Experiment plan & script modifications**

| Iter | Component | Before | After |
|---|---|---|---|
| 1 | `refine-logs/EXPERIMENT_PLAN.md` step 3.2 | "evaluate on val" | "evaluate on held-out test, normalize with train stats only" |
| 1 | `experiments/<name>/eval.py:L42` | `scores / scores.max()` | `scores / train_stats.max` |

**Re-experiment outcome**

| Iter | Path | New runs | Result |
|---|---|---|---|
| 1 | full re-run: `/auto-experiment` + `/auto-verify` | `runs/iteration_round_1/<run-id>/` | main-experiment integrity PASS, variants ran, verdict=PASS, robustness=<r> |

**Final status**: **PASS** | **FAIL after fix** | **still INCONCLUSIVE — flagged in Open Items**

**Reviewer memory thread**:
- <related bullets, if any>

---

## Section 4 — ZERO_ELIGIBLE_VARIANTS Claims (variant-fix journey)

For each claim id in the original `verify_zero_eligible_variants` bucket. Structure mirrors Section 3 but diffs target variant scripts (`verify/<dir>/variants/<v>/...`), not main-experiment scripts.

### 4.x `<claim-id>` — <one-line statement>

**Original ZERO_ELIGIBLE_VARIANTS reason** (from `verify/<dir>/ROBUSTNESS.md`'s `zero_eligible_reason`):
- <verbatim breakdown — N_exp_fail / N_mech_fail / N_both_fail>

**Variant script modifications**

| Iter | Variant | Component | Before | After |
|---|---|---|---|---|
| 1 | method-swap-X | `verify/<dir>/variants/method-swap-X/eval.py:L87` | <…> | <…> |
| 1 | model-swap-Y | `verify/<dir>/variants/model-swap-Y/mechanism.py:L24` | <…> | <…> |

**Re-verify outcome**

| Iter | Path | Action | Result |
|---|---|---|---|
| 1 | `/auto-verify <id> — resume: true` | only variant phases re-ran | N_eligible=2/3, robustness=<r>, verdict=PASS |

**Final status**: **PASS** | **FAIL after fix** | **still ZERO_ELIGIBLE_VARIANTS — flagged in Open Items**

---

## Section 5 — Legacy DEFERRED Claims (empty under current architecture)

> New verify runs never populate this section — `MAX_VERIFY_CLAIMS` cap-cut claims now land in Section 4b (INTEGRITY_ONLY, stage2_skip_reason: max_verify_claims_cap) with their Stage 1 audit results on disk. Section 5 is retained only for backward compatibility with legacy `VERIFY_REPORT.md` files that still carry a `## Deferred Claims` section.

For each claim id in a legacy `deferred_claims` list (if any):

### 5.x `<claim-id>` — <one-line statement>
- **Required next step**: standalone `/auto-verify <claim-id>` before re-entering iteration
- **Why deferred**: legacy `MAX_VERIFY_CLAIMS` cap (pre-restructure — verify ran only a subset)

---

## Section 6 — Cross-Cutting Patterns

> Patterns the reviewer kept flagging across iterations — surfaced separately because they often point to systemic methodology issues rather than per-claim problems.

- <verbatim `- **Patterns**:` bullets from each `## Iteration N` block of REVIEWER_MEMORY.md, deduped across iterations>
- For each pattern: which claims it touched, and whether it was resolved at termination

> This section is **inclusive** — every pattern the reviewer ever flagged appears here, whether or not it was eventually resolved. Section 8 ("Open Items") repeats only the still-unresolved subset.

---

## Section 7 — Iteration Budget & Pipeline

- **Iterations consumed**: <iterations_consumed> / <MAX_ITERATIONS>
- **Claim-reentries consumed**: <claim_reentries_consumed> / <MAX_CLAIM_REENTRIES>
- **Iteration `/run-experiment` calls**: runs_total = <K>
- **Iteration GPU-hours**: gpu_hours_total = <H>

### Per-iteration breakdown (from `iteration_breakdown[]`)

| Iter | Type | Target claims | Produced claims | Runs | GPU-hours | Score after | Verdict after |
|---|---|---|---|---|---|---|---|
| 1 | ① variant_fix | C1 | — | 1 | 2.1 | 5 | not ready |
| 2 | ② plan_script_rerun | C2 | — | 3 | 6.3 | 6 | almost |
| 3 | ③ claim_reentry | C1 | C1_v2 | 2 | 4.0 | 7 | almost |

---

## Section 8 — Open Items for Human Reviewer

> Items the loop could not close. These need a human or a separate pipeline.

- **Still-FAIL claims** (after exhausting routing options): <list with one-line why>
- **Still-INCONCLUSIVE claims**: <list>
- **Still-ZERO_ELIGIBLE_VARIANTS claims**: <list>
- **INTEGRITY_ONLY claims (Stage 2 skipped — not stress-tested)**: <list — surfaced verbatim from each iteration's "Unverified Under Swaps" subsection; each entry names the claim id, its `stage2_skip_reason` (`swap_variants_false` or `max_verify_claims_cap`), the matching upgrade instruction, plus the `main_experiment_integrity` level and any `warn_source`>
- **Legacy deferred claims (empty in new runs)**: <list — surfaced only when a legacy `VERIFY_REPORT.md` still carries a `## Deferred Claims` section>
- **Recurring unresolved patterns**: <list>
- **Claim-reentry refusals** (where reviewer requested ③ but sub-budget was exhausted): <list>
```

## Key Rules

- **Five-bucket discipline.** Every iteration's reviewer prompt must include all five verify-state buckets (`verify_passed`, `verify_failed`, `verify_inconclusive`, `verify_zero_eligible_variants`, `verify_integrity_only`) explicitly. Reviewers are not allowed to rewrite INCONCLUSIVE claims (rewrite is a FAIL-Phase-2 action only), nor to propose any back-edge action on INTEGRITY_ONLY claims (that bucket is no-action-with-upgrade-suggestion — the fix is to re-run verify with the per-`stage2_skip_reason` upgrade command, not to touch the main experiment or the claim). The legacy `deferred_claims` bucket is empty in new runs and does not appear in the reviewer prompt.
- **Unified iteration budget.** `MAX_ITERATIONS` counts every back-edge action (① variant fix / ② plan+script fix / ③ claim re-entry) uniformly. New claims produced by ③ inherit the same budget — they do not get a fresh allocation. `MAX_CLAIM_REENTRIES` is a sub-budget within `MAX_ITERATIONS` specifically for ③.
- **State-machine status values**: `in_progress` / `awaiting_upstream` / `completed`. `awaiting_upstream` is the handoff signal to the orchestrator; only `completed` triggers `FINAL_REPORT_DOC` assembly.
- **Append-only audit chain.** `AUTO_REVIEW.md` (per-iteration log), `REVIEWER_MEMORY.md` (cross-iteration suspicions), and `iteration_breakdown[]` in `REVIEW_STATE.json` are all append-only. `FINAL_REPORT_DOC` is the one-shot synthesis written at Termination — never appended to.
- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **Anti-hallucination citations**: When adding references, NEVER fabricate BibTeX. Use DBLP → CrossRef → `[VERIFY]` chain. Do NOT generate BibTeX from memory.
- Be honest about weaknesses.
- Implement real fixes (①/②/③) BEFORE re-reviewing whenever the reviewer flagged a non-narrative weakness. Type ⓪ (narrative-only) is allowed as an iteration's sole action only when every weakness the reviewer named is genuinely a paper-presentation issue, not a methodology or data issue dressed up as one.
- Document everything per the per-category Phase E template (every subsection, even when `none`).
- Include previous context in iteration 2+ prompts.
- Prefer MCP tool over curl when available.

## Prompt Template for Iteration 2+

The iteration-2+ prompt has two prepended blocks before the body: **Reviewer Memory** (verbatim contents of `REVIEWER_MEMORY_DOC`) and **Previous Review Summary** (parsed from the prior iteration). The memory block is what gives this loop its adversarial edge — the reviewer sees its own prior suspicions and can check whether they were genuinely addressed.

**Path selection.** This template is used when `REVIEW_STATE.json`'s `thread_id` is `null` (curl fallback was used in iteration 1, or the MCP server doesn't support thread continuation) — both blocks are concatenated into a fresh prompt with no server-side conversation state. **When `thread_id` is non-null, prefer the thread-continuation path**: pass `thread_id` to `mcp__llm-chat__chat` so the reviewer keeps its prior conversation, drop the "Previous Review Summary" block (the server already has it), but keep the Reviewer Memory prepend (it's structured suspicions, not dialog history). The template below covers the no-thread case; the thread case is just "Reviewer Memory + body, no summary block, `thread_id` passed as a call arg."

```
mcp__llm-chat__chat:
  system: "You are a senior ML reviewer (NeurIPS/ICML level)."
  prompt: |
    [Iteration N/MAX_ITERATIONS of autonomous review loop]
    [Iteration budget: <iterations_consumed>/<MAX_ITERATIONS> used;
     claim-reentry sub-budget: <claim_reentries_consumed>/<MAX_CLAIM_REENTRIES> used]

    ## Your Reviewer Memory (persistent across iterations)
    [Paste the FULL contents of review-stage/REVIEWER_MEMORY.md here — do not summarize]

    IMPORTANT: You have memory from prior iterations. Check whether your previous
    suspicions were genuinely addressed or merely sidestepped. The author
    (Claude) controls what context you see in the iteration body below — be
    skeptical of convenient omissions. If a prior suspicion is not mentioned
    in this iteration's "Changes Since Last Review", that itself is a signal.

    ## Previous Review Summary (Iteration N-1)
    - Previous Score: X/10
    - Previous Verdict: [ready/almost/not ready]
    - Previous Key Weaknesses: [list]

    ## Per-claim verify state (from /auto-verify, refreshed for this iteration)
    verify_passed:                  [<ids or "none">]
    verify_failed:                  [<ids or "none">]
    verify_inconclusive:            [<ids or "none">]
    verify_zero_eligible_variants:  [<ids or "none">]
    verify_integrity_only:          [<ids or "none">]   # Stage 2 skipped; no back-edge action (upgrade dispatched by stage2_skip_reason)

    ## Changes Since Last Review
    1. [Action 1]: [result]
    2. [Action 2]: [result]

    ## Updated Results
    [paste updated metrics/tables]

    Please re-score and re-assess:
    1. Score this work 1-10 for a top venue.
    2. For each FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS claim, name the MINIMUM
       fix and tag it with routing type (①/②/③). Reject ③ on INCONCLUSIVE claims.
       Reject ③ if claim-reentry sub-budget is exhausted.
    3. State clearly: is this READY for submission? Yes/No/Almost. READY requires all
       non-deferred claims in PASS state.
    4. **Memory update**: list any new suspicions, unresolved concerns,
       or patterns you want to track in future iterations. Output as a
       `## Memory update` section so Phase B.5 can copy it verbatim.

    Be brutally honest. Actively look for things the author might be hiding.
```

The same prepend rule applies when Phase A uses the curl fallback instead of MCP — concatenate the memory block + previous-review-summary block before the iteration body in the `messages[].content` field. The memory block is **skipped only on iteration 1** (no file yet); from iteration 2 onward it is mandatory whenever `REVIEWER_MEMORY_DOC` exists non-empty.
