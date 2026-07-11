---
name: auto
description: "Autonomous pipeline: claim → experiment (mechanism routing folded in) → verify → iteration. Each stage is delegated to an isolated agent with its own context window and configurable model. Gates are AUTO_PROCEED-governed; defaults run end-to-end without human input. Use when user says \"auto pipeline\", or wants the core stages chained without confirmation."
argument-hint: [research-direction (optional; falls back to task.md when omitted)]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, AskUserQuestion, Skill, CronCreate, CronList, mcp__llm-chat__chat
---

# Auto Pipeline: Idea → Experiments → Verify → Review

End-to-end autonomous run for: **$ARGUMENTS** (when provided) or the project's `task.md` (when `$ARGUMENTS` is empty).

Each stage runs in a dedicated agent (isolated context + configurable model). The orchestrator only sees each agent's final summary and the files on disk — it uses those to fire the gates between stages.

> **⏰ First action — register the hourly notification timer.** Before any pipeline work, if `task.md` opts into notifications (see the Notifications rule in [Key Rules](#key-rules)), register a **recurring scheduled task** with `CronCreate` (cron `<off-minute> * * * *` — one call per hour, pick a minute ≠ 0/30; prompt: `/notify hourly`). This fires the hourly briefing on a real wall-clock timer instead of relying on the orchestrator remembering to poll during long waits. The timer is the **sole** source of the hourly cadence — the orchestrator never separately polls or manually fires `/notify hourly`. Register it **once, up front** — first `CronList` to check an equivalent `/notify hourly` job is not already scheduled (e.g. on resume), and skip if so. When `task.md` does **not** opt into notifications, skip this entirely (no timer). The timer covers only the hourly cadence; the event-driven `/notify` touchpoints (progress / done / halted / approval-needed) are separate and stay orchestrator-initiated (see [Key Rules](#key-rules)).

**Direction source resolution:**

- `$ARGUMENTS` non-empty → use it as the research direction; if `task.md` also exists, the claim agent treats `task.md` as authoritative detailed context (current behavior).
- `$ARGUMENTS` empty + `task.md` exists → use `task.md` as the sole direction source; pass `direction: ""` to the claim agent so it relies entirely on `task.md`.
- `$ARGUMENTS` empty + `task.md` absent → stop and report `[direction] no input — provide $ARGUMENTS or create task.md`. Do not invent a direction.

## Defaults

| Flag | Default | Effect |
|---|---|---|
| `AUTO_PROCEED` | `true` | When `true`, gates skip the UI prompt entirely and directly pick the recommended option. When `false`, the orchestrator calls `AskUserQuestion` and waits for the user. |
| `RESUME` | `false` | When `true`, the orchestrator skips any stage whose final artifacts already exist non-empty on disk, and forwards `resume: true` to each invoked agent so sub-skills can do phase-level skipping too. Useful for picking up after a crash, or for re-running only the missing stages. Default `false` = always run every stage from scratch (and overwrite previous artifacts). |
| `REVIEW_LOOP` | `true` | Run iteration after verify; set `false` to stop at verify. |
| `MODEL` | _none_ | Global model **family** alias applied to every stage whose `<STAGE>_MODEL` is unset. Accepts `opus` / `sonnet` / `haiku` (case-insensitive). Per-stage `<STAGE>_MODEL` always wins over this. When both `MODEL` and `<STAGE>_MODEL` are unset, the stage falls back to its agent frontmatter default. |
| `<STAGE>_MODEL` | _none_ | Per-stage model **family** override for any of `CLAIM`, `EXPERIMENT`, `VERIFY`, `ITERATION`. Accepts **only family aliases**: `opus`, `sonnet`, `haiku` (case-insensitive). When unset, falls back to the global `MODEL` flag (if set), then to the agent frontmatter default (currently claim/experiment/iteration = `claude-opus-4-7`, verify = `claude-sonnet-4-6`). **Version pinning is managed only in `agents/<name>.md` frontmatter** — to change the pinned version, edit the agent file directly (one source of truth, fully tracked in git). Pinned IDs are not accepted on the CLI because the Agent tool's `model` parameter schema is restricted to family aliases; passing a pinned ID at the CLI level would fail schema validation. |
| `DIMENSIONS` | `model` | Verify swap axes — and therefore **the variant count per picked claim**, since verify runs exactly one swap per listed axis. List or comma-separated subset of `{method, dataset, model}`. Default `model` → 1 variant/picked-claim (fast, single-axis model swap). Broaden with `dimensions: method,dataset,model` → 3 variants/picked-claim (full stress test). Forwarded to verify agent. |
| `TARGET_CLAIMS` | `all` | Which claims verify stress-tests: `all` (default; covers both main-experiment-supported and main-experiment-rejected claims so robustness is checked in both directions) / `passed` (only main-experiment-supported = `claim_supported = pass`) / `failed` (only main-experiment-rejected = `claim_supported = fail`) / a specific claim id. Note `passed ∪ failed = all`. Forwarded to verify agent. |
| `MAX_VERIFY_CLAIMS` | `1` | Cap on how many Stage-1-admitted claims proceed into Stage 2 (swap variants). Stage 1 (main-experiment integrity audit) **always audits every target claim regardless** — the cap only gates Stage 2 entry. When the admitted pool exceeds the cap, `/auto-verify`'s Phase 3 step 0 picks the top-K by importance judgment (reading each admitted claim's statement against upstream narrative like `IDEA_REPORT.md` / `## Rationale`; row order is NOT a priority signal). Un-picked admitted claims are marked `INTEGRITY_ONLY` with `stage2_skip_reason: max_verify_claims_cap` in `VERIFY_REPORT.md`; user can swap-test them later via `/auto-verify <id> — resume: true` (Stage 1 audit is reused via RESUME). Forwarded to verify agent. At the default cap of 1 with default `DIMENSIONS=model`, verify launches 1 × 1 = 1 variant run per `/auto` pass. |
| `ROBUSTNESS_THRESHOLD` | `0.5` | A claim PASSes verify iff `robustness ≥ ROBUSTNESS_THRESHOLD`. Set higher (e.g., `0.67`) for stricter publication-ready verification, lower (`0.33`) for exploratory work. Forwarded to verify agent. |
| `MIN_VARIANTS_FOR_VERDICT` | `1` | Minimum number of integrity-clean variants required to issue a PASS / FAIL verdict on a claim. Default `1` means a single eligible variant still yields a verdict; `N_eligible < MIN_VARIANTS_FOR_VERDICT` triggers **ZERO_ELIGIBLE_VARIANTS** (a distinct terminal state from INCONCLUSIVE — see `auto-verify/SKILL.md` Phase 10). Raise to `2`/`3` for stricter projects where you want multiple independent axes to agree before issuing PASS / FAIL. Forwarded to verify agent. |
| `BASE_REPO` | _none_ | GitHub repo URL to clone before implementing. |
| `RESEARCH_DOMAIN` | `auto` | Project domain tag (e.g. `mechanistic-interpretability`, `vision-encoders`, `rl-policy-eval`). Used to gate mechanism-family routing and downstream auxiliary decisions. Default `auto`: orchestrator forwards `auto` to the experiment agent and the sub-skill infers from `FINAL_PROPOSAL.md`; if inference is ambiguous, silently falls back to `general` regardless of `AUTO_PROCEED` (no UI prompt). To force a specific domain, set this flag explicitly on the CLI. |
| `COMPACT` | `false` | Generate compact summary artifacts: `idea-stage/IDEA_CANDIDATES.md` after claim, `refine-logs/EXPERIMENT_LOG.md` after experiment, skip per-claim `verify/<claim_dir>/ROBUSTNESS.md` (where `<claim_dir>` = `<claim_id>_<short_claim>` on disk; see `skills/auto-verify/SKILL.md` "Directory Layout"). Forwarded to claim / experiment / verify agents. |
| `CODE_REVIEW` | `true` | External LLM reviewer checks experiment + verify-variant code before deployment. Set `false` to skip. Forwarded to experiment + verify agents. |
| `SANITY_FIRST` | `true` | Run the smallest/cheapest run first to catch setup bugs before launching the full suite. Forwarded to experiment + verify agents. |
| `AUTO_DEPLOY` | `true` | Auto-deploy after implementation + review; set `false` to pause for manual inspection. Forwarded to experiment + verify agents. |
| `MAX_PARALLEL_RUNS` | `4` | Max concurrent `/run-experiment` calls dispatched within the experiment / verify stages. Becomes `max_parallel:` in the `/experiment-queue` manifest when Phase 4 of experiment routes to the queue path. Forwarded to experiment + verify agents. |
| `BATCH_DISPATCH` | `auto` | Phase 4 dispatch routing rule (experiment stage). `auto` (default) lets `/auto-experiment` auto-pick `/run-experiment` for small milestones (≤ 5 ad-hoc runs) and `/experiment-queue` for large or dependency-laden ones (≥ 10 runs, `depends_on`, grid expansions, ≥ 3-seed × ≥ 3-config sweeps). `queue` forces every milestone to `/experiment-queue`; `direct` forces every milestone to `/run-experiment` (debug-only — emits a warning if it overrides the queue rule). Forwarded to experiment agent. |
| `REF_PAPER` | `false` | Reference paper for the claim stage to summarize first. Accepts a local PDF path, an arXiv abs URL, or any paper URL. When set, claim Phase 0.5 writes `idea-stage/REF_PAPER_SUMMARY.md` and downstream idea generation builds on it. Forwarded to claim agent as `ref_paper:`. |
| `BEHAVIOR_SOURCE` | `given` | **Behavior stage** — controls where the behavior to study comes from and whether it is validated. Three values: **`given`** (default): the behavior is already specified in the direction / `task.md` and **assumed to hold** — no ideation, no novelty check, **no M0 validation**; the claim stage faithfully captures it and goes straight to the mechanism. **Precondition enforced by the Given-Behavior Comprehension Gate** (see the claim stage): `task.md` must name a *concrete* behavior; if it names only a topic, the orchestrator asks the user to specify a behavior or switch to `discovery` (this gate always waits — even in full-auto). **`given-validation`**: the behavior is given the same way (faithfully captured from `task.md`, no mining, no ideation, no novelty) **but its existence is validated first** — the experiment plan opens with a hard **M0 phenomenon-validation gate** that the experiment stage runs before any mechanism compute. **`discovery`**: the behavior itself is mined — load `/mechanism-behavior-discovery` to *sharpen* a *new* candidate phenomenon and run the full ideation pipeline (research-lit → idea-creator → novelty-check → impact-check → research-review → research-refine-pipeline; final idea chosen by impact-first, novelty-second), then the experiment plan opens with the **M0 gate** too. The M0 four-state verdict (`established`/`conditional` proceed; `not-established` ends the pipeline with a negative-result report skipping verify+iteration; `inconclusive` re-runs M0) applies to both `given-validation` and `discovery`. Accepts `given` / `given-validation` / `discovery` (case-insensitive). Forwarded to the claim agent as `behavior_source:`. |
| `MECHANISM` | `discovery` | **Mechanism stage** — controls who picks the mechanism method. **`discovery`** (default): the system selects the mechanism family — the experiment stage runs `/mechanism-skills` routing (route_only → auto-select the recommended candidate, or the family mini-prompt when `AUTO_PROCEED=false`) and the claim stage loads `/mechanism-explore` to shape the hypothesis direction + experiment plan. **`given`**: the user has specified the mechanism method/family in `task.md` — the claim stage captures it and the experiment stage commits it **directly** (Phase 1.5 Mode B, `CHOSEN_FAMILY=<the method>`), bypassing routing and the family mini-prompt; `task.md` **must** name a concrete mechanism method/family, else the claim stage halts (report it back). Accepts `given` / `discovery` (case-insensitive). Forwarded to the claim agent as `mechanism:`. **Resource fidelity:** the claim stage stamps `resource_fidelity: strict` into `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md` **iff `BEHAVIOR_SOURCE=given` AND `MECHANISM=given`** (the reproduction combination) — the experiment stage then enforces the **Resource-Fidelity Harness** on the main experiment (exact models/datasets at full scale — no smaller-model swap, no data subsetting, no skipped must-run runs; OOM handled by batch↓/grad-accum/sharding/offload, HALT rather than downscale; verify is exempt, its swaps are intentional). Every other combination leaves the marker unstamped, so model/dataset choice is unconstrained (cost-aware). |
| `MAX_ITERATIONS` | `6` | Iteration agent: max total back-edge actions (variant fix / plan+script fix / claim-stage re-entry) before stopping. Counts every back-edge uniformly; new claims produced by claim-stage re-entry inherit the same budget (no fresh allocation). Forwarded to iteration agent. Legacy alias `MAX_ROUNDS` is accepted at the CLI for one release and silently normalized to `MAX_ITERATIONS`. |
| `MAX_CLAIM_REENTRIES` | `2` | Iteration agent: sub-budget within `MAX_ITERATIONS` for claim-stage re-entries (action type ③ — see `auto-iteration-loop/SKILL.md`). Prevents the failure mode where the reviewer keeps requesting claim rewrites without anyone fixing the experiments behind them. When exhausted, the iteration loop refuses further ③ actions even if iterations remain. Forwarded to iteration agent. |
| `TARGET_SCORE` | `6` | Iteration agent: stop early when score ≥ this AND verdict is `ready`/`almost` AND no FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS claim remains (three-dimensional STOP rule). |
| `GPU_ID` | `auto` | GPU device(s) to pin every experiment / verify-variant / iteration-round run to. `auto` lets each sub-skill inherit from the environment / launcher (no pinning). A single id (`0`) or comma-list (`4,5,6,7`) causes the sub-skill to **pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional argument to `/run-experiment`** (and sanity runs); `/run-experiment` is a Skill, not a shell command, so it cannot accept a shell prefix — instead it parses this positional arg and exports `CUDA_VISIBLE_DEVICES` itself before launching the experiment subprocess. Forwarded to experiment + verify + iteration agents (iteration's Phase-C `/run-experiment` dispatches inherit the same pin). |
| `OOM_MAX_GPUS` | `4` | **`resource_fidelity: strict` only (the `BEHAVIOR_SOURCE=given` + `MECHANISM=given` reproduction combo).** Upper bound on how many free GPUs the Resource-Fidelity Harness may auto-add to a single OOM'd run before halting. On OOM the harness queries free GPUs (`memory.used < 500 MiB`), auto-adds them to the run and enables sharding — auto-converting a single-GPU script (`model.cuda()` / `.to(device)`) to `device_map="auto"` / FSDP / CPU-or-disk offload, first verified numerically equivalent on a fit-on-one-GPU proxy slice — repeating up to this cap while leaving `MAX_PARALLEL_RUNS` headroom for sibling runs. Only after the cap is hit (or no free GPU remains) **and** CPU/disk offload is exhausted does it HALT — and **never** by downscaling (smaller model / subset data stay forbidden, even in full-auto). Set higher to let one big run spread across more devices; `auto` lets it use all currently-free GPUs. Forwarded to experiment + verify + iteration agents. Ignored when the strict marker is absent (every non-reproduction combination). |
| `UNDERPOWER` | `tag` | **Active whenever the strict marker is absent** (ignored under `resource_fidelity: strict` — the reproduction combo — which already forbids subsetting). Guards against an under-powered cheap run's weak/negative verdict being mistaken for a *real* negative. After the experiment, a claim whose main-experiment verdict is weak (`not-supported` / `partial` / null) **and** whose realized scale is materially below the plan (`used_n` shortfall, fewer seeds, or fewer grid/checkpoint points than `EXPERIMENT_PLAN.md`) is flagged **suspected under-power**. `tag` (default): tag the claim `[suspected under-power: used_n X/Y, seeds A/B, grid P/Q]` (recorded as a **provisional** caveat carried into the ledger + verify + iteration, so the negative is treated as provisional, not a confirmed falsification) and proceed — respecting the cost-aware design; under `AUTO_PROCEED=false` the experiment agent instead asks (full re-run / targeted-milestone re-run / accept demo-scale). `stop`: treat a suspected-under-power claim as a **Round-End Decision** (`ended-needs-decision (experiment: suspected-under-power)`) even under `AUTO_PROCEED=true`, so you decide whether to re-run at full scale before verify trusts it. `off`: disable the check. Forwarded to experiment agent. |
| `LEDGER_FIGURES` | `auto` | Whether the final ledger render should call `/paper-figure` to produce per-claim plots **and tables** embedded into `CLAIMS_LEDGER.md` (image figures = PNG inline + PDF link; tables = Markdown inline + `.tex` link). Tri-state: `auto` (default) generates figures only for claims with at least one plottable or tabulable data source; `true` forces an attempt for every non-deferred claim (an unsupported claim still degrades to a `skipped` entry, never a halt); `false` disables the hook entirely and the ledger renders without a `Figures` bullet. Fires **once per pipeline run**, at the final ledger hook only (`iteration:final`, or `verify` when `REVIEW_LOOP=false`); intermediate hooks never re-invoke `/paper-figure`. See [Ledger Figures hook](#ledger-figures-hook). |

Override on the CLI, e.g. `/auto "direction" — auto-proceed: false, claim-model: opus, verify-model: sonnet, dimensions: method,dataset, code-review: false`. **Canonical CLI form is hyphen-separated** (`auto-proceed`, `claim-model`, `code-review`, ...). The parser also accepts underscore (`auto_proceed`) and uppercase env-style (`AUTO_PROCEED`) for compatibility — see "Argument parsing" below.

Pass each flag to the agent(s) listed in its "Forwarded to" hint as the corresponding arg in `agents/<name>.md`'s Invocation contract (e.g., `COMPACT` → `compact:`, `CODE_REVIEW` → `code_review:`).

### Argument parsing

`$ARGUMENTS` is shaped as `"<direction>" — <key>: <value>, <key>: <value>, ...`. Both the direction and the option list are independently optional. The orchestrator parses it as follows:

1. **Direction (positional, optional)** — everything before the first ` — ` (em dash with spaces) or `--` is the research direction; pass it to the claim agent as `direction:`. When omitted (empty `$ARGUMENTS`, or `$ARGUMENTS` starts directly with ` — ` / `--`), pass `direction: ""` and rely on `task.md` (see "Direction source resolution" above). If both are absent, stop and report rather than inventing a direction.
2. **Options (after ` — ` or `--`)** — comma-separated `key: value` pairs. Whitespace around `:` and `,` is ignored. Quoted strings keep their content.
3. **Key normalization** — lower-case, hyphens → underscores, then upper-case for the env-style flag (`auto-proceed` / `auto_proceed` → `AUTO_PROCEED`; `verify-model` → `VERIFY_MODEL`).
4. **Model values** — for both `MODEL` (global) and `<STAGE>_MODEL` (per-stage), the value must be one of the family aliases `opus` / `sonnet` / `haiku` (case-insensitive; lowercase before passing through). Anything else is a parse error — log `[arg-parse] <key>: "<value>" is not a family alias (opus|sonnet|haiku) — version pinning is managed in agents/<name>.md frontmatter, not on the CLI` and stop. To change the pinned version of a stage, edit that agent file directly.
5. **Bool values** — `true` / `false` / `1` / `0` / `yes` / `no`. Anything else is a parse error.
6. **Enum string values** — documented set or fall back to default with a log line:
   - `BATCH_DISPATCH` accepts `auto` / `queue` / `direct` (case-insensitive; lowercase before passing through). On unknown value: log `[arg-parse] BATCH_DISPATCH: "<value>" not in {auto, queue, direct} — falling back to default 'auto'` and continue with the default.
   - `BEHAVIOR_SOURCE` accepts `given` / `given-validation` / `discovery` (case-insensitive; lowercase before passing through). On unknown value: log `[arg-parse] BEHAVIOR_SOURCE: "<value>" not in {given, given-validation, discovery} — falling back to default 'given'` and continue with the default.
   - `MECHANISM` accepts `given` / `discovery` (case-insensitive; lowercase before passing through). On unknown value: log `[arg-parse] MECHANISM: "<value>" not in {given, discovery} — falling back to default 'discovery'` and continue with the default.
   - Other future enum flags follow the same pattern.
7. **Unknown keys** — log `[arg-parse] unknown key: <name> — ignoring` and continue. The legacy `MODE` flag is **removed**: a passed `mode:` is an unknown key (ignored with the log line) — use `behavior-source` + `mechanism` instead (old `mode: reproduction` ≡ `behavior-source: given, mechanism: given`; old `mode: discovery` is the default and implied by any non-reproduction combination).

All three of these invocations resolve to the same flags. The first (hyphen-separated) is the canonical form; the other two are accepted for compatibility — prefer the canonical form when writing new docs / examples / scripts.

```
# Canonical: hyphen-separated, lowercase
/auto "direction" — auto-proceed: false, claim-model: opus, verify-model: sonnet, dimensions: method,dataset

# Also accepted: underscore form
/auto "direction" -- auto_proceed: false, claim_model: opus, verify_model: sonnet, dimensions: method,dataset

# Also accepted: uppercase env-style
/auto "direction" — AUTO_PROCEED: false, CLAIM_MODEL: opus, VERIFY_MODEL: sonnet, DIMENSIONS: method,dataset
```

## Retrieval rule

The claim agent's Phase 1 `research-lit` step must follow the requirements in `skills/research-lit/SKILL.md`, and `mechanic-db-search` must be executed, not skipable.

In other subagents, they may freely choose any retrieval source — WebSearch, WebFetch, MCP tools, or their own bundled `scripts/` helpers. The orchestrator does **not** constrain the tool. 

## Overview

```
/auto (orchestrator)
    │
    ├─ claim       [claude-opus-4-7]     → idea-stage/IDEA_REPORT.md
    │       │                              refine-logs/FINAL_PROPOSAL.md
    │       │                              refine-logs/EXPERIMENT_PLAN.md
    │       │  (internal chain depends on BEHAVIOR_SOURCE (behavior origin + ideation + M0) and
    │       │   MECHANISM (routing vs. user-given family; when MECHANISM=discovery the chain loads
    │       │   /mechanism-explore to shape the hypothesis direction + experiment plan):
    │       │     given            — [Given-Behavior Comprehension Gate: concrete behavior in task.md? no → ask user: switch-to-discovery (default) | specify-behavior]
    │       │                        research-lit → faithful behavior capture → [MECHANISM=discovery: /mechanism-explore] → research-refine-pipeline   (no ideation, no novelty, NO M0)
    │       │     given-validation — [Given-Behavior Comprehension Gate] research-lit → faithful behavior capture → [MECHANISM=discovery: /mechanism-explore] → research-refine-pipeline (plan opens with M0 gate; no ideation, no novelty)
    │       │     discovery        — research-lit → /mechanism-behavior-discovery → idea-creator → novelty-check → impact-check → research-review → [MECHANISM=discovery: /mechanism-explore] → research-refine-pipeline (plan opens with M0 gate)
    │       │   resource_fidelity: strict is stamped iff BEHAVIOR_SOURCE=given AND MECHANISM=given (the reproduction combo).
    │       │   MECHANISM=given captures the user's mechanism method from task.md → forwarded to experiment as CHOSEN_FAMILY.)
    │       └─ Claim Gate
    │
    ├─ experiment  [claude-opus-4-7]
    │       ├─ Phase 1.25 (BEHAVIOR_SOURCE ∈ {given-validation, discovery} — fires on the plan's M0 marker): Phenomenon-Validation Gate M0 — run M0 first → 4-state:
    │       │     established/conditional → continue ; not-established → 🛑 end pipeline (negative report, skip verify+iteration) ; inconclusive → fix & re-run M0
    │       ├─ (MECHANISM=given → skip Call A + mini-prompt; read chosen_mechanism: from EXPERIMENT_PLAN.md → Call B with CHOSEN_FAMILY=that value, or MECHANISM_ROUTING=not-applicable when it is behavioral-only)
    │       ├─ Call A (mode=route_only) → refine-logs/MECHANISM_ROUTING.md (2–3 candidates)   [MECHANISM=discovery only]
    │       ├─ 🔸 Mini-prompt: pick mechanism family (AUTO_PROCEED=true → skip prompt, pick recommended)   [MECHANISM=discovery only]
    │       └─ Call B (mode=build, chosen_family=X)
    │               → Phase 4 dispatch fork (per-milestone routing):
    │                   ├─ ≥10 runs / depends_on / grid → /experiment-queue (batch scheduler with OOM retry, stale cleanup, GPU gate, phase deps)
    │                   └─ else                          → /run-experiment per run (direct dispatch)
    │               → refine-logs/EXPERIMENT_RESULTS.md, refine-logs/EXPERIMENT_TRACKER.md
    │               → MECHANISM_ROUTING.md with committed: true
    │           └─ Experiment Gate (inside agent)
    │
    ├─ verify      [claude-sonnet-4-6]
    │       ├─ Phase 2   : per-claim main-experiment integrity audit (Stage 1 gate)
    │       │              — /experiment-audit + /mechanism-audit on refine-logs/
    │       ├─ Phase 3–7 : pick within-family method swap (+ data/model swaps), run variants
    │       ├─ Phase 8   : /result-to-claim per variant → consistent_with_main_experiment
    │       ├─ Phase 9   : per-claim variant integrity audit (symmetric to Phase 2)
    │       ├─ Phase 10  : compute robustness → PASS / FAIL / ZERO_ELIGIBLE_VARIANTS
    │       └─ write verify/VERIFY_REPORT.md, verify/INTEGRITY_AUDIT.md, verify/<claim_dir>/ROBUSTNESS.md
    │       └─ Verify Gate (AUTO_PROCEED-governed, same as Claim/Experiment gates)
    │
    └─ iteration   [claude-opus-4-7]     → review-stage/AUTO_REVIEW.md, REVIEW_STATE.json,
            (skipped when REVIEW_LOOP=false)   REVIEWER_MEMORY.md, AUTO_ITERATION_FINAL_REPORT.md
```

## Pipeline

### Multi-round guard (run first)

Before anything else, protect a prior round's outputs from being silently overwritten. When `RESUME=false` (a fresh run) AND un-archived prior-round artifacts are present at the project root — test `[ -s CLAIMS_LEDGER.md ]` **or** `[ -s refine-logs/FINAL_PROPOSAL.md ]` existing **outside** any `rounds/` folder — a previous round's outputs have not been archived, and starting fresh would overwrite them. Do **not** proceed silently. Halt with:

```
[multi-round] un-archived prior-round artifacts detected (CLAIMS_LEDGER.md / refine-logs/...).
A fresh /auto would overwrite them. Choose one:
  • /next-round   — archive this round into rounds/round_<N>/ and draft the next task.md (recommended)
  • RESUME=true   — continue the existing (unfinished) round instead of starting fresh
  • delete the listed artifacts manually to intentionally overwrite
Aborting.
```

This guard is **independent of `AUTO_PROCEED`** — it is data-protective and the remedy is a single user action, so it halts rather than auto-overwriting even in full-auto mode. It is skipped when `RESUME=true` (continuing is the intent) and when no such artifacts exist (a true first round). See [Global Exploration Memory](#global-exploration-memory-cross-round) and the `/next-round` skill.

### Resume-mode setup (only when `RESUME=true`)

Skip entirely if `RESUME=false` (default). When `true`:

Before invoking each stage's agent, check whether the stage is already complete by testing the existence and non-emptiness (`[ -s <path> ]`) of its **stage-completion artifacts**:

| Stage      | Stage-completion artifacts (all must exist non-empty to count as "done") |
|---|---|
| claim      | `idea-stage/IDEA_REPORT.md`, `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`. |
| experiment | `refine-logs/MECHANISM_ROUTING.md` (with `committed: true`), `refine-logs/EXPERIMENT_RESULTS.md`, `refine-logs/EXPERIMENT_TRACKER.md`. **Exception (phenomenon-terminated):** if `EXPERIMENT_RESULTS.md` carries `phenomenon_status: not-established` (or terminal `inconclusive`), the stage counts as done with no `MECHANISM_ROUTING.md`/`EXPERIMENT_TRACKER.md` required — the M0 gate ended the run before mechanism work (see the experiment resume branch's case 0). |
| verify     | `verify/VERIFY_REPORT.md` AND `verify/INTEGRITY_AUDIT.md` — both required, AND `INTEGRITY_AUDIT.md` must contain a non-empty `## Variant integrity (Phase 9)` section (a file with only the `## Main-experiment integrity (Phase 2, per-claim)` section is an incomplete run and must re-execute Phase 9). When Phase 2 returned `fail` on every target claim and Phase 9 was legitimately short-circuited, the Phase 9 section still exists, populated as `[skipped — all main-experiment audits FAIL]`. Per-claim main-experiment audit JSON `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.json` must exist non-empty for **every** target claim — glob-expand `verify/<claim_id>_*/main_experiment_audit/` for each. ("at least one" is too weak: the `[skipped — all main-experiment audits FAIL]` short-circuit asserts *all* main experiments failed, so if any target claim has no main-experiment audit on disk the prior run was partial — re-run, don't skip.) Do not test the bare `verify/main_experiment_audit/` (the legacy flat layout). |
| iteration  | `review-stage/AUTO_REVIEW.md`, `review-stage/REVIEW_STATE.json`, `review-stage/AUTO_ITERATION_FINAL_REPORT.md` (written by the iteration agent's Termination once `status=completed`; absence with `status=completed` means the agent crashed before report assembly and the stage must be resumed) |

If every artifact for a stage is present non-empty, the orchestrator:
1. **Does not invoke that stage's agent.**
2. Logs `[resume] stage=<name> skipped — artifacts present: <comma-separated list>`.
3. Reads the stage's existing artifacts as if the agent had just produced them, fires the stage's Gate normally (which under `AUTO_PROCEED=true` is a no-op), and moves to the next stage.

If any artifact is missing or empty, the stage's agent **is** invoked, with `resume: true` forwarded so the agent can still apply phase-level skipping inside the skill. This way a half-done stage finishes the remaining phases instead of restarting from scratch.

Log on entry:
```
[resume-mode] resume=true — completed stages: <claim,experiment,...>; will resume from: <first-incomplete-stage>
```

Note: `RESUME=true` never deletes or overwrites pre-existing artifacts on its own. If you want a clean run, either set `RESUME=false` (default) or remove the relevant files manually.

### Resolve per-agent models

Resolution order (per stage, evaluated independently for `claim` / `experiment` / `verify` / `iteration`):
1. If the user passed `<STAGE>_MODEL=<alias>` on the CLI (`opus` / `sonnet` / `haiku` only), use it. Pass the alias **as-is** to the Agent tool's `model` parameter. The Agent tool then routes to the alias's current latest version.
2. Else if the user passed the global `MODEL=<alias>` on the CLI, use that alias for this stage.
3. Else omit the `model` parameter when calling the Agent tool — the agent falls back to its frontmatter `model:` line, which is the **only** place version pinning lives.

| Agent | Frontmatter pin (source of truth, edit here to bump version) | CLI override accepted |
|---|---|---|
| claim      | `claude-opus-4-7`   | `claim-model: opus \| sonnet \| haiku` (or global `model:`)      |
| experiment | `claude-opus-4-7`   | `experiment-model: opus \| sonnet \| haiku` (or global `model:`) |
| verify     | `claude-sonnet-4-6` | `verify-model: opus \| sonnet \| haiku` (or global `model:`)     |
| iteration  | `claude-opus-4-7`   | `iteration-model: opus \| sonnet \| haiku` (or global `model:`)  |

Log on entry:
```
[models] claim=<frontmatter-pin or alias>  experiment=...  verify=...  iteration=...  (override-source: CLI-stage | CLI-global | frontmatter per stage)
```

When a CLI alias is supplied (per-stage or global), the log line shows the alias rather than the frontmatter pin (since the alias is what the runtime actually used).

### claim — Idea Discovery

**Resume check (only when `RESUME=true`)**: if all three claim stage-completion artifacts exist non-empty, log `[resume] stage=claim skipped — IDEA_REPORT.md, FINAL_PROPOSAL.md, EXPERIMENT_PLAN.md present` and **do not invoke the claim agent**; jump straight to the Claim Gate using the existing files. Otherwise invoke the agent with `resume: true` forwarded so it can phase-skip internally.

Invoke the claim agent with a self-contained natural-language prompt that **opens with the two injected blocks — `## HARD CONSTRAINTS (from task.md — non-negotiable)` then `## NOTICE (from task.md — informational)`** (see the Key Rules "Injecting `task.md`" bullet; the **claim agent receives the full union of both** — every stage's items — because it authors `EXPERIMENT_PLAN.md` for all downstream stages) and then includes: the research direction, a pointer to `task.md` if it exists, the retrieval rule, `AUTO_PROCEED`, `RESUME`, and the expected output paths. The same two blocks are prepended to every other stage agent's dispatch prompt (experiment / verify / iteration) — but **stage-scoped**: each downstream agent gets only the items routed to it (per the targeting rules), re-injected on every stage and every resume.

**↳ Global memory read (default on; no-op only in the reproduction combo `BEHAVIOR_SOURCE=given` + `MECHANISM=given`).** When `research_memory.json` exists at the project root, pass `research_memory: research_memory.json` to the claim agent so the strategy skills avoid re-doing concluded work — `BEHAVIOR_SOURCE=discovery` avoids behaviors whose `status ∈ {established, conditional, not-established}` (all settled; `inconclusive` stays a retry candidate); `BEHAVIOR_SOURCE ∈ {given, given-validation}` avoids, for the matched behavior, any `(mechanism direction, family)` whose `headline` + `claims[].conclusion` prose reads as stable positive or stable negative per Rule 1 (mixed / deferred / integrity-broken / under-power all stay retry candidates). An explicit pin in `task.md` (behavior / direction / family) overrides this avoidance (Rule 2). **Before dispatching the claim agent, the orchestrator checks for a settled-pin conflict here** (it already holds both `task.md` and `research_memory.json`): scan `task.md` for the pinned behavior (the `given` behavior) and any `mechanism direction:` / `family:` line, and — for direction/family pins — read the matched behavior's `mechanisms[]` entries (`headline` + `claims[].conclusion`) to decide whether the pinned pair is already settled per Rule 1. **On a hit, resolution respects `AUTO_PROCEED` and keys on the `retry-settled` marker in `task.md`** (see Rule 2): when `task.md` carries `retry-settled: true`, resolve to `honor-pin` (the user explicitly authorized re-doing settled work); otherwise — `AUTO_PROCEED=true` resolves to `pick-fresh` **silently** (log `[settled-pin] <pinned item> already settled in round <N>, no retry-settled marker — picking a fresh untried <level>`), `AUTO_PROCEED=false` calls `AskUserQuestion` (`honor-pin` vs `pick-fresh`, recommended `pick-fresh`) and blocks. Pass the resolved decision into the claim agent's prompt as `pin_resolution: honor-pin | pick-fresh`. When **no** conflict is detected (pin present but not settled, or no pin), pass **no** `pin_resolution` — the claim agent then honors any pin as written (Rule 2). (The claim agent re-checks settled status as a backstop against a missed semantic match — see `agents/claim.md` step 0.5.) No flag governs the read (on by default); pass `research_memory: false` only in the reproduction combo (`BEHAVIOR_SOURCE=given` + `MECHANISM=given`) or when the file is absent (round 1). See [Global Exploration Memory](#global-exploration-memory-cross-round).

**↳ Given-Behavior Comprehension Gate (`BEHAVIOR_SOURCE ∈ {given, given-validation}` only; fires independent of `AUTO_PROCEED` — always waits for the user, like the multi-round guard; note the settled-pin gate does NOT, it respects `AUTO_PROCEED`).** Both `given` and `given-validation` take the behavior **as written in `task.md` / the inline direction** (they differ only in whether M0 later validates it) — so before dispatching the claim agent, the orchestrator (it already holds `task.md`) checks that a concrete behavior is actually present. A **concrete behavior** names a specific, falsifiable model-observable output pattern, ideally with its triggering condition — e.g. *"the model rates first-person `I believe X` as less likely true than the matched third-person assertion"* — as opposed to a bare topic / research direction — e.g. *"explore the mechanics of LLM beliefs"*. An explicit Rule-2 pinned behavior in `task.md` always counts as concrete.
- **PASS** (a concrete behavior is present) → proceed with the requested `behavior_source` as-is; pass no extra field.
- **FAIL** (only a topic / direction, no concrete behavior) → **halt and `AskUserQuestion`** (independent of `AUTO_PROCEED`), two options:
  - **switch to discovery** *(recommended)* → re-dispatch the claim stage with `behavior_source: discovery`, so the phenomenon is mined (`/mechanism-behavior-discovery`) and then **hard-gated by M0** before any mechanism work.

  This gate **always waits** for the user's answer — there is no timeout, no auto-abort, and no silent auto-fallback even under `AUTO_PROCEED=true` (`AskUserQuestion` blocks indefinitely; a vague given direction is a decision only the user can make).
  - **specify the behavior** → the user supplies the concrete phenomenon as free text; inject it into the claim agent's prompt as `given_behavior: "<text>"` and proceed with the requested `behavior_source`.

  Rationale: running `given` / `given-validation` on a vague direction would make the claim stage silently **invent** a behavior — this gate forces either a user-pinned/clarified behavior or the M0-protected `discovery` path. The claim agent re-checks this as a backstop (see `agents/claim.md` step 0.6), so standalone `/auto-claim` callers are covered too. Ignored when `BEHAVIOR_SOURCE=discovery` (discovery mines + M0-validates the phenomenon by design).

**Expected artifacts:** `idea-stage/IDEA_REPORT.md`, `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`.

**↳ Claim Ledger update:** after the Claim Gate fires, **seed** the ledger from `refine-logs/EXPERIMENT_PLAN.md` — one row per claim id with `statement`, `origin`, and the *planned* `data` (set `provenance`, `source`, `available_n`, and the *planned* `used_n`), `models`, `method`; `final_status = "planned"`. Set the global header (`project`, `direction`, `models`). See [Claim Ledger](#claim-ledger-global-living-report).

**🚦 Claim Gate:** Echo the agent's top-3 idea list, then branch on `AUTO_PROCEED` **before** any UI call:
- `AUTO_PROCEED=true` (default) → **do NOT call `AskUserQuestion`**. Directly accept the top-ranked idea from `IDEA_REPORT.md` and proceed to the experiment routing call. Log `AUTO_PROCEED: accepted top idea — [title] (no prompt shown)`.
- `AUTO_PROCEED=false` → call `AskUserQuestion` with the four choices (approve / switch / re-run / stop) and block:
  - **approve** → continue to the experiment stage with the top idea.
  - **switch <N>** → re-invoke the claim agent with `chosen_idea: <N>` so it rewrites `refine-logs/FINAL_PROPOSAL.md` and `refine-logs/EXPERIMENT_PLAN.md` for idea #N (leaving `IDEA_REPORT.md` intact), then re-open the gate.
  - **re-run** → re-invoke the claim agent with the same arguments plus the user's free-form feedback.
  - **stop** → halt the pipeline.

If `IDEA_REPORT.md` is missing, empty, or only a placeholder, re-invoke the agent with corrective context before opening the gate.

### experiment — Mechanism Routing + Build + Deploy

**Resume check (only when `RESUME=true`)**. Note on `committed` flag semantics: Mode A (`route_only`) writes the routing candidates with `committed: false`; Mode B (`build`) flips it to `committed: true` once its Phase 0 has locked in `chosen_family`. The **exception** is a `routing: not-applicable` (behavioral-only) proposal — Mode A writes `committed: true` immediately with no mechanism family, because such a proposal is by definition "committed" to having none. So `committed:true` means *either* "Mode B has at least started" *or* "Mode A wrote the not-applicable stub"; the two are disambiguated by checking for a `routing: not-applicable` line in the file.

**Pre-branch parse step (mandatory for cases 1 / 2 below):** before classifying, extract from `refine-logs/MECHANISM_ROUTING.md`:

```bash
# committed flag (last occurrence wins so Mode-B overwrites Mode-A)
committed=$(grep -E '^committed:' refine-logs/MECHANISM_ROUTING.md | tail -1 | awk '{print $2}')
# not-applicable marker
not_applicable=$(grep -cE '^routing:[[:space:]]*not-applicable' refine-logs/MECHANISM_ROUTING.md)
# chosen_family value (may be absent on a not-applicable stub)
chosen_family=$(grep -E '^chosen_family:' refine-logs/MECHANISM_ROUTING.md | tail -1 | sed 's/^chosen_family:[[:space:]]*//')
```

Then derive the value to forward to Mode B's `chosen_family:` arg:
- If `not_applicable > 0` → `chosen_family_for_mode_b = "not-applicable"` (overrides whatever the `chosen_family:` line says; not-applicable is the canonical sentinel Mode B's invocation contract accepts).
- Else if `chosen_family` is non-empty and not literal `none` → use it verbatim.
- Else (`committed:true` but no usable `chosen_family` and no `routing: not-applicable` marker) → the file is malformed; **fall back to case 3** (re-run both calls) rather than invoking Mode B with a missing required arg. Log `[resume] MECHANISM_ROUTING.md committed:true but chosen_family missing — falling back to fresh routing`.

Branch as follows (using `committed` and `chosen_family_for_mode_b` from the parse step):

0. **Phenomenon-terminated run (check first, before the `committed` cases).** If `refine-logs/EXPERIMENT_RESULTS.md` exists non-empty AND its top metadata has `phenomenon_status: not-established` (or a terminal `phenomenon_status: inconclusive`), the experiment stage's Phase 1.25 M0 gate already **ended the pipeline** on a prior run — `MECHANISM_ROUTING.md` may be absent or uncommitted, which is expected (the run stopped before mechanism routing). Do **not** re-run the experiment agent. Log `[resume] stage=experiment skipped — phenomenon_status=<not-established|inconclusive>, pipeline already ended at M0`, then **re-apply the phenomenon early exit**: skip the verify and iteration stages, and finalize state into the Ledger — set `claims_ledger.json`'s `pipeline_status = ended-phenomenon-not-established` (or `ended-phenomenon-inconclusive`), populate `journey_summary` / `open_items[]` per the [Terminal-state writeback rule](#terminal-state-writeback-ledger-only), set each affected claim's `final_status` to `✗ phenomenon not established` / `phenomenon validation inconclusive — fix M0`, and re-render `CLAIMS_LEDGER.md`. This branch takes precedence over cases 1–4 below — a terminal `phenomenon_status` is checked before the `committed`-flag parse, since on a clean negative finding there is intentionally no committed routing.

1. `committed: true` AND `EXPERIMENT_RESULTS.md` + `EXPERIMENT_TRACKER.md` exist non-empty → log `[resume] stage=experiment skipped — routing committed, results present` and skip all call(s).
2. `committed: true` but no (or empty) results files → either build previously started, locked the routing, then crashed before producing results, **or** the proposal is `routing: not-applicable` and build has never been invoked. Either way: invoke the experiment agent in build-only mode with `chosen_family: <chosen_family_for_mode_b>` and `resume: true`. Phase 0 will either resume from where it crashed (chosen_family was a real family) or take the no-mechanism path (chosen_family was `not-applicable`). This holds regardless of `AUTO_PROCEED` — the routing decision is already persisted in the file, so there is nothing to mini-prompt about.
3. `MECHANISM_ROUTING.md` exists with `committed: false` (a previous Mode A finished but build never reached its commit step — only reachable under the legacy `AUTO_PROCEED=false` two-call flow) → re-run per the Call-count rule below. Under `AUTO_PROCEED=true` this means a single combined call (Phase 0 will overwrite the stale candidates as needed); under `AUTO_PROCEED=false` it means re-running the route_only call, re-prompting the user, then the build call.
4. No `MECHANISM_ROUTING.md` at all → run per the Call-count rule below from scratch.

In all cases forward `resume: true` to whichever calls are invoked.

**`MECHANISM=given` short-circuit (both `AUTO_PROCEED` modes).** When `MECHANISM=given`, the user specified the mechanism method/family in `task.md` and the claim stage stamped it as `chosen_mechanism:` in the top metadata of `refine-logs/EXPERIMENT_PLAN.md` (and `FINAL_PROPOSAL.md`). The orchestrator reads that value:

```bash
chosen_mechanism=$(grep -E '^chosen_mechanism:' refine-logs/EXPERIMENT_PLAN.md | tail -1 | sed 's/^chosen_mechanism:[[:space:]]*//')
```

Then branch on the value, in both `AUTO_PROCEED` modes (no routing call, no family mini-prompt — the mechanism is already user-decided):
- **A real method/family** → forward `CHOSEN_FAMILY=<chosen_mechanism>` to the experiment agent and use the **build path directly (Phase 1.5 Mode B)**. This is the first-class form of the family-pin short-circuit below; both resolve to the same Mode-B direct commit.
- **`not-applicable`** (a behavioral-only reproduction — the user declared no mechanism claim) → forward `CHOSEN_FAMILY=not-applicable` to the experiment agent's build call — the **same behavioral-only sentinel** the post-routing build call already accepts (see "Special case — behavioral-only proposal" below). The experiment writes the `routing: not-applicable` stub and runs no mechanism milestone.
- **Marker absent** (`MECHANISM=given` but nothing stamped — a malformed claim output) → fall back to the normal routing branch below and log `[mechanism] MECHANISM=given but no chosen_mechanism stamped — falling back to routing`.

**Family pin short-circuit (Rule 2, both `AUTO_PROCEED` modes).** *(Applies when `MECHANISM=discovery` but `task.md` still pins a `family:`.)* If `task.md` pins a `family:` and the orchestrator's settled-pin gate (claim-stage setup) resolved it to `honor-pin` (or there was no conflict), forward `CHOSEN_FAMILY=<pinned family>` to the experiment agent and use the **build path directly (Phase 1.5 Mode B)** — this bypasses both the combined-call auto-select and the `AUTO_PROCEED=false` mini-prompt, since the family is already user-chosen. (A `pick-fresh` resolution leaves `CHOSEN_FAMILY` unset, falling through to the normal branch below, where the avoid-set excludes the settled family.)

**Call count** (branch on `AUTO_PROCEED`, when neither the `MECHANISM=given` short-circuit nor a family pin short-circuit applies — i.e. `MECHANISM=discovery` with no pin):
- **`AUTO_PROCEED=true` (default) → one combined call.** Invoke the experiment agent once with `CHOSEN_FAMILY` unset; the agent's Phase 0 Step 4 auto-selects the `[recommended]` candidate and proceeds straight into build. No orchestrator-side mini-prompt.
- **`AUTO_PROCEED=false` → two calls**: route_only → mini-prompt → build (sections below). The human picks the family.

#### Routing call (`mode: route_only`) — only when `AUTO_PROCEED=false`

Invoke the experiment agent. It reads `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md`, runs `/mechanism-skills`, and writes `refine-logs/MECHANISM_ROUTING.md` with 2–3 candidates (recommended one marked, `committed: false`).

**Special case — behavioral-only proposal:** if the agent's notes say `routing: not-applicable`, skip the mini-prompt and go straight to the build call with `chosen_family: not-applicable`.

#### 🔸 Mini-prompt — Family selection (only when `AUTO_PROCEED=false`)

Call `AskUserQuestion` and wait for the user to pick:

  ```
  question: "Which mechanism family should the experiment commit to?"
  header:   "Mech family"
  options:  [candidate 1 (recommended), candidate 2, candidate 3]
  ```

> ℹ️ **Implementation note**: `AskUserQuestion` blocks until the user responds — there is no timer mechanism behind it, and that is intentional under the binary `AUTO_PROCEED` model: `AUTO_PROCEED=true` skips this prompt entirely via the Combined call above (full auto, no human needed); `AUTO_PROCEED=false` waits indefinitely for the human (human-in-the-loop, waiting is the desired behavior). There is no third "auto-proceed after timeout" mode — the two are mutually exclusive by design.

This is a single-question selection, not a full gate.

#### Build call (`mode: build`) — only when `AUTO_PROCEED=false`

**Before invoking Mode B**, extract `chosen_idea_title` from the claim agent's return message (cached from the Claim Gate). The claim agent's output contract (see `agents/claim.md`'s "Output contract") guarantees a line of the shape `**Recommended:** #<n> — <title>` — parse the title from that line:

```bash
chosen_idea_title=$(printf '%s\n' "$claim_agent_return" \
  | grep -E '^\*\*Recommended:\*\*' \
  | head -1 \
  | sed -E 's/^\*\*Recommended:\*\*[[:space:]]*#[0-9]+[[:space:]]*—[[:space:]]*//')
```

If the parse yields an empty string (claim agent's return is malformed, or the `switch <N>` branch produced a re-run that re-wrote the report), fall back to reading the title from `idea-stage/IDEA_REPORT.md` — find the `### 🏆 Idea <CHOSEN_IDEA>:` heading (or `### Idea <CHOSEN_IDEA>:` for non-top-ranked) and take the title after the colon. If both sources fail, log `[build-call] chosen_idea_title unresolved — passing "n/a"` and forward `chosen_idea_title: n/a` (Mode B's contract says this field is for logging only, so it does not gate behavior).

Invoke the experiment agent with the chosen family and chosen_idea_title. It commits the routing, implements code, runs cross-model code review, runs sanity, deploys the full suite, and collects results.

**Expected artifacts:** `refine-logs/EXPERIMENT_RESULTS.md`, `refine-logs/EXPERIMENT_TRACKER.md`, `MECHANISM_ROUTING.md` with `committed: true`.

**↳ Claim Ledger update:** after the Experiment Gate returns, fill each claim's *actual* `data` (overwrite `used_n` with the amount actually used in the runs; correct `available_n`/`provenance`/`source` and set `subset_note` if the realized data differs from plan), `models`, `method`, and the `main_experiment` block (`verdict`, `key_stats`, `headline`) from `refine-logs/EXPERIMENT_RESULTS.md` (+ `MECHANISM_ROUTING.md` for the method/family). When a claim carries `suspected_under_power: true` (Power-Fidelity check, `UNDERPOWER=tag`), append `[suspected under-power: used_n X/Y, seeds A/B, grid P/Q]` to its `caveats[]` and mark its `main_experiment.verdict` provisional (e.g. `not-supported [provisional — suspected under-power]`) so verify + iteration treat the negative as provisional, not a confirmed falsification. See [Claim Ledger](#claim-ledger-global-living-report).

**🚦 Experiment Gate (inside the agent):** After code review and sanity pass, before launching the full suite, the agent decides on `AUTO_PROCEED` × `AUTO_DEPLOY` — same binary-binary matrix as the Verify Gate:
- `AUTO_PROCEED=true` (default) → the agent proceeds without UI prompt regardless of `AUTO_DEPLOY`. Log on return: `AUTO_PROCEED: deployed [N] experiments, ~[X] GPU-hours`.
- `AUTO_PROCEED=false` AND `AUTO_DEPLOY=true` → the agent proceeds without UI prompt; `AUTO_DEPLOY=true` acts as standing approval for the deploy step.
- `AUTO_PROCEED=false` AND `AUTO_DEPLOY=false` → the agent calls `AskUserQuestion` with the deploy plan (approve / narrow scope / abort) and **blocks indefinitely** until the user answers. This is the intended human-in-the-loop behavior — no timeout.

**🚦 Plan-reconciliation conflict → Round-End Decision.** When the experiment agent returns `reconciliation_status: escalate` (its Phase 1.5 Step 7 found that the committed submethod cannot satisfy a `method_sensitive` field — e.g. the planned `metric` or `sites` — without changing the plan's *scientific intent*), it stops **before** building, since this stage may not rewrite the claim-authored `EXPERIMENT_PLAN.md`. Because the fix would have to alter scientific intent, the orchestrator does **not** auto-rewrite the plan (that risks silently changing the question the claim asserts — safety-first). Instead it writes a **Round-End Decision** (`ended-needs-decision (experiment: plan-reconciliation-conflict)`, see [Round-End Decision](#round-end-decision-clean-stop-for-next-round-decision)) naming the conflicting milestone field and pointing at `MECHANISM_ROUTING.md`'s `## Plan reconciliation`, then stops. Repair is the plan owner's job: the user fixes the conflicting milestone field in `EXPERIMENT_PLAN.md` (or picks a submethod that fits, or re-scopes the claim) and re-runs. A plain `re-bind` (no `conflict`) is **not** a stop — the agent absorbs it in routing and proceeds normally.

**🛑 Phenomenon-Validation early exit (`BEHAVIOR_SOURCE ∈ {given-validation, discovery}` runs).** When the experiment agent returns `Phenomenon status: not-established` (or a terminal `inconclusive`), the experiment stage's Phase 1.25 gate already stopped before any mechanism milestone (see `/auto-experiment` Phase 1.25). The orchestrator then **ends the pipeline early**:
- **Skip the verify and iteration stages entirely** — there is no established phenomenon to stress-test or iterate on.
- Update the Claim Ledger: set the affected claim(s)' `final_status` to `✗ phenomenon not established` (for `not-established`) or `phenomenon validation inconclusive — fix M0` (for terminal `inconclusive`), pulling the M0 evidence from `refine-logs/EXPERIMENT_RESULTS.md` (`phenomenon_status` metadata). Treat this as the run's **final ledger hook**, so the maintenance protocol's step (6) fires the [Ledger Figures hook](#ledger-figures-hook) here (a negative finding still gets a clean record).
- Set `claims_ledger.json`'s `pipeline_status = ended-phenomenon-not-established` (or `ended-phenomenon-inconclusive`) per the [Terminal-state writeback rule](#terminal-state-writeback-ledger-only), populate `journey_summary` (experiment: negative headline + M0 evidence) and `open_items[]` (any surfaced caveats — under-power, unmatched distributions, missing cross-check tools, etc.), and re-render `CLAIMS_LEDGER.md`. The M0 result is framed as a **valid negative finding**, not an error.
- This is governed by `AUTO_PROCEED` at the experiment-stage gate (Phase 1.1): under `AUTO_PROCEED=false` the agent already presented verdict-appropriate options (`terminate — accept & write report` / `re-run M0 — adjust the test/plan first`) before returning; the orchestrator only sees `not-established` (or terminal `inconclusive`) once that choice resolved to terminate. `established` / `conditional` returns proceed to verify normally (`conditional` having restricted mechanism analysis to the holding conditions at runtime — the plan file is not rewritten by the experiment stage).

**🚦 Power-Fidelity Gate (strict marker absent — every non-reproduction combination; `UNDERPOWER != off`).** Cost-aware runs use (often reduced) scale, so a `not-supported` / `partial` / null main-experiment verdict can be an **under-power artifact** (too little data/seeds/grid to detect a real effect) rather than a genuine negative — and a false negative propagating to verify can get a true claim wrongly "falsified". After the experiment results land, the experiment agent flags any claim whose verdict is weak **and** whose realized scale is materially below `EXPERIMENT_PLAN.md` (`used_n` shortfall, fewer seeds, or fewer grid/checkpoint points) as `suspected_under_power`, with the X/Y figures. The orchestrator then, per `UNDERPOWER`:
- **`tag` (default)** → tag the claim `[suspected under-power: used_n X/Y, seeds A/B, grid P/Q]` as a **provisional** caveat (carried into the ledger `caveats[]`, and forwarded to verify + iteration so the negative is treated as *provisional*, not a confirmed falsification) and **proceed** to verify (respecting discovery's cost-aware design). This is the `AUTO_PROCEED=true` behavior; under `AUTO_PROCEED=false` the experiment agent instead `AskUserQuestion`s (full re-run at plan scale / targeted re-run of the suspect milestone / accept demo-scale & proceed) and blocks.
- **`stop`** → treat it as a **Round-End Decision** (`ended-needs-decision (experiment: suspected-under-power)`, see [Round-End Decision](#round-end-decision-clean-stop-for-next-round-decision)) **even under `AUTO_PROCEED=true`**, with `detail` = which claims/milestones look under-powered and by how much, `remedy` = re-run at plan scale (or accept & re-run with `UNDERPOWER=tag`). For users who never want a suspected artifact to silently reach verify.
- **`off`** → no check (full cost-aware behavior).

### verify — Claim Verification

**Resume check (only when `RESUME=true`)**: skip verify only if **all** of these hold — `verify/VERIFY_REPORT.md` non-empty, `verify/INTEGRITY_AUDIT.md` non-empty with a populated `## Variant integrity (Phase 9)` section (which may be `[skipped — all main-experiment audits FAIL]` for the legitimate short-circuit), and **every** target claim has a non-empty `verify/<claim_id>_*/main_experiment_audit/EXPERIMENT_AUDIT.json` (glob-expand the per-claim directory for each; the legacy flat `verify/main_experiment_audit/` path no longer applies). If any target claim is missing its main-experiment audit, the prior run was partial (it never audited that claim) — do **not** trust an `[skipped — all main-experiment audits FAIL]` marker; re-run verify. Log `[resume] stage=verify skipped — Phase 2 + Phase 9 both finalized`. Otherwise invoke the agent with `resume: true` forwarded so partially-completed variants and partially-done integrity audit can be reused. Guards against a common failure mode: Phase 2 finishes and writes `INTEGRITY_AUDIT.md` with only the main-experiment section, then the process dies during Phase 9 — without the Phase-9-section check, resume would wrongly think verify is done.

Invoke the verify agent. It runs `/auto-verify`, whose full state machine — target selection (Stage 1 audits **every** target claim), the mandatory Phase 2 per-claim main-experiment integrity gate, the Phase 3 step 0 Stage-2 pick (top-K by importance judgment from the Stage-1-admitted pool; `K = MAX_VERIFY_CLAIMS`), within-family method swaps along `DIMENSIONS` on the picked set, the `robustness = #pass / N_eligible` formula, the mandatory Phase 9 per-claim variant integrity gate, and final state assignment — is **owned by `skills/auto-verify/SKILL.md` (single source of truth)**. Do not re-derive that logic here; this orchestrator only consumes the outputs below.

What the orchestrator acts on (everything else is skill-internal):

- **Five per-claim terminal states**, read from `verify/VERIFY_REPORT.md` (trust-the-files): **PASS** / **FAIL** / **INCONCLUSIVE** (Phase 2 main-experiment integrity FAIL — variants never ran) / **ZERO_ELIGIBLE_VARIANTS** (variants ran but all failed Phase 9 integrity) / **INTEGRITY_ONLY** (Phase 2 pass/warn but Stage 2 intentionally skipped; per-claim `stage2_skip_reason` ∈ {`swap_variants_false`, `max_verify_claims_cap`}). All five are valid; INCONCLUSIVE and ZERO_ELIGIBLE_VARIANTS route to different iteration surfaces (fix main experiment vs. fix variants); INTEGRITY_ONLY is a no-op-with-upgrade-suggestion bucket. These map to the five iteration context buckets below and to the ledger `verify.verdict`.
- **Two integrity verdicts** for logging / the Verify Gate: main-experiment integrity (Phase 2) and variant integrity (Phase 9), each `PASS|WARN|FAIL`.
- **All-integrity-broken outcome** (see Key Rules → "All-integrity-broken"): Phase 2 main-experiment integrity FAIL on *every* target claim, or Phase 9 variant integrity FAIL on every claim with no recoverable verdict. **Never** a crash halt and **never** relabeled PASS — with `REVIEW_LOOP=true` (default) the broken claims route into iteration (`verify-inconclusive` / `verify-zero-eligible`); with `REVIEW_LOOP=false` it becomes a **Round-End Decision** (`ended-needs-decision (verify: all-main-experiments-integrity-broken | all-variants-integrity-broken)`).

**Expected artifacts:** `verify/VERIFY_REPORT.md`, `verify/INTEGRITY_AUDIT.md` (Phase 2 main-experiment section + Phase 9 variant section, in one file), `verify/STAGE2_PICK.json` (Phase 3 step 0 record of who was picked for Stage 2), `verify/<claim_dir>/main_experiment_audit/{EXPERIMENT,MECHANISM}_AUDIT.{md,json}` per target claim (Stage 1 audits all), `verify/<claim_dir>/variant_audit/{EXPERIMENT,MECHANISM}_AUDIT.{md,json}` per picked claim only, and `verify/<claim_dir>/ROBUSTNESS.md` per claim (always written — verbose body when `COMPACT=false`, minimal verdict header when `COMPACT=true`; the per-claim verdict is the resume protocol's source of truth). `<claim_dir>` = `<claim_id>_<short_claim>` on disk (see `skills/auto-verify/SKILL.md` "Directory Layout"). Resume checks that need to match a per-claim path must glob-expand `verify/<claim_id>_*/`, not test the bare `verify/<claim_id>/`.

**↳ Claim Ledger update:** after the Verify Gate returns, fill each claim's `verify` block — `robustness`, per-axis `axes.{method,dataset,model}`, `integrity`, `verdict`, and (when `verdict = integrity_only`) `stage2_skip_reason` — from `verify/VERIFY_REPORT.md` + `verify/<claim_dir>/ROBUSTNESS.md` + `verify/INTEGRITY_AUDIT.md`, and set `final_status` to mirror `verify.verdict`. Claims marked `INTEGRITY_ONLY` with `stage2_skip_reason: max_verify_claims_cap` get `final_status: "audit passed, swap-test deferred (max_verify_claims cap)"`; those with `stage2_skip_reason: swap_variants_false` get `final_status: "audit passed, swap-test skipped (audit-only mode)"`. See [Claim Ledger](#claim-ledger-global-living-report). **When `REVIEW_LOOP=false`** this hook is also the *final* ledger hook of the run, so the maintenance protocol's step (6) fires the [Ledger Figures hook](#ledger-figures-hook) here; with `REVIEW_LOOP=true` step (6) is deferred to `iteration:final`.

**🚦 Verify Gate (inside the agent):** Before launching variants, the verify agent prints the target-claim summary + projected GPU-hours and decides on `AUTO_PROCEED` — same binary semantics as Claim Gate / Experiment Gate:
- `AUTO_PROCEED=true` (default) → the agent proceeds without UI prompt regardless of `AUTO_DEPLOY`. Log on return: `AUTO_PROCEED: verified [N] claim(s) across [DIMENSIONS] — [N_pass] PASS / [N_fail] FAIL / [N_inconclusive] INCONCLUSIVE / [N_zev] ZERO_ELIGIBLE_VARIANTS / [N_integ_only] INTEGRITY_ONLY; main-experiment-integrity: <PASS|WARN|FAIL>, variant-integrity: <PASS|WARN|FAIL>`.
- `AUTO_PROCEED=false` AND `AUTO_DEPLOY=true` → the agent proceeds without UI prompt; `AUTO_DEPLOY=true` acts as standing approval for the deploy step.
- `AUTO_PROCEED=false` AND `AUTO_DEPLOY=false` → the agent calls `AskUserQuestion` with the deploy plan (`approve` / `narrow scope` / `abort`) and **blocks indefinitely** until the user answers. This is the intended human-in-the-loop behavior — no timeout.

### iteration — Auto Review Loop

Skip this stage if `REVIEW_LOOP=false`.

**Resume check (only when `RESUME=true`)**: read `review-stage/REVIEW_STATE.json` (schema: `iterations_consumed`, `claim_reentries_consumed`, `status`, `last_verdict`, `last_score`, `pending_upstream_calls` — see `auto-iteration-loop/SKILL.md` "State Persistence"). Branch:
- `status == "completed"` AND `last_verdict ∈ {ready, almost}` AND `last_score >= TARGET_SCORE` → log `[resume] stage=iteration skipped — completed at score=<last_score>, verdict=<last_verdict> (final report at review-stage/AUTO_ITERATION_FINAL_REPORT.md)` and do not invoke. Confirm `AUTO_ITERATION_FINAL_REPORT.md` exists non-empty; if missing, re-invoke the iteration agent with `resume: true` so it can run Termination's final-report assembly.
- `status == "completed"` AND `iterations_consumed >= MAX_ITERATIONS` (or `claim_reentries_consumed >= MAX_CLAIM_REENTRIES` AND only ③ paths remain) → log `[resume] stage=iteration skipped — budget exhausted (iterations=<n>, claim_reentries=<m>)` and do not invoke. Confirm `AUTO_ITERATION_FINAL_REPORT.md` exists non-empty; if missing, re-invoke the iteration agent with `resume: true` so it can run Termination's final-report assembly.
- `status == "awaiting_upstream"` → this is the back-edge handoff. See the "Back-edge handoff" subsection below.
- Otherwise → invoke the iteration agent with `resume: true`. The agent inherits `iterations_consumed` and `claim_reentries_consumed` from the state file; the orchestrator does NOT reset them.

Invoke the iteration agent. Up to `MAX_ITERATIONS` cycles of: external LLM review → routed per-claim fixes (① variant-only / ② main-experiment-script / ③ claim-stage re-entry; the iteration agent may also record ⓪ narrative-only entries that change paper text without dispatching any back-edge) → deploy → re-review. Stops early when **score ≥ `TARGET_SCORE`** AND **verdict ∈ {ready, almost}** AND **no claim is still FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS** (three-dimensional STOP rule). Each back-edge action ①/②/③ consumes 1 iteration uniformly; ③ additionally consumes 1 from `MAX_CLAIM_REENTRIES`; ⓪ does not consume budget and never escalates to the orchestrator.

**Verify-result context handling** — the orchestrator's job here is *extraction + forwarding only*, not routing. Parse `VERIFY_REPORT.md` for each claim's terminal state and forward **five context lists** to the iteration agent. The per-bucket fix routing (① / ② / ③ / ⓪, two-phase FAIL handling, the no-action-with-upgrade-suggestion contract for INTEGRITY_ONLY) is **owned by `skills/auto-iteration-loop/SKILL.md` (single source of truth)** — do not re-specify it here.

| Forward as | Claims with state |
|---|---|
| `verify-passed` | `PASS` |
| `verify-failed` | `FAIL` |
| `verify-inconclusive` | `INCONCLUSIVE` |
| `verify-zero-eligible` | `ZERO_ELIGIBLE_VARIANTS` |
| `verify-integrity-only` | `INTEGRITY_ONLY` (both `stage2_skip_reason` values collapse here; iteration reads the per-claim field to pick the right upgrade command) |

Verify itself never picks among these; iteration's reviewer does (per the iteration skill's routing contract).

#### Back-edge handoff (status `awaiting_upstream`)

When the iteration agent returns with `status: awaiting_upstream` and a non-empty `pending_upstream_calls` list, that means Phase C of an iteration chose action type ③ via the full-path (not lightweight) route. The orchestrator must:

1. Execute each call in `pending_upstream_calls` in order. Each entry has the shape `{skill: "auto-claim" | "auto-experiment" | "auto-verify", args: {…}}`. Use the standard agent invocation (claim agent for `auto-claim`, etc.).
2. After **all** queued calls complete and their artifacts are on disk, re-invoke the iteration agent with `resume: true`. The agent inherits `iterations_consumed` and `claim_reentries_consumed` from the state file — the orchestrator does NOT reset them. The Phase C of the iteration that queued the upstream calls already incremented both counters before returning, so when the iteration loop resumes it starts a fresh iteration (Phase A → E).
3. If any queued call does not complete cleanly, do NOT re-invoke the iteration agent — **propagate the queued call's terminal state** (the upstream skill already exhausted its own recovery, so retrying it here is pointless):
   - **Queued call returned `ended-needs-decision`** (a clean, fixable stop — e.g. the re-done `/auto-experiment` hit a plan-reconciliation conflict, produced no result, or a scorer collapse) → the pipeline takes the **Round-End Decision** path: set `pipeline_status = ended-needs-decision (iteration-upstream: <underlying qualifier>)`, and copy the underlying call's `detail` / `remedy` into this run's Round-End Decision Record + `claims_ledger.json` `round_end`. Not a crash halt.
   - **Queued call genuinely crashed / halted** (e.g. strict-OOM, an API error, sanity exhausted) → set `claims_ledger.json`'s `pipeline_status = halted-at-iteration-upstream` per the [Terminal-state writeback rule](#terminal-state-writeback-ledger-only), record the failure detail as an entry in `open_items[]`, and re-render `CLAIMS_LEDGER.md`.

Lightweight type-③ rewrites do NOT go through this handoff — the iteration agent runs `/auto-experiment` and `/auto-verify` inline within the same iteration and never sets `awaiting_upstream`. The orchestrator only sees `awaiting_upstream` when the iteration agent explicitly handed off.

**Expected artifacts:** `review-stage/AUTO_REVIEW.md`, `review-stage/REVIEW_STATE.json`, `review-stage/REVIEWER_MEMORY.md` (from iteration 2+), and `review-stage/AUTO_ITERATION_FINAL_REPORT.md` (written by Termination once `status = completed`).

**↳ Claim Ledger update (per round + at iteration end):** after each iteration round's `AUTO_REVIEW.md` round section is written — and once more at iteration termination — merge that round's per-claim evidence into the ledger and **overwrite each affected claim's `final_status`** (see [Claim Ledger](#claim-ledger-global-living-report)). This is the step that records how a verify-PASS claim is narrowed or falsified across rounds; it is the ledger's single most important hook. **The termination write is the final ledger hook of the run** (when `REVIEW_LOOP=true`), so the maintenance protocol's step (6) fires the [Ledger Figures hook](#ledger-figures-hook) immediately after — per-round writes never trigger it.

## Claim Ledger (global living report)

A single claim-centric report maintained **incrementally across all four stages**, so the user can read one file and, per claim, see: what the claim is, what data and which model(s) it ran on, the experimental method, the main-experiment result, the verify verdict, and whether iteration later narrowed or falsified it — ending in one combined `final_status`. It is also the **single canonical terminal record** of the whole run: the top-level `pipeline_status` / `journey_summary` / `open_items[]` / `round_end` fields carry what a former separate pipeline report would have; there is no second report file to keep in sync.

**Owner & contention rule.** The **orchestrator** is the sole writer. It does not require any stage agent to change its return contract — at each hook it reads that stage's already-written artifacts on disk and extracts the per-claim fields. (Trust-the-summary-verify-the-files still applies: extract from the files, not the agent's prose.)

**Stage-artifact ownership.** Every stage document (`EXPERIMENT_RESULTS.md`, `EXPERIMENT_TRACKER.md`, `MECHANISM_ROUTING.md`, `VERIFY_REPORT.md`, `ROBUSTNESS.md`, `AUTO_REVIEW.md`, …) is owned by the skill that produces it and written only by its stage agent; the orchestrator writes only the ledger. A re-task **re-runs the owning skill**, which supersedes the rejected result in place (never a second, conflicting narrative); a stage that cannot produce compliant docs takes a Round-End Decision (see Key Rules).

**Two files (both at project root):**
- `claims_ledger.json` — machine-readable single source of truth. **Always English**, stable schema, merge key = `id`. Survives `RESUME` (rebuildable from artifacts).
- `CLAIMS_LEDGER.md` — human view, **rendered from the JSON every time** (so the file is always self-consistent even after a crash). Report-style prose follows `task.md`'s language (per the Output-language rule); claim ids, file paths, and numbers stay as-is.

**Maintenance protocol (idempotent re-render).** At each hook the orchestrator: (1) reads `claims_ledger.json` if present, else starts `{}`; (2) merges only the current stage's fields into each claim by `id` (never deletes another stage's fields); (3) bumps `updated_after_stage`; (4) writes the JSON; (5) fully re-renders `CLAIMS_LEDGER.md` from the JSON. New claims produced by an iteration claim-stage re-entry are appended as new rows.

**Step (6) [final-only].** When the current hook is the *final* ledger hook of the run (`iteration:final`, or `verify` when `REVIEW_LOOP=false`) AND `LEDGER_FIGURES != false`, fire the [Ledger Figures hook](#ledger-figures-hook), merge the returned per-claim entries into `figures[]`, and re-run step (5) so the Markdown picks up the new image links and inline tables. The presence of `figures/INDEX.md` at the project root is the witness that step (6) has already fired for this run — on resume, an existing INDEX.md means skip; otherwise run. Non-final hooks never trigger step (6), so `/paper-figure` is invoked at most once per pipeline run.

**Step (7) [final-only].** For every terminal state that produced a behavior/mechanism outcome — `completed`, `truncated-at-verify` (`REVIEW_LOOP=false`), `ended-phenomenon-not-established`, `ended-phenomenon-inconclusive` — the final ledger hook also updates the cross-round **Global Exploration Memory** by appending this run's behavior + mechanism outcome to `research_memory.json`. See [Global Exploration Memory](#global-exploration-memory-cross-round) for the schema and the write procedure. Idempotent per round number, so a resume that re-reaches the final hook overwrites its own entry rather than appending a duplicate. `ended-needs-decision` exits produce no scientific outcome and therefore invoke no step (7).

**JSON schema** (`claims_ledger.json`):

```json
{
  "project": "<chosen idea title>",
  "direction": "<research direction or task.md one-liner>",
  "date_range": {"start": "", "end": ""},
  "models": {"claim": "", "experiment": "", "verify": "", "iteration": ""},
  "pipeline_status": "running | completed | halted-at-<stage> | ended-needs-decision | truncated-at-verify | ended-phenomenon-not-established | ended-phenomenon-inconclusive",
  "round_end": {"qualifier": "", "detail": "", "remedy": "", "see": "", "partial_artifacts": [], "next_round_options": []},
  "journey_summary": {
    "claim":       "<one-line: X ideas → top idea [title] (impact/novelty/feasibility)>",
    "mechanism_strategy": "<directions from EXPERIMENT_PLAN.md mechanism_strategy; n/a when MECHANISM=given>",
    "mechanism_routing":  "<family=<name>, submethod=<name> (or `not-applicable`)>",
    "experiment":  "<[N] runs, [X] GPU-hours, headline positive|negative|inconclusive>",
    "verify":      "<[N] claim(s): [Np] PASS / [Nf] FAIL / [Ni] INCONCLUSIVE / [Nz] ZEV / [No] INTEGRITY_ONLY (cap=[N_cap], swap_off=[N_swap_off]); integrity[Phase2/Phase9]; or `skipped — <reason>`>",
    "iteration":   "<[N]/MAX_ITERATIONS iterations, claim-reentries=[R]/MAX_CLAIM_REENTRIES, score X/10 verdict Y, termination=<reason>; or `skipped — <reason>`>",
    "figures":     "<[F] across [C] claims; [J] judgment-skipped; [S] render-skipped, [E] errored; or `disabled — LEDGER_FIGURES=false` / `not-run — <reason>`>"
  },
  "open_items": [
    "<free-form one-line entry — one per unresolved item; the orchestrator populates from: verify INTEGRITY_ONLY claims (stage2_skip_reason: max_verify_claims_cap — swap-test deferred), iteration Section-8 unresolved claims, claim-reentry refusals, halted-stage diagnostics, figure render/batch issues, and cross-stage caveats (under-power, missing cross-check tools, unmatched distributions, prepared-but-not-deployed code, etc.). Omit the field entirely (or use []) when nothing is open.>"
  ],
  "iteration_summary": {"score": null, "verdict": "", "rounds_consumed": 0, "max_rounds": 0},
  "updated_after_stage": "claim | experiment | verify | iteration:round-<N> | iteration:final",
  "claims": [
    {
      "id": "C1",
      "statement": "",
      "origin": "",
      "data": {"provenance": "existing | adapted | constructed", "source": "", "available_n": "", "used_n": "", "subset_note": ""},
      "models": [],
      "method": "",
      "main_experiment": {"verdict": "", "key_stats": "", "headline": ""},
      "verify": {
        "robustness": null,
        "axes": {"method": "pass|fail|excluded|n/a", "dataset": "pass|fail|excluded|n/a", "model": "pass|fail|excluded|n/a"},
        "integrity": "PASS|WARN|FAIL",
        "verdict": "PASS|FAIL|INCONCLUSIVE|ZERO_ELIGIBLE_VARIANTS|INTEGRITY_ONLY|n/a",
        "stage2_skip_reason": "swap_variants_false|max_verify_claims_cap|null"
      },
      "iteration": {"final_reviewer_status": "", "changed": [], "falsified": [], "narrowed_to": ""},
      "final_status": "",
      "caveats": [],
      "artifacts": [],
      "figures": []
    }
  ]
}
```

**`figures` field rule.** Default `[]`. Populated **only** at the final ledger hook by the [Ledger Figures hook](#ledger-figures-hook); intermediate hooks leave it untouched. Each entry mirrors one row of `figures/<claim_id>/INDEX.json` and carries one of two artifact shapes depending on `type`:

```json
// image figure (line / bar / grouped_bar / scatter / heatmap / box / violin / multi_panel)
{
  "id": "c1_robustness",
  "type": "bar",
  "caption": "Robustness of C1 across method/dataset/model swaps.",
  "png": "figures/C1/c1_robustness.png",
  "pdf": "figures/C1/c1_robustness.pdf",
  "md":  null,
  "tex": null,
  "source_data": "verify/C1_<short>/ROBUSTNESS.md",
  "status": "ok"
}

// table figure
{
  "id": "c1v2_k_sensitivity",
  "type": "table",
  "caption": "C1_v2 K-sensitivity sweep — necessity is knife-edge in K.",
  "png": null,
  "pdf": null,
  "md":  "figures/C1_v2/c1v2_k_sensitivity.md",
  "tex": "figures/C1_v2/c1v2_k_sensitivity.tex",
  "source_data": "runs/iteration_round_3/M0_K_sensitivity/summary.json",
  "status": "ok"
}
```

The four artifact slots (`png`, `pdf`, `md`, `tex`) are all optional. Image figures fill `png` + `pdf` and leave `md` + `tex` null; tables fill `md` + `tex` and leave `png` + `pdf` null. The render template (below) dispatches on `type` to decide which slots to read. Only entries with `status: ok` are rendered into `CLAIMS_LEDGER.md`. `error` / `skipped` entries are preserved in the JSON (for debugging and re-render decisions) but suppressed in the human view — their tallies surface as entries in the Ledger's `open_items[]` instead.

**`data` field rule.** `provenance` records whether the dataset is an existing one used as-is (`existing`), an existing one transformed/relabeled/filtered (`adapted`), or built from scratch / synthetic (`constructed`). `source` names the dataset (or, for `constructed`, the construction method). `available_n` is the **total** size of the source pool; `used_n` is the amount **actually used in this project's experiments** — these differ whenever the project subsets the data, in which case `subset_note` states how/why. `used_n` is seeded with the *planned* count at the claim hook and **overwritten with the realized count** at the experiment hook.

**`final_status` rule (the truth column).** After verify, set it to mirror `verify.verdict`. For INTEGRITY_ONLY claims, append the `stage2_skip_reason` context (e.g., `⚪ integrity_only (swap-test deferred — max_verify_claims cap)`). After iteration, **overwrite** it with the combined truth — e.g. `✓ holds`, `⚠ configuration-specific (not general)`, `✗ falsified — <one-line why>`. When verify says PASS but iteration falsifies/narrows, the overwrite is what surfaces the discrepancy in one place.

**`round_end` field rule.** Default all-empty `{"qualifier": "", "detail": "", "remedy": "", "see": "", "partial_artifacts": [], "next_round_options": []}` (the `## Round-End Decision — <qualifier>` section at the end of `CLAIMS_LEDGER.md` is omitted entirely from the render when empty). Populated **only** when `pipeline_status = ended-needs-decision`. `qualifier` = the `(<stage>: <reason>)` tag; `detail` = the one-sentence concrete root cause (e.g. *which* `metric`/`sites` field conflicts and *why* the submethod can't satisfy it; *which* scorer collapsed and the measured variance; etc.); `remedy` = the one-line fix; `see` = pointer to the diagnostic stage artifact (e.g. `MECHANISM_ROUTING.md → ## Plan reconciliation` for a plan-reconciliation-conflict, `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md` for a main-experiment-integrity halt, the failing run's log path for a scorer-invalid stop, etc.); `partial_artifacts[]` = list of surviving paths worth inspecting; `next_round_options[]` = 2–4 concrete options the user can pick from the per-case values below. This is what makes the ledger self-explanatory — a reader sees the *specific* problem and fix, not just the `ended-needs-decision` label. Also set the affected claim(s)' `final_status` to a short pointer, e.g. `⏸ round ended — <qualifier> (see round_end)`.

**Field provenance (which artifact each hook reads):**

| Field | Source artifact |
|---|---|
| `id`, `statement`, `origin`, planned `data` (`provenance`/`source`/`available_n`/planned `used_n`)/`models`/`method` | `refine-logs/EXPERIMENT_PLAN.md` (+ `FINAL_PROPOSAL.md`) |
| actual `data.used_n` (+ any `available_n`/`provenance`/`subset_note` correction), `models`/`method` (incl. the composition one-liner from `## Composition plan`), `main_experiment.*` | `refine-logs/EXPERIMENT_RESULTS.md` (+ `MECHANISM_ROUTING.md`) |
| `verify.*`, `final_status` (verify view), `integrity` | `verify/VERIFY_REPORT.md`, `verify/<claim_dir>/ROBUSTNESS.md`, `verify/INTEGRITY_AUDIT.md` |
| `iteration.*`, `final_status` (overwrite), `iteration_summary` | `review-stage/AUTO_REVIEW.md` (per round), `review-stage/REVIEW_STATE.json` |

**`CLAIMS_LEDGER.md` render template** (top grid for at-a-glance, then one section per claim):

```markdown
# Claim Ledger — <project>

**Direction**: <direction>
**Date**: <date_range.start> → <date_range.end>
**Pipeline**: <pipeline_status> | **Iteration**: <score>/10 "<verdict>" (<rounds_consumed>/<max_rounds>)
**Models**: claim=<…>, experiment=<…>, verify=<…>, iteration=<…>
**Updated after**: <updated_after_stage>

| Claim | Main experiment | Verify | Post-Iteration | Final |
|-------|-----------------|--------|----------------|-------|
| C1 <short> | <main_experiment.verdict> | <verdict> <robustness> | <iteration one-liner> | <final_status> |
| … |

---
## C1 — <short statement>
- **Statement**: <statement>
- **Origin**: <origin>
- **Data**: <data.source> — provenance=<data.provenance>; available=<data.available_n>, used=<data.used_n>[; subset: <data.subset_note>]
- **Models**: <models joined>
- **Method**: <method> — <composition one-liner: screen → decode → verify → recover, pulled from MECHANISM_ROUTING.md `## Composition plan`; omit the dash and one-liner when `routing: not-applicable`>
- **Main experiment**: <main_experiment.verdict> — <main_experiment.key_stats>
- **Verify**: robustness=<robustness> — method <axes.method> / dataset <axes.dataset> / model <axes.model>; integrity=<integrity>; verdict=<verdict>
- **Iteration**: <final_reviewer_status>; falsified: <falsified>; narrowed_to: <narrowed_to>
- **Final**: <final_status>
- **Caveats**: <caveats>
- **Artifacts**: <artifacts>
- **Figures**:
  - <render(figures[0])>
  - <render(figures[1])>
  - ...

... (repeat one section per claim: C2, C3, …) ...

<!-- render this section ONLY when journey_summary is populated (any hook after claim stage). Placed after all per-claim sections so the per-claim scientific state comes first, then the process narrative. -->

---
## Journey Summary
- **Claim**: <journey_summary.claim>
- **Mechanism strategy**: <journey_summary.mechanism_strategy>
- **Mechanism routing**: <journey_summary.mechanism_routing>
- **Experiment**: <journey_summary.experiment>
- **Verify**: <journey_summary.verify>
- **Iteration**: <journey_summary.iteration>
- **Figures**: <journey_summary.figures>

<!-- render this section ONLY when open_items is non-empty; omit the whole section when open_items == []. Placed after Journey Summary so unresolved items sit near the end of the file for easy scanning. -->

## Open Items
- <open_items[0]>
- <open_items[1]>
- ...

<!-- render this Round-End Decision block at the END of the file, ONLY when pipeline_status = ended-needs-decision AND round_end is populated. The pipeline_status label is already visible in the header **Pipeline**: line above, so this section is NOT rendered for other terminal states — it exists purely to give the reader the actionable fix + partial artifacts on ended-needs-decision exits. -->

## Round-End Decision — <round_end.qualifier>
- **What happened**: <round_end.detail>
- **Fix**: <round_end.remedy>
- **See**: <round_end.see>
- **Partial artifacts to inspect**:
  - <round_end.partial_artifacts[0]>
  - <round_end.partial_artifacts[1]>
  - ...
- **Next-round options** (you decide — the pipeline will not auto-pick):
  1. <round_end.next_round_options[0]>
  2. <round_end.next_round_options[1]>
  3. <... 2–4 total>
```

`render(figure)` dispatches on `figure.type`:

- **Image types** (`line` / `bar` / `grouped_bar` / `scatter` / `heatmap` / `box` / `violin` / `multi_panel`) → `![<caption>](<png>) — vector: <pdf>`. PNG renders inline in any Markdown viewer; the adjacent PDF path is the publication-grade vector kept for later paper-write use.
- **`table`** → an h4 caption followed by the inlined contents of `<md>`:
  ```markdown
  #### <caption>

  <contents of figures[i].md verbatim>

  Source `.tex`: `<tex>`
  ```
  The Markdown table renders directly in the ledger; the adjacent `.tex` file is the paper-write copy. Inlining keeps the ledger self-contained — readers do not have to open a separate file to see the numbers.

The `Figures` bullet is **omitted entirely** when `figures[]` has no `status: ok` entries, so claims with no plottable data render cleanly.

**RESUME behavior.** The ledger is *derived*, so it is **not** a stage-completion gating artifact (do not skip a stage just because the ledger has its row). On resume, if `claims_ledger.json` is missing or stale, rebuild it from whatever stage artifacts exist on disk before continuing, then proceed normally. For per-claim `figures[]`: if the JSON still has them and the referenced PNG/PDF files exist on disk, reuse as-is; if `figures[]` is empty but `figures/<claim_id>/INDEX.json` exists on disk, hydrate `figures[]` from that file before re-rendering (mirrors the broader rebuild rule). `/paper-figure` is only re-invoked when the run reaches its final ledger hook *and* `figures[]` is still empty after hydration.

### Ledger Figures hook

A single end-of-run hook that calls `/paper-figure` once to populate each claim's `figures[]` with publication-quality plots, so the human reader of `CLAIMS_LEDGER.md` sees evidence inline instead of having to chase paths into `runs/` and `verify/`.

**When it fires (exactly once per pipeline run):**

- After the `iteration:final` ledger write, when `REVIEW_LOOP=true` and the iteration agent reached Termination normally (`completed` / `iterations_exhausted` / `claim_reentry_exhausted` — all three are valid final states, not halts).
- After the verify-hook ledger write, when `REVIEW_LOOP=false` (verify is the last stage by configuration).
- Skipped when `LEDGER_FIGURES=false`. Skipped on halt-writeback by default (data may be incomplete); set `LEDGER_FIGURES=true` to force an attempt even on halt.

**Per-claim figure-plan construction.** This is a **judgment task, not a lookup**. For each claim whose `verdict ∈ {PASS, FAIL, INCONCLUSIVE, ZERO_ELIGIBLE_VARIANTS, INTEGRITY_ONLY}`, the orchestrator reasons about what the claim is asserting and what 0–3 figures would best communicate the supporting evidence to a paper reader — same kind of decision paper-figure's scan-and-ask branch makes when a human isn't around to write `PAPER_PLAN.md`. For INTEGRITY_ONLY claims the figures scope is limited to Stage 1 main-experiment findings (no swap-robustness plot is possible). The output is a `plan_inline` list per claim; an empty list is a valid answer when prose already conveys everything.

**How to reason about it:**

1. **Read the claim, then the evidence.** Open the claim's `statement`, `main_experiment.headline`, `verify.verdict` + per-axis `axes.*`, and `iteration.final_reviewer_status`. Ask: what is this claim actually trying to show — a comparison, a trend, a robustness profile, a calibration, a tradeoff? The answer drives figure choice far more than the shape of any one data file.
2. **Walk the artifacts.** Typical sources to consider — none are required, none are sufficient on their own:
   - `verify/<claim_dir>/ROBUSTNESS.md`, `verify/VERIFY_REPORT.md` (per-variant scores, per-axis pass/fail)
   - `refine-logs/EXPERIMENT_RESULTS.md` (`main_experiment.key_stats` tables, headline numbers)
   - `runs/<run-id>/metrics.json` / `*.csv` / training logs (time series, distributions)
   - `review-stage/AUTO_REVIEW.md` (round-by-round score deltas, falsification evidence)
   - Anything the claim's `artifacts[]` field points to
3. **Pick figure types via paper-figure's Step 3 decision tree** (`skills/paper-figure/SKILL.md` → "Auto-Select Figure Type"). That table is the source of truth for `line` / `bar` / `grouped_bar` / `scatter` / `heatmap` / `box` / `violin` / `multi_panel` / `table` — do not re-derive it here. Match the data shape that *best tells the claim's story*, not just the first shape that fits.
4. **Apply taste.** A figure should add information the prose can't. Skip a bar chart if two numbers are already in the ledger text. Prefer one well-composed multi-panel over three redundant single-panel plots. Robustness claims with ≥ 3 variants often want a heatmap *or* a forest-style bar — pick what reads better for *this* claim's axes. Reject "data exists therefore plot" reasoning.

   **Table vs chart.** Pick `type: table` when the reader needs to read small numbers precisely and there are ≥ 3 columns of them (K-sensitivity sweeps, multi-baseline MSE/score comparisons, ablation matrices, bootstrap CIs). A bar chart loses precision past the second significant figure, and a labelled heatmap loses readability fast. Conversely, pick a chart when the *shape* of the data carries the message (a trend, a gap above a threshold, a distribution). Charts win on shape; tables win on precise values.
5. **Stay within budget.** Soft cap: ≤ 3 figures per claim. Hard cap: ≤ 5. The hook's value drops sharply past that; the ledger is meant to be scannable.
6. **Empty is a real answer.** If no figure would meaningfully outperform the existing prose + numbers (e.g., the claim is purely qualitative, or all evidence is a single scalar), emit `plan_inline: []` for that claim. This is a **judgment-skip** — a clean state that yields `figures[]: []` in the ledger; it is counted in the Ledger's `journey_summary.figures` line as a judgment-skip but does **not** appear in `open_items[]` (nothing to fix).

**Two flavors of "skipped" — keep them distinct in your head.** *Judgment-skip* is the orchestrator's decision above: empty `plan_inline`, no entries written. *Render-skip* is `/paper-figure`'s response when a plan entry's data turns out missing or malformed at render time: a `status: skipped` entry in `INDEX.json`. Render-skips and `status: error` entries are the only kinds that surface in Open Items; judgment-skips don't, because they were never problems.

**Plan entry shape** (each item in `plan_inline`):

```yaml
- id: <short_stem>                 # filename stem; e.g., c1_variant_robustness
  type: <one of paper-figure's Step 3 types>
  data: <one or more concrete paths the figure-script will read>
  caption: <one sentence stating what this figure shows for THIS claim>
  # plus type-specific fields (x, y, group, etc.) — see paper-figure Step 4
```

Plan construction is allowed to scan headers, summary tables, and JSON keys, but should not load full run logs — the goal is a plan, not a render. If the chosen data source turns out to be malformed or missing at script-run time, `/paper-figure` records a `skipped` entry in `INDEX.json` and the orchestrator surfaces it in Open Items. This separation (orchestrator decides *what to plot*, paper-figure decides *how to plot it and whether the data actually supports it*) keeps each side honest.

**Invocation contract.** All claims in one batched call — `/paper-figure` is invoked once per pipeline run with `mode: auto-ledger` and the full claim list (see `skills/paper-figure/SKILL.md` "Auto-ledger invocation contract"). Forwarded fields:

```yaml
mode: auto-ledger
project_root: <cwd>
formats: pdf,png
review: false
style: publication
claims:
  - claim_id: C1
    claim_title: <from ledger>
    output_dir: figures/C1/         # bare id, not <claim_id>_<short>
    plan_inline: [<entries from the rules above>]
  - claim_id: C2
    ...
```

**Merge-back into the ledger.** After `/paper-figure` returns, for each claim:

1. Read `figures/<claim_id>/INDEX.json` (the orchestrator's only contract with the skill).
2. Copy each entry into `claims_ledger.json[claim].figures[]` verbatim — keep `error` and `skipped` entries too, they are useful debug records.
3. Append a global index entry to `figures/INDEX.md` (one section per claim: image figures shown as Markdown image links, table figures shown as their inlined `.md` content).
4. Re-run step (5) of the maintenance protocol so `CLAIMS_LEDGER.md` picks up the new image links and inline tables.

**Failure handling (fail-soft, never halts the pipeline):**

- *Batch-level error* — `/paper-figure` raises before producing any `INDEX.json`. Log `figures-batch-error: <one-line>` to `figures/INDEX.md`, leave every claim's `figures[]` empty, and surface a single `Figures: batch failed — ...` line in Open Items. The pipeline does NOT enter `halted-at-*` state on figure-generation failure.
- *Per-figure render-skip or error* — already captured by `/paper-figure` in `INDEX.json.figures[].status`. The orchestrator aggregates these into the Ledger's `open_items[]` as one entry per affected claim (e.g. `Figures: C5 render-error on c5_training_curves (see figures/C5/INDEX.json)`). Judgment-skips do not appear here.
- *`LEDGER_FIGURES=true` finds nothing to plot or tabulate* — not an error. Write an empty `figures/INDEX.md` with a note; every claim ends up judgment-skipped, counted in `journey_summary.figures` but absent from `open_items[]`.

### Terminal-state writeback (Ledger-only)

After the last stage finishes — regardless of whether the pipeline ran end-to-end, was truncated by `REVIEW_LOOP=false`, was halted by a fail-loudly condition, or ended on a Round-End Decision or phenomenon early-exit — the orchestrator finalizes state **into `claims_ledger.json` + `CLAIMS_LEDGER.md` only**. There is no separate pipeline-level report file; the Ledger is the single terminal artifact. Concretely, in the final ledger hook the orchestrator:

1. Sets `pipeline_status` (`completed | halted-at-<stage> | ended-needs-decision (<stage>: <reason>) | ended-phenomenon-not-established | ended-phenomenon-inconclusive | truncated-at-verify`).
2. Populates `journey_summary` (per-stage one-liners — see the JSON schema above for the exact fields) from the on-disk artifacts (`IDEA_REPORT.md`, `EXPERIMENT_PLAN.md#mechanism_strategy`, `MECHANISM_ROUTING.md`, `EXPERIMENT_RESULTS.md`, `VERIFY_REPORT.md`, `AUTO_ITERATION_FINAL_REPORT.md`, `figures/INDEX.md`).
3. Populates `open_items[]` — one string per unresolved item — by aggregating: `verify/VERIFY_REPORT.md` INTEGRITY_ONLY claims where `stage2_skip_reason: max_verify_claims_cap` (Stage 1 audit passed, Stage 2 swap-test deferred), `AUTO_ITERATION_FINAL_REPORT.md` Section 8 (still-FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS), `REVIEW_STATE.json` claim-reentry refusals, per-claim `main_experiment_audit/*_AUDIT.md` / `variant_audit/*_AUDIT.md` diagnostics (only when halted), `figures/<claim_id>/INDEX.json` `status: skipped|error` entries, `refine-logs/EXPERIMENT_TIPS.md` tips marked `committed` in Phase 1.1 whose prescribed change is not traceable to the run's code or invocation (matched ≠ implemented — flagged by the M0 audit or a Phase 1.25 `/experiment-tips` re-invocation), and any cross-stage caveats surfaced by the experiment/verify agents (suspected under-power, missing cross-check tools, unmatched distributions, code prepared but not deployed, etc.). Omit or use `[]` when nothing is open.
4. If `pipeline_status = ended-needs-decision`, also populates `round_end.partial_artifacts[]` and `round_end.next_round_options[]` (see the [Round-End Decision](#round-end-decision-clean-stop-for-next-round-decision) section for the per-case content).
5. Re-renders `CLAIMS_LEDGER.md` — the Journey Summary section, Open Items section, and (when applicable) the expanded Round-End Decision block are all rendered from these JSON fields per the render template above.

The Ledger is the **single canonical record of what ran and what didn't** — the terminal `pipeline_status` + `journey_summary` (per-stage one-liners) + `open_items[]` (unresolved items) + `round_end` (fix-and-continue detail on `ended-needs-decision` exits) + per-claim `caveats[]` + per-claim `figures[]` together carry everything a run needs to be self-explanatory.

### Round-End Decision (clean stop for next-round decision)

Nine conditions are **not crashes** — they are clean "this round produced nothing viable / nothing trustworthy to continue on" outcomes where the safety-first move is to stop, record *why* in decision-grade detail, and let the user choose the next round. They are governed by **safety-first, independent of `AUTO_PROCEED`**: even in full-auto the orchestrator never fabricates a missing input, silently relaxes a quality bar, relabels an integrity-FAIL as PASS, nor rewrites the claim-authored plan's scientific intent to push past them (doing so would auto-produce a low-quality idea, a mislabeled mechanism, a masked code bug, invalid scores, a verdict built on broken evidence, or an experiment answering a different question than the claim asserts). Each writes `pipeline_status = ended-needs-decision` with the per-case qualifier below — distinct from `halted-at-<stage>` (a fail-loudly crash) and from `ended-phenomenon-*` (a valid negative finding). The two all-integrity-broken cases take this path **only when `REVIEW_LOOP=false`**; with `REVIEW_LOOP=true` (default) the broken claims instead route into iteration to fix the evidence and re-audit (see the all-integrity-broken rule under Key Rules) — they are never a crash halt either way.

| Case | Trigger | Qualifier | Detected by |
|---|---|---|---|
| no viable idea | claim returns zero executable ideas (`IDEA_REPORT.md` empty / placeholder) | `ended-needs-decision (claim: no-viable-idea)` | orchestrator, at Claim Gate |
| no mechanism candidate | routing produces zero candidates (and not `routing: not-applicable`) | `ended-needs-decision (experiment: no-mechanism-candidate)` | experiment stage |
| no experiment result | build completes with no results on disk | `ended-needs-decision (experiment: no-result)` | orchestrator, after build call |
| no verify target | resolved target-claim list is empty after Phase 1 | `ended-needs-decision (verify: no-target)` | verify stage (`/auto-verify` Phase 1) |
| scorer invalid | label-floor pilot collapses (score variance below the gate) | `ended-needs-decision (experiment: scorer-invalid)` | experiment stage (code-review / pilot) |
| plan-reconciliation conflict | committed submethod cannot satisfy a `method_sensitive` plan field without changing scientific intent (`reconciliation_status: escalate`) | `ended-needs-decision (experiment: plan-reconciliation-conflict)` | experiment stage (Phase 1.5 Step 7) |
| suspected under-power | weak/negative main-experiment verdict from a run materially below plan scale, **AND `UNDERPOWER=stop`** (strict marker absent — non-reproduction combinations) | `ended-needs-decision (experiment: suspected-under-power)` | experiment stage (Power-Fidelity Gate) |
| all main experiments integrity-broken | every target claim FAILs Phase 2 main-experiment integrity **AND `REVIEW_LOOP=false`** | `ended-needs-decision (verify: all-main-experiments-integrity-broken)` | verify stage (Phase 2) |
| all variants integrity-broken | every target claim FAILs Phase 9 variant integrity (no recoverable verdict) **AND `REVIEW_LOOP=false`** | `ended-needs-decision (verify: all-variants-integrity-broken)` | verify stage (Phase 9) |

**Propagated form (iteration back-edge).** When any of the above occurs inside an iteration `awaiting_upstream` back-edge (a queued `/auto-claim` / `/auto-experiment` / `/auto-verify` call returned `ended-needs-decision`), it propagates to the pipeline as `ended-needs-decision (iteration-upstream: <underlying qualifier>)` — same Ledger `round_end` write, carrying the underlying call's `detail` / `remedy` (see [Back-edge handoff](#back-edge-handoff-status-awaiting_upstream)). A queued call that genuinely crashes still halts (`halted-at-iteration-upstream`).

For each, the orchestrator records the operational stop in `claims_ledger.json` / `CLAIMS_LEDGER.md`. Concretely: set `pipeline_status = ended-needs-decision (<stage>: <reason>)` (terminal-state agreement rule) **and** populate the `round_end` object: `qualifier` = the `(<stage>: <reason>)` tag, `detail` = one-sentence concrete root cause (which milestone field / which scorer collapsed / which run-id crashed — see per-case examples below), `remedy` = one-line fix, `see` = pointer to the diagnostic stage artifact (e.g. `MECHANISM_ROUTING.md → ## Plan reconciliation`, `runs/<run-id>/*.log`, `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md`, etc.), `partial_artifacts[]` = list of surviving paths worth inspecting, `next_round_options[]` = 2–4 concrete options the user can pick. Also set the affected claim(s)' `final_status` to a `⏸ round ended — <qualifier> (see round_end)` pointer. The rendered `CLAIMS_LEDGER.md` displays this via the `## Round-End Decision — <qualifier>` section **at the end of the file** (after all per-claim sections) — the `pipeline_status` label is already visible in the header `**Pipeline**:` line, so no top-of-file duplicate is rendered. See the render template in [Claim Ledger](#claim-ledger-global-living-report).

It keeps all partial artifacts for inspection (deletes nothing) and skips the Ledger Figures hook (same as a halt).

Per-case next-round options the orchestrator fills with concrete values (into `round_end.next_round_options[]`):
- **no viable idea** → broaden / re-pin the direction in `task.md`; manually lower the novelty/impact bar; pick a different behavior (`/next-round`).
- **no mechanism candidate** → pin a `family:` in `task.md`; mark the proposal behavioral-only (`routing: not-applicable`); re-scope the mechanism direction.
- **no experiment result** → fix the implementation and re-run with `RESUME=true`; swap the implementation approach; narrow the milestone.
- **no verify target** → adjust `TARGET_CLAIMS` (e.g. to `all`); confirm `EXPERIMENT_PLAN.md` has claims; verify a specific id via `/auto-verify <id>`.
- **scorer invalid** → choose the scorer that matches the answer format (multiple-choice → option-token exact-match; short free-form → normalized EM / token-F1; long free-form → LLM-judge / documented substring rubric), then re-run.
- **plan-reconciliation conflict** → fix the conflicting milestone field in `EXPERIMENT_PLAN.md` (the `metric` / `sites` the submethod can't satisfy); or pick a submethod that fits the planned field; or re-scope the claim so the field is satisfiable — then re-run.
- **suspected under-power** → re-run the flagged milestone(s) at the plan's full scale (`used_n`, seeds, grid/checkpoints); or accept the demo-scale negative as provisional and continue with `UNDERPOWER=tag`.
- **all main experiments integrity-broken** → fix the main-experiment evaluation / mechanism rigor flagged in the per-claim `main_experiment_audit/*_AUDIT.md` (fake GT, dead metric, scope overclaim, steering sweep, …), then re-run; or enable `REVIEW_LOOP=true` to let iteration auto-fix the main experiments via `verify-inconclusive`.
- **all variants integrity-broken** → fix the variant evaluation flagged in the per-claim `variant_audit/*_AUDIT.md`, then re-run verify; or enable `REVIEW_LOOP=true` to let iteration auto-fix the variants via `verify-zero-eligible`.

**Halted-pipeline writeback rule.** When fail-loudly conditions stop the pipeline mid-run (the Resource-Fidelity Harness exhausted auto-scale-up + offload at `OOM_MAX_GPUS` (strict-OOM), or an iteration `awaiting_upstream` handoff's queued calls **crashed / halted** — a queued call that instead returned `ended-needs-decision` propagates as `ended-needs-decision (iteration-upstream: <underlying>)`, not a halt), still finalize state into the Ledger per the [Terminal-state writeback rule](#terminal-state-writeback-ledger-only): set `pipeline_status = halted-at-<stage>`, populate `open_items[]` with the halt diagnostics (one-line root cause + pointer to the diagnostic artifact — e.g. `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md` for a Phase-2 FAIL halt, `pending_upstream_calls` failure detail for `halted-at-iteration-upstream`, etc.), populate `journey_summary` with whatever stages did run, and re-render `CLAIMS_LEDGER.md`. This is the single canonical record of what ran and what didn't. (The nine "nothing viable / nothing trustworthy to continue on" conditions — no viable idea, no mechanism candidate, no result, no verify target, scorer invalid, plan-reconciliation conflict, suspected under-power (only when `UNDERPOWER=stop`), and — when `REVIEW_LOOP=false` — all-main-experiments-integrity-broken / all-variants-integrity-broken — take the **Round-End Decision** path above, `ended-needs-decision`, not `halted-at-<stage>`; with `REVIEW_LOOP=true` the two integrity-broken cases route into iteration instead.) **Note**: iteration finishing at `iterations_exhausted` or `claim_reentry_exhausted` is NOT a halt — the iteration agent completes Termination normally, writes `AUTO_ITERATION_FINAL_REPORT.md`, and the orchestrator sets `pipeline_status = completed` with the unresolved claims surfaced in the Ledger's `open_items[]`. The writeback is the orchestrator's job, not the halted agent's — agents return their failure summary, the orchestrator composes the Ledger updates. Do not emit only a CLI message and skip the writeback. **Terminal-state agreement (every exit, not just halts):** whatever terminal `pipeline_status` the run reaches — `halted-at-<stage>`, `ended-needs-decision`, `ended-phenomenon-not-established`, `ended-phenomenon-inconclusive`, `truncated-at-verify`, or `completed` — is set in `claims_ledger.json` and re-rendered into `CLAIMS_LEDGER.md`. The Ledger Figures hook is skipped on halt / `ended-needs-decision` by default (see [Ledger Figures hook](#ledger-figures-hook) for the `LEDGER_FIGURES=true` override).

## Global Exploration Memory (cross-round)

A project-level memory of the whole multi-round research program. Every behavioral **phenomenon** the project has explored is recorded with its `status` and prose `behavior_conclusion`; every **mechanism direction** attempted under that phenomenon is recorded with its `headline` and per-claim `statement` / `method` / `conclusion`. Later `/auto` runs read the memory to avoid re-doing a phenomenon or a `(direction, family)` pair whose conclusions are already settled (see Rule 1); `/next-round` reads it to recommend what to explore next. This is the **cross-round** file, separate from `claims_ledger.json` (single-round, per-claim) and from `review-stage/REVIEWER_MEMORY.md` (single-round, reviewer suspicions).

**File (project root, never moved when a round is archived):**
- `research_memory.json` — machine-readable source of truth, read directly by `/next-round` and any downstream consumer. **Always English**, merge key = behavior `id`.

**Owner.** The orchestrator (`/auto`) is the **sole writer** — once per run, at the final ledger hook (step (7) of the maintenance protocol). `/next-round` only **reads** it. No stage agent changes its return contract; the orchestrator extracts the per-run fields from the already-written artifacts on disk.

**Round number.** `round = (highest existing rounds/round_<k> suffix) + 1` — parse the numeric **suffix**, not a count of folders. A count recycles a slot when a middle archive was deleted (round_1 + round_3 present, round_2 gone → count 2 → 3 collides with round_3); max-suffix+1 never does. The multi-round guard guarantees every prior round is archived before a fresh run, so this covers **every** round, including phenomenon-not-established `given-validation`/`discovery` rounds and reproduction-combo (`given`+`given`) rounds (which write no `mechanisms[].round`). Defensively, if memory records a higher round (`max(behaviors[].decided_in_round, mechanisms[].round)`), use that instead — a gap is safer than reusing a slot. Archives and memory both absent → round 1. On `RESUME`, the current round's outputs are still at root un-archived, so the count is unchanged and the same round number recurs (idempotent). The archive folder `rounds/round_<N>/` uses this number, so the orchestrator can stamp `archived_to: "rounds/round_<N>/"` on each `mechanisms[]` entry by convention (the path `/next-round` will archive into).

**JSON schema (`research_memory.json`):**

Every scientific field — `behavior_conclusion`, each mechanism's `headline`, and every `claims[]` entry's `statement` / `method` / `conclusion` — carries a real sentence of substantive content extracted from the round's artifacts. **`/next-round` reads only this file**, so a status label ("PASS") in place of a real finding is exactly the context loss the schema guards against. A filled two-behavior example lives in `example.json` at the repo root.

```json
{
  "direction": "<overarching research direction / topic>",
  "behaviors": [
    {
      "id": "B1",
      "statement": "<one-sentence phenomenon>",
      "status": "<phenomenon verdict: established | conditional | not-established | inconclusive>",
      "behavior_conclusion": "<SUBSTANTIVE: what is now known about the phenomenon itself — for `conditional`, the conditions under which it holds; for `not-established`, what was tested and the null that was found>",
      "impact": {
        "assessment": "<SUBSTANTIVE one line: why this phenomenon matters + who would build on it>",
        "recommendation": "<PROCEED | PROCEED WITH CAUTION | DEPRIORITIZE>",
        "assessed_in_round": 1
      },
      "decided_in_round": 1,
      "mechanisms": [
        {
          "round": 1,
          "direction": "<mechanism strategy: a chain of /mechanism-explore directions joined by →, e.g. 'Location → Causal Intervention'>",
          "family": "<the chosen mechanism family from /mechanism-skills (optionally with a / submethod suffix), or null if behavioral-only>",
          "headline": "<SUBSTANTIVE: the mechanistic finding + key evidence/number — e.g. 'no residual-stream localization of the 1P/3P asymmetry (selectivity peaks S=1.07 at L2, never ≥2); a separable paraphrase-invariant 1P endorsement direction does exist at L12-L16'>",
          "claims": [
            {
              "id": "<claim_id>",
              "statement": "<paper-abstract-style one sentence: what the claim asserts, incl. any narrowing / conditional scope; strip iteration meta-brackets>",
              "method": "<paper-abstract-style one sentence: what was measured + the predicate/threshold that decides support; drop hyperparameter minutiae>",
              "conclusion": "<paper-abstract-style one sentence: what was found — lead with the qualitative outcome (not the PASS/FAIL label), name any narrowing / falsification, include one key stat when it earns its place; state 'audit passed, swap-test deferred (cap) — <Stage 1 finding>' for INTEGRITY_ONLY with stage2_skip_reason=max_verify_claims_cap; name the integrity break for INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS>"
            }
          ],
          "archived_to": "rounds/round_1/"
        }
      ],
      "untried_mechanism_directions": ["<the /mechanism-explore directions NOT yet tried for this behavior — the six directions minus those in this behavior's mechanisms[].direction>"]
    }
  ],
  "untried_behavior_directions": ["<candidate phenomena considered but not yet investigated — free-form, one sentence each>"]
}
```

**Controlled values come from the defining skills — do not enumerate or invent them here.** `mechanisms[].direction` and `untried_mechanism_directions` use the **six directions** defined in `/mechanism-explore` (`Location`, `Causal Intervention`, `Tuning & Editing`, `Formation Tracing`, `Unit Interpretation`, `Decision Auditing`); `mechanisms[].family` uses the **eleven families** defined in `/mechanism-skills`. Those skills are the single source of truth — this schema only points at them, so adding a direction/family there never makes this schema stale. `status` is memory's own enum (defined inline above). Settlement of a mechanism attempt is judged at read time from its `headline` + `claims[].conclusion` prose (see Rule 1).

**Memory records only rounds with a scientific outcome.** Four terminal states qualify: `completed`, `truncated-at-verify`, `ended-phenomenon-not-established`, and `ended-phenomenon-inconclusive`. The two phenomenon-not-established / -inconclusive exits write a behavior entry with an empty `mechanisms[]` list, since mechanism work never ran on an unestablished phenomenon. `ended-needs-decision` exits — operational stops such as no viable idea, no mechanism candidate, no result, no verify target, a scorer collapse, a plan-reconciliation conflict, or (under `REVIEW_LOOP=false`) all-integrity-broken — reach no scientific verdict and never appear in memory at all; their trace lives in the archived round's `CLAIMS_LEDGER.md.round_end`.

**Write procedure (step (7)).** All scientific fields are extracted from on-disk artifacts, never re-derived from the agents' prose. The per-claim source of truth is `claims_ledger.json` — its `statement`, `final_status`, `main_experiment.headline` / `key_stats`, `verify.verdict` / `robustness` / `axes`, and `iteration.narrowed_to` / `falsified` are already substantive. The M0 phenomenon verdict comes from `refine-logs/EXPERIMENT_RESULTS.md`'s `phenomenon_status`. The write procedure just compresses and re-shapes what these files already say:

1. **Behavior of this run.** In `BEHAVIOR_SOURCE ∈ {given-validation, discovery}` runs, take the M0-validated phenomenon from `refine-logs/EXPERIMENT_RESULTS.md` (`phenomenon_status`) + `FINAL_PROPOSAL.md`; in `given` runs (no M0), take the behavior stated in `task.md` / `FINAL_PROPOSAL.md`. In the **reproduction combo** (`BEHAVIOR_SOURCE=given` + `MECHANISM=given`), **skip the memory write** (no discovery semantics).
2. **Merge by behavior.** Semantic-match the behavior against existing `behaviors[]` entries; if there is no match, append a new one with a fresh `id`. On merge, refresh each field incrementally — a superseding status or a stronger conclusion overwrites the prior value, but a weaker or duplicative one does not. Then set:
   - **`status`** — the M0 verdict for `given-validation` / `discovery`; `established` for user-asserted `given`, unless a stronger status is already on record.
   - **`behavior_conclusion`** — the M0 finding combined with the round's headline result. For `conditional`, name the conditions under which the phenomenon holds; for `not-established`, name what was tested and the null that was found.
   - **`impact`** — from the claim stage's impact-check: the chosen idea's one-line case and `recommendation`, read from `idea-stage/IDEA_REPORT.md`. Impact-check runs only in `BEHAVIOR_SOURCE=discovery`, so `given` / `given-validation` runs leave `impact` empty unless a prior discovery round already assessed the same behavior. `/next-round` reads `impact.assessment` + `impact.recommendation` to prioritise higher-impact untried directions.
3. **Append one `mechanisms[]` entry** for this run:
   - **`round`** — the current round number.
   - **`direction`** — a chain of `/mechanism-explore` directions joined by `→`, read verbatim from `EXPERIMENT_PLAN.md`'s `mechanism_strategy:` line. Never enumerate or invent — take the actual value from the plan.
   - **`family`** — the chosen `/mechanism-skills` family (with an optional `/` submethod suffix), read from `MECHANISM_ROUTING.md`'s chosen family or `## Composition plan`. `null` when the proposal is behavioral-only.
   - **`archived_to`** — `"rounds/round_<N>/"` by convention, where `<N>` is this entry's `round`. This is the path `/next-round` will move the round's outputs into on the next transition; the orchestrator stamps it directly from the resolved round number without reading from disk (the archive folder does not exist yet at write time). It is a pointer, not a check — a later reader can jump straight from a mechanism entry to its provenance artifacts (`refine-logs/`, `verify/`, `CLAIMS_LEDGER.md`, etc.) once archiving has run.
   - **`headline`** — one full sentence stating the mechanistic finding, synthesized from the leading claims' `main_experiment.headline` + `key_stats` and any `iteration.narrowed_to` / `falsified`. Name the key number and any scope narrowing. A later round reads this first when judging whether the mechanism attempt is settled or worth retrying, so a bare label is not acceptable.
   - **`claims[]`** — one object per claim. For each claim in `claims_ledger.json.claims[]`, extract:
     - **`id`** — verbatim from the ledger.
     - **`statement`** — compress `claims_ledger.json[claim].statement` into ONE paper-abstract-style sentence. Strip iteration meta-brackets (`[revised at iteration 1 (⓪ ...); original: '...']` and similar — those describe process, not what the claim now asserts). Keep the scientific assertion + any conditional scope in a subordinate clause. Target ≤ 35 words.
     - **`method`** — compress `claims_ledger.json[claim].method` into ONE sentence naming what was measured and the predicate / threshold that decides support. Drop position / layer-level hyperparameters unless the method identity depends on them. Target ≤ 30 words.
     - **`conclusion`** — synthesize ONE paper-abstract-style sentence from `main_experiment.headline` + `main_experiment.key_stats` + `verify.robustness` + `verify.axes.*` + `iteration.narrowed_to` + `iteration.falsified` + `final_status`. Rules: (a) **lead with what was found, not the PASS / FAIL label** ("robust across method / dataset / model" is fine; "PASS" alone is not); (b) include one key stat when it earns its place — one number is usually enough; (c) when narrowed or falsified, name the narrowing scope or the falsifier; (d) when `verify.verdict = integrity_only` with `stage2_skip_reason: max_verify_claims_cap`, write "audit passed, swap-test deferred — <what the main experiment measured>" so the audit result is surfaced without overclaiming robustness; (e) when `verify.verdict ∈ {INCONCLUSIVE, ZERO_ELIGIBLE_VARIANTS}`, name the integrity break (e.g. "main-experiment integrity broken (see `EXPERIMENT_AUDIT.md`) — no robustness measurable"). Target 30–55 words.
   - **Phenomenon-not-established / -inconclusive runs skip this step** — mechanism work never ran; `status` + `behavior_conclusion` + `decided_in_round` on the behavior entry carry the M0 finding on their own.
4. **Refresh both `untried_*` lists** — these are the schema's only two shrink-and-grow fields; every other field is append/refresh-only.
   - **`untried_mechanism_directions`** (per behavior, on this round's matched behavior): recompute as the six `/mechanism-explore` directions **minus** those now appearing in this behavior's `mechanisms[].direction`. Every new mechanism entry shrinks this list by one direction (or more, when the round's `direction` is a chain).
   - **`untried_behavior_directions`** (root list): two operations, in this order.
     - (a) **Remove** — semantic-match the round's primary behavior against the existing entries and drop any entry that describes the same phenomenon: it has now been investigated, and carrying it forward would mislead `/next-round` into recommending an already-explored candidate. This step **applies to every mode** that produced a behavior outcome (`given` / `given-validation` / `discovery`), because a prior discovery round may have parked a candidate that a later `given` / `given-validation` round then picks up — the entry must still be pruned once the phenomenon is actually investigated.
     - (b) **Append** — only fires when `BEHAVIOR_SOURCE=discovery` (the ideation stage is the sole source of these entries). Read `idea-stage/IDEA_REPORT.md`'s `## Ranked Ideas` section (its final form, after `/impact-check` re-ranks by impact-first / novelty-second in Phase 3.5 of `/auto-claim`); every **surviving non-selected** idea (i.e., rank ≠ `CHOSEN_IDEA` and not eliminated by novelty / impact) is a runner-up phenomenon. Append each as a one-sentence string with the `(round <N> idea #<K> — impact <X>, novelty <Y>)` tail so `/next-round` can prioritise from the impact / novelty scores. `given` / `given-validation` runs skip step (b) entirely — no ideation, no `## Ranked Ideas`, nothing to append.
     - The remove-then-append order is deliberate: it prevents a runner-up that later got promoted to primary from ending up back in the untried list on the same write.
   - Idempotent per `round`: if a mechanism entry for this round already exists (resume re-reaching the final hook), overwrite it rather than appending a duplicate; likewise, do not re-remove or re-append entries the same round already touched.

**Read (default on; no-op only in the reproduction combo `given`+`given`).** The claim stage passes `research_memory.json` to the claim agent, which surfaces the exploration history — the substantive `behavior_conclusion`, `impact.assessment` + `impact.recommendation`, each mechanism's `headline`, and every claim's `statement` / `method` / `conclusion` — to the strategy skills (see `agents/claim.md` step 0.5). This lets the next round build on what has been learned rather than just avoiding a label. Two cross-round rules govern how the memory is applied, across three granularities — **behavior**, **mechanism direction**, and **family**:

- **Rule 1 — don't redo settled work; do retry the unresolved.** Settlement is judged at two levels:
   - **Behavior settled** ⇔ `status ∈ {established, conditional, not-established}`. `inconclusive` is NOT settled — the test failed to decide, so the question is still open (positive retry candidate: re-run with a fixed/stronger test).
   - **Mechanism attempt settled** (a `(direction, family)` pair under a behavior) ⇔ its `headline` + `claims[].conclusion` prose together report either a **stable positive** answer (the located component is causally verified as driving the behavior in the predicted, specific way) or a **stable negative** answer (the hypothesis was falsified by robust evidence — a robust null, a failing causal test, or a "located but not causal" result). It is **not settled** when the conclusions report swap-test deferral (INTEGRITY_ONLY with `stage2_skip_reason: max_verify_claims_cap` or `swap_variants_false`), integrity break (INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS), mixed / partial support, or an explicit under-power caveat — those are retry candidates.

   The strategy skills (`/mechanism-explore`, `/mechanism-skills`) make this settlement judgment by reading each `mechanisms[]` entry's `headline` + every `claims[].conclusion`. The `agents/claim.md` step 0.5 handoff passes each behavior's `mechanisms[]` verbatim so they see the full text.

   Where the judgment applies depends on the mode: `BEHAVIOR_SOURCE=discovery` judges at the **behavior** level (skip settled behaviors when picking a new phenomenon); `BEHAVIOR_SOURCE ∈ {given, given-validation}` judges at the **mechanism-attempt** level (for the matched behavior, skip settled `(direction, family)` pairs when picking a new mechanism). Family-level avoid flows to the experiment stage via `EXPERIMENT_PLAN.md` — see `agents/claim.md` step 0.5. Use the conclusions to pick a genuinely complementary direction, not just a different label.

   Worked example: in `example.json`, behavior B2's `(Location, Probing)` entry has `claims[].conclusion` prose reporting that no separable causal direction was recovered — even though the per-claim `verify.verdict`s were PASS. The combined reading is **stable negative** (localization does not hold for this behavior), so that direction+family is settled and skipped for B2 in later rounds. Reading only the PASS/FAIL labels would wrongly flag it as a positive result and re-run the same test.
- **Rule 2 — an explicit user request overrides Rule 1.** If `task.md` explicitly pins a behavior, a mechanism direction, or a family (lightweight free-text, e.g. `mechanism direction: Tuning & Editing` / `family: Steering Vectors`), use it **directly** — do not pick from untried candidates/backlog for that level. (A pinned behavior is the `BEHAVIOR_SOURCE ∈ {given, given-validation}` path.) **Exception — a bare pin does NOT override a *settled* item.** When a pin names something Rule 1 marks settled (a settled behavior, or a settled `(direction, family)` per the `headline` + `claims[].conclusion` reading), the pin alone is treated as a likely oversight (the user may have forgotten it was concluded), not an override — it falls to the conflict rule below. The **only** way to force re-doing settled work is the `retry-settled` marker: a `task.md`-level switch `retry-settled: true` that explicitly authorizes honoring any pin which collides with already-settled memory. With the marker, a settled pin is honored (re-done); without it, the settled pin yields to a fresh untried candidate.
- **Conflict → resolve via `retry-settled`, respecting `AUTO_PROCEED` (orchestrator-owned).** The **orchestrator** detects, at the claim-stage setup (the [Global memory read](#pipeline) step where it already holds both `task.md` and `research_memory.json`), whether a Rule-2 pin names something Rule 1 marks settled — a behavior with terminal `status`, or a `(direction, family)` whose `headline` + `claims[].conclusion` prose read as stable positive / stable negative. On conflict it neither silently re-runs nor silently skips — it resolves deterministically: **`retry-settled: true` in `task.md` → `honor-pin`** (the user explicitly authorized re-doing the settled item); **otherwise → `pick-fresh`**, applied **silently when `AUTO_PROCEED=true`** (log the swap) and via **`AskUserQuestion`** (`honor-pin` vs `pick-fresh`, recommended `pick-fresh`) **when `AUTO_PROCEED=false`**. The resolved decision passes into the claim agent's prompt as `pin_resolution: honor-pin | pick-fresh`. No conflict → no `pin_resolution` is passed and any pin is honored as written. Unlike the multi-round guard, this gate **respects `AUTO_PROCEED`**: re-doing settled work without the explicit `retry-settled` opt-in is wasteful but recoverable (a wrong auto-pick merely explores a fresh direction, still useful work), so full-auto can decide it from the marker without a human. The claim agent and the strategy skills (`/mechanism-explore`, `/mechanism-skills`) do **not** raise this gate themselves; they act on the `pin_resolution` the orchestrator passes down (and the claim agent additionally re-checks settled status as a backstop against a missed match).

An absent file means round 1 with an empty history; absent any conflict, the read never blocks execution.

**RESUME / archive.** `research_memory.json` is not a stage-gating artifact and is never moved by archiving. On `RESUME=true` the file stays untouched until the resumed run reaches its own final hook, where the idempotent per-round write applies.

## Re-tasking a stage — two triggers

A stage is re-run under a changed requirement for exactly two reasons: the **orchestrator rejects** the result it got, or the **user directs** a change. They share one invariant and differ only in who initiates and how urgently it lands.

**Shared invariant.** The on-disk `EXPERIMENT_PLAN.md` is the single authoritative constraint. Re-tasking is always **update the authoritative plan first (via the editor the current stage allows) → terminate the old subagent → dispatch a fresh subagent** that trusts only the updated plan — it does **not** adopt the rejected run's leftover docs, it **overwrites / supersedes** them in place. Never inject the new requirement as dispatch prose that contradicts the plan (the agent treats the plan as authoritative and reverts). The orchestrator **never** hand-edits `EXPERIMENT_PLAN.md` (raw edits corrupt its machine markers) and **never** hot-notifies a running agent. *Who* may edit the plan is fixed by **stage**: **claim = always (owner) · iteration = scoped failing-step edit · experiment / verify = never · orchestrator = never.**

### A. The orchestrator rejects a subagent result

When a returned result is not trustworthy enough to open the next gate (missing / incomplete artifacts, under-power, failed sanity, an integrity break, a result the gate cannot accept), re-task by **the stage the rejection happened in**:

- **claim** (Claim Gate) → the **claim agent** rewrites `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md` (`switch` / `re-run`). Nothing downstream yet, so nothing to supersede.
- **experiment** (Experiment Gate / mid-run / a rejected result such as under-power) → experiment **cannot** edit the plan: if it merely **under-realized** an otherwise-correct plan (under-power, 2/8 grid points, sanity-failed, partial run), re-task a **fresh** experiment agent against the *same* plan, naming what to redo; if the **plan itself must change**, route back via a **claim re-entry**, then a fresh experiment.
- **verify** (Verify Gate) → verify never edits the plan (it only runs swap variants); a plan / main-experiment problem **sinks into iteration** — a `verify-inconclusive` main-experiment fix, or a claim re-entry — where the edit actually happens.
- **iteration** → the **iteration agent** makes the scoped **plan-step edit** to the failing step + re-runs (in-loop, or a re-dispatched `/auto-experiment`); a **full** re-plan hands off to the claim agent via the `awaiting_upstream` handoff.

**Bounded retries ≤ 2** per rejection; still non-compliant → **Round-End Decision**. Never keep arguing, never take over — the orchestrator running the stage itself breaks the single-source-of-truth boundary and orphans the stage docs (see the red line in Key Rules).

### B. The user directs a change

A plan change / redo the **user** requests — verbally to the orchestrator mid-run, at a gate, or by editing the files — is the **top authority**: it **overrides `task.md` pins and the plan's protection** (the user may change scientific intent) and is honored **immediately, even under `AUTO_PROCEED=true`**. Do **not** defer it to a Round-End (that would circularly ask the user to do what they just asked). The orchestrator **judges and routes only**:

1. **Judge urgency × in-flight state.** Strong and it invalidates the running stage → **stop the current subagent** (stopping is scheduling, allowed) so no compute is wasted under the stale plan. Weak / deferrable → apply at the next milestone or gate boundary.
2. **Delegate the plan edit to the stage-allowed editor** (per the shared invariant): at or before the experiment stage, only the **claim agent** (a claim re-entry — full re-plan for an intent change, scoped rewrite for a same-intent tweak); once iteration is live, a same-intent tweak may instead be the **iteration agent's** scoped plan-step edit. If the override touches a **hard constraint** (budget / prohibition / emphatic-positive) or a **notice** item (model / dataset / preference), also regenerate the affected injected block — `## HARD CONSTRAINTS` and/or `## NOTICE` — for the stage(s) it is routed to (see the "Injecting `task.md`" Key Rule).
3. **Log the override to `task.md` — only when it conflicts with the original.** If **and only if** the user's request **contradicts something the user already wrote in `task.md`** (overrides a stated constraint, changes a specified behavior / task, lifts a prohibition), append one line to a `## User Overrides (log)` section at the **end** of `task.md` — `- @<point>: <what the user asked> (overrides: <the conflicting original>)` — **never editing the user's original body above it** (create the section on the first such conflict). A request that does **not** conflict with anything in `task.md` (adds something the file is silent on, or merely refines the plan) is **not** logged, and the `## User Overrides (log)` section stays absent. This keeps `task.md` the *current* truth — original intent **plus** the trail of actual overrides — while the authoritative machine constraint still lives in `EXPERIMENT_PLAN.md` / the regenerated HARD CONSTRAINTS block. `<point>` = a stable marker (stage / round, or a timestamp).
4. **Re-dispatch fresh** against the updated plan; stamp the superseded narrative `superseded: per user request @ <point>`.

A user who simply edits `EXPERIMENT_PLAN.md` / `task.md` themselves and asks to re-run is already on the sanctioned path — `RESUME` re-runs the affected stages through the owning skills.

## Key Rules

- **Trust the agent's summary, verify the files.** Each agent returns a short report; the orchestrator must still confirm expected artifacts exist on disk before opening the next gate. If a file is missing or a result is rejected, re-task per the protocol below — do not synthesize a fallback.
- **Re-tasking a stage (rejection or user-directed change).** Update the authoritative `EXPERIMENT_PLAN.md` first (via the stage-allowed editor — claim: always / iteration: failing-step / experiment · verify · orchestrator: never), then dispatch a **fresh** subagent that overwrites the rejected leftovers; bounded retries ≤ 2 → Round-End. Full protocol, both triggers, in [Re-tasking a stage](#re-tasking-a-stage--two-triggers).
- **Orchestrator never executes stage logic.** Its only actions: dispatch an agent, fire a gate, read files, write the ledger. It never runs an experiment, never writes a stage-owned artifact, never does a skill's work in place of its agent. A stage that can't produce a compliant result (including after the ≤ 2 retries) → **Round-End Decision**, not takeover — a takeover both breaks the single-source-of-truth boundary and orphans the stage docs. Stay a scheduler.
- **One agent at a time.** Stages run sequentially. Within an agent, it may parallelize as it sees fit.
- **Global exploration memory is cross-round and orchestrator-owned.** Written once per run at the final ledger hook (step (7)) for every terminal state that produced a scientific outcome (`ended-needs-decision` exits produce none and are absent from this file). Read by default at the claim stage (every combination except the reproduction combo `given`+`given`) to avoid re-doing settled behaviors and settled `(mechanism direction, family)` pairs per Rule 1 (settlement is judged from each mechanism entry's `headline` + `claims[].conclusion` prose); `inconclusive` / mixed / swap-test-deferred (INTEGRITY_ONLY) / integrity-broken / under-power all stay retry candidates. An explicit `task.md` pin overrides this (Rule 2), and a settled-pin conflict resolves via `retry-settled`. Never moved when a round is archived; never written by `/next-round`. See [Global Exploration Memory](#global-exploration-memory-cross-round).
- **GPU pin propagation (assert, don't assume).** When `GPU_ID != auto`, the pin must survive every hop — orchestrator → stage agent (`gpu_id:`) → sub-skill (`GPU_ID`) → `/run-experiment` (leading `CUDA_VISIBLE_DEVICES=<GPU_ID>` positional). Passing the flag down is not proof it took effect, so **verify the witness on disk**: every dispatched run writes `runs/<run-id>/cost.json` with a `gpu_ids` field = the effective `CUDA_VISIBLE_DEVICES` list (see `skills/run-experiment/SKILL.md` Step 5.5). After each stage that dispatched runs (experiment, verify, and any iteration Phase-C run — also `runs/iteration_round_<N>/<run-id>/cost.json`), the orchestrator checks that the union of `gpu_ids` across that stage's fresh `cost.json` files is a **subset of the requested `GPU_ID` set**. On mismatch — a run landed on a device **outside** the requested set — do **not** silently continue: log `[gpu-pin] stage=<name> requested={<GPU_ID>} but ran on {<observed>} — pin did not propagate` and treat it as a fail-loudly halt (`Pipeline status = halted-at-<stage>`, root cause in Open Items). An **empty** `gpu_ids` is **not** a violation — it means the run used no GPU (a CPU-only sanity / analysis step), and the empty set is trivially a subset of the requested set, so it passes. (Do not halt merely because a run used no GPU, or used fewer of the requested devices than expected — only an *unrequested* device is a propagation failure.) When `GPU_ID = auto` this check is skipped entirely (device choice is delegated to the launcher by design).
- **Large file handling:** if the orchestrator's Write tool fails due to file size, retry with Bash (`cat << 'EOF' > file`) in chunks. Do not ask permission.
- **All gates are governed by `AUTO_PROCEED` (binary, no third mode).** Claim Gate, Experiment Gate, Verify Gate, mechanism-family mini-prompt: when `true` (default), the orchestrator/agent skips `AskUserQuestion` entirely and proceeds with the recommended option — full auto, no human needed; when `false`, the UI prompt is shown and execution blocks **indefinitely** until the user responds — human-in-the-loop, waiting is the desired behavior. There is no timeout-then-default fallback; the two modes are mutually exclusive by design. **Exceptions** (gates not governed by `AUTO_PROCEED`): see the `RESEARCH_DOMAIN` row in the flag table for the silent inference-ambiguity fallback; see the Verify Gate section for `AUTO_DEPLOY=true` standing approval; the **multi-round guard** (un-archived prior-round artifacts) halts even in full-auto (data-protective — overwriting prior outputs is irreversible); and the **Given-Behavior Comprehension Gate** (a `given` direction with no concrete behavior) always waits for the user even in full-auto (a vague direction is a decision only the user can make). **Note:** the **settled-pin conflict** is *not* in this exception list — it **respects `AUTO_PROCEED`**, resolving via the `task.md` `retry-settled` marker (full-auto) or `AskUserQuestion` (interactive); see [Global Exploration Memory](#global-exploration-memory-cross-round).
- **Round-End Decision (clean stop, safety-first, not a crash).** When a stage produces nothing viable to continue on — claim returns no viable idea, the routing call produces no candidates, the build call has no results, verify has no target claim (empty resolved list), or the experiment's label-floor pilot collapses (scorer invalid) — do **not** fabricate the missing input or relax the bar to push past it (governed independent of `AUTO_PROCEED`). Stop, set `pipeline_status = ended-needs-decision` with the per-case qualifier, and write the **Round-End Decision Record** (see [Round-End Decision](#round-end-decision-clean-stop-for-next-round-decision)) so the user chooses the next round.
- **All-integrity-broken (verify) → route or end, never relabel.** When verify finds *every* target claim's evidence integrity-broken — all main experiments FAIL at Phase 2 (main-experiment integrity), or all variants FAIL at Phase 9 (variant integrity, no recoverable verdict) — do **not** relabel any integrity-FAIL as PASS (hard red line, never bypassable). With `REVIEW_LOOP=true` (default) this is **not** a halt: route the broken claims into iteration (`verify-inconclusive` for main-experiment breaks, `verify-zero-eligible` for variant breaks) to fix the evidence and re-audit; even the all-broken case goes through the bucket, not a halt. With `REVIEW_LOOP=false` (no fixer available) write a **Round-End Decision** (`ended-needs-decision (verify: all-main-experiments-integrity-broken)` / `(verify: all-variants-integrity-broken)`) naming the failing sub-audit and pointing at the per-claim `*_AUDIT.md`, so the user fixes the evidence and re-runs. Neither path is `halted-at-<stage>`.
- **Fail loudly between agents.** Stop and report (no invented next steps), writing `Pipeline status = halted-at-<stage>`, when any of these genuine error conditions occur:
  - `GPU_ID != auto` but a stage's dispatched runs landed on a device outside the requested set — see the GPU pin propagation rule above. (An empty `gpu_ids` / CPU-only run is not a violation.)
  - An iteration `awaiting_upstream` handoff's queued `pending_upstream_calls` **crashed / halted** (e.g., strict-OOM or an API error during back-edge execution). Halt with `Pipeline status = halted-at-iteration-upstream`; do NOT silently re-invoke the iteration agent. (If instead the queued call returned `ended-needs-decision`, the pipeline takes the **Round-End Decision** path `ended-needs-decision (iteration-upstream: <underlying>)`, not a crash halt — see [Back-edge handoff](#back-edge-handoff-status-awaiting_upstream).)
- **If iteration ends without a positive assessment** — either `iterations_exhausted` (hit `MAX_ITERATIONS`) or `claim_reentry_exhausted` (hit `MAX_CLAIM_REENTRIES` with remaining ③ requests) — that is **not** a fail-loudly halt. The iteration agent writes `AUTO_ITERATION_FINAL_REPORT.md` with the unresolved claims surfaced in Section 8; the orchestrator copies those into the Ledger's `open_items[]` and continues to completion. The user reads `AUTO_ITERATION_FINAL_REPORT.md` for the review-detail view and `CLAIMS_LEDGER.md` for the pipeline-terminal view.
- **Budget awareness:** track total GPU-hours across experiment, verify, **and any `/run-experiment` calls fired inside iteration** (read from `review-stage/REVIEW_STATE.json`'s `gpu_hours_total` field, surfaced by the iteration agent's final summary), plus reviewer-call count in iteration. Flag if approaching user-defined limits. The iteration agent also surfaces `iterations_consumed` / `claim_reentries_consumed` against their caps — make these visible in the orchestrator's per-stage log line on iteration return.
- **Output language follows `task.md`.** Detect the dominant language of `task.md` (or of `$ARGUMENTS` when `task.md` is absent) and require every agent to write its report-style outputs — `IDEA_REPORT.md`, `FINAL_PROPOSAL.md`, `EXPERIMENT_RESULTS.md`, `VERIFY_REPORT.md`, `AUTO_REVIEW.md`, `CLAIMS_LEDGER.md`, etc. — in that language. Code, file paths, identifiers, and machine-readable artifacts (`*.json`, `*.csv`, `REVIEW_STATE.json`, `claims_ledger.json`) stay in English regardless.
- **Injecting `task.md` into each agent — two blocks, stage-scoped.** Not everything the user writes in `task.md` (or a related doc they designate) binds the same way, and not every item is relevant to every stage. The orchestrator front-injects **two** orchestrator-authored blocks, and **routes each extracted item only to the stage(s) it applies to** — never one undifferentiated dump into every agent (that both buries a stage's real constraints in noise and can mis-bind a stage-scoped item, e.g. a *verify-only* "may not run the same model" leaking into the main experiment that legitimately needs it):

  **① `## HARD CONSTRAINTS (from task.md — non-negotiable)` — 硬约束.** Mandatory directives, extracted **verbatim**. Three kinds:
  1. **Explicit budget / resource / compute allocation** — a stated GPU-hours / compute / wall-clock / $ budget, max usable GPUs, max parallel runs, or an allocation of specific devices / resources to specific stages. These also *enable* the run: a generous budget tells the agent **not** to simplify or abandon experiments to save cost (see the GPU-budget rule in `/auto-experiment`).
  2. **Negative prohibitions** — any *"don't / never / must-not / forbidden"* directive (a forbidden method / model / dataset / action).
  3. **Emphatic positive requirements** — a *"must"* directive naming a specific mandatory choice (e.g. "must use exactly xxx model", "when verifying claim x only use xxx dataset"). This front-injects the mandatory choice; the reproduction combo's `resource_fidelity: strict` marker is the separate, broader full-scale-fidelity mechanism for the whole main experiment — the two are complementary, not in conflict. (A plain *"use / prefer / should"* with no emphasis is **not** here — it should be in the NOTICE block below, not a hard constraint.)
  **② `## NOTICE (from task.md — informational, not authoritative)`.** Items the user named **without** mandatory force — non-emphatic model / dataset choices, environment notes, preferences, stylistic guidance. Injected so the receiving agent is *aware* of them, but framed as informational: the **authoritative** machine form is `EXPERIMENT_PLAN.md` (claim-authored), and an agent may adapt a notice item when the plan or a HARD constraint requires (e.g. a cost-aware smaller-model swap in verify). Never silently **drop** one; surface a conflict rather than picking a side.

  **Stage targeting.** Route each item by the **scope** the user gave it — read from explicit markers (`## Experiment Stage` / `[verify]` / "for claim 3") **or** inferred semantically from the prose:
  - **Global** (no stage / claim scope — a project-wide budget, a blanket prohibition) → inject into **every** stage.
  - **Stage- or claim-scoped** (names a stage / phase / activity owned by one stage — "when verifying …", "in the main experiment …", "during iteration …" — or a specific claim id) → inject **only into the stage(s) that own that work**, **plus the claim agent always** (claim authors `EXPERIMENT_PLAN.md` for every downstream stage, so it needs the full union to encode the scoping correctly). Carry the claim-id / stage qualifier verbatim so the receiving agent can match it (verify's block reads "for claim x only use xxx model"; experiment's does not).
  - **Ambiguous scope:** a **prohibition** errs **broad** (inject wherever it could bind — a forbidden model reaches every stage that might run it); a **positive notice / emphatic-positive** errs to the **named stage** (a "verify uses model Y" item does not constrain the main experiment).

  Ownership for routing: **claim** = idea + plan authoring (**always receives the full union** of both blocks — every stage's items); **experiment** = the main-experiment runs; **verify** = the swap-variant runs; **iteration** = the fix runs. So a main-experiment model pin lands in experiment (+claim); a verify-only model constraint lands in verify (+claim), never in experiment.

  Both blocks are re-injected on **every** stage dispatch and **every** resume, so no subagent runs without its slice. The agent honors block ① as non-negotiable — never exceed a cap, never do a forbidden thing, always satisfy an emphatic positive; on a genuinely impossible-under-constraint run it raises a Round-End Decision rather than crossing it. It treats block ② as awareness. **Notifications are not a constraint** — they are an orchestrator-side scheduled task (next bullet), never injected into any subagent, which need not know they exist. **Consistency on override:** both blocks are orchestrator-authored, so when the user overrides an item mid-run (raises / lifts a budget, lifts a prohibition, changes a pinned model / dataset), the orchestrator **regenerates the affected block** (stamped `— per user request @ <point>`) before the next dispatch / resume, instead of re-injecting the stale `task.md` value against the user's newer instruction, and — since lifting a stated cap / prohibition or changing a pinned choice **conflicts with the original** — appends the override to `task.md`'s `## User Overrides (log)` (Re-tasking §B step 3 — append-only, only on conflict, never touching the user's original body). This is the operational sibling of the output-language rule.
- **Notifications (opt-in via `task.md`, zero-impact otherwise).** When `task.md` opts into notifications (a `notify:` / `notification:` / `email-notify:` directive, or natural-language intent such as "notify/email me when …", in any language), the orchestrator invokes `/notify <event> <one-line reason>` at the touchpoints below. `/notify` drafts a progress briefing (fixed content spec — Progress / Plan / In-flight tasks / Next / Blocked·needs-manual-approval), saves it to `notification/` (never overwritten, never archived by `/next-round`), and dispatches it through whatever notification service the user configured. When `task.md` does **not** opt in, every call is a silent no-op and the pipeline behaves exactly as before. `/notify` never blocks and never fails loudly. Touchpoints:
  - **Hourly cadence during long-running waits** → `/notify hourly` — handled **entirely** by the `CronCreate` timer registered as the orchestrator's first action (see the ⏰ callout near the top). The timer fires `/notify hourly` on a real wall-clock schedule.
  - **After Experiment Gate returns** → `/notify progress "experiment done — <N> runs, ~<X> GPU-hours, headline: <positive|negative|inconclusive>"`.
  - **After Verify Gate returns** → `/notify progress "verify — <N_pass> PASS / <N_fail> FAIL / <N_inconclusive> INCONCLUSIVE / <N_zev> ZERO_ELIGIBLE"`.
  - **After the final ledger hook (terminal-state writeback into `CLAIMS_LEDGER.md`)** → `/notify done "pipeline <pipeline_status> — final state in CLAIMS_LEDGER.md"`.
  - **On fail-loudly halt or Round-End Decision** → `/notify halted "halted at <stage> — <one-line reason + remedy>"`.
  - **When the run is blocked on a human-only action** (a step needs sudo / credentials / disk-or-quota / an external approval the pipeline cannot perform) → `/notify approval-needed "<what is blocked> — action required: <the one thing the user must do>"`. This is the case a notification most exists for; surface it even under `AUTO_PROCEED=true`.
  Each touchpoint is a single non-blocking call; the orchestrator never waits for a reply.
