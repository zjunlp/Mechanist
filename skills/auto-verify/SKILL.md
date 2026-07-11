---
name: auto-verify
description: "Workflow 1.75: stress-test claims (regardless of main-experiment verdict) by swapping method, dataset, and model, then judging whether each variant agrees with the main experiment. Three stages with two integrity gates: Stage 1 audits the main experiment's eval method for every target claim; Stage 2 runs swap variants only on the top-K admitted claims picked by importance (K = `MAX_VERIFY_CLAIMS`, default 1); Stage 3 judges (binary pass/fail per variant), audits the variants, and computes a per-claim `robustness = #pass / N_eligible ∈ [0,1]` that decides PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS (threshold default 0.5 → at least half of eligible variants must pass; e.g. at N=3 this means ≥2 of 3). INCONCLUSIVE = main-experiment integrity broken (Phase 2 FAIL — variants never ran); ZERO_ELIGIBLE_VARIANTS = variants ran but all failed integrity at Phase 9; INTEGRITY_ONLY = Stage 1 audit passed but Stage 2 was intentionally skipped (either `SWAP_VARIANTS=false` global mode or per-claim `MAX_VERIFY_CLAIMS` cap — distinguished by `stage2_skip_reason`). All are valid on purpose: iteration fixes the main experiment for INCONCLUSIVE, only the variants for ZERO_ELIGIBLE_VARIANTS, and takes no action for INTEGRITY_ONLY. The goal is objective correctness, not maximizing PASS. No cross-claim aggregation. Use when user says \"verify\", \"robustness check\", \"stress test claim\"."
argument-hint: [claim-id-or-empty]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, AskUserQuestion, Skill, mcp__llm-chat__chat
---

# Workflow 1.75: Claim Verification

Stress-test claims by swapping method, dataset, and model — applied uniformly to every claim regardless of whether the main experiment supported or rejected it. Each variant runs, gets judged against the main experiment's verdict on the frozen claim, and contributes to a per-claim `robustness` score; the claim passes if `robustness ≥ ROBUSTNESS_THRESHOLD` (default 0.5).

For: **$ARGUMENTS**

## Overview

`/auto-experiment` produces per-run verdicts; `/result-to-claim` turns them into per-claim support. This skill asks a narrower but harder question: **does the variant reach the same conclusion as the main experiment when we change the method, the dataset, or the model?**

Per-variant we judge agreement as **binary** (`pass` / `fail`) — there is no middle "partial" tier; anything short of unambiguous agreement counts as `fail`. Per claim we aggregate as `robustness = #pass / N_eligible`, counted over the variants whose integrity check passed. The claim **PASSes** iff `robustness ≥ ROBUSTNESS_THRESHOLD` (default `0.5` — at least half of eligible variants must `pass`; e.g. at N=3 this means ≥2 of 3), otherwise **FAILs** — unless the eligible set is empty, in which case the claim is **ZERO_ELIGIBLE_VARIANTS** (a distinct terminal state, see below).

The pipeline runs in three stages, with two integrity gates:

1. **Stage 1 — Setup & Gate** (Phases 1–2). Parse arguments and identify target claims (no cap here — Stage 1 audits **every** target claim), then invoke two cross-model audits per claim on `refine-logs/`: `/experiment-audit` for evaluation methodology (fake GT, score normalization, phantom results, dead metric code, scope overclaim) and `/mechanism-audit` for mechanism-intervention rigor (steering coefficient sweep + reserved checks). The Phase 2 gate verdict for each claim is a single derived value `combined = max_severity(exp.overall_verdict, mech.overall_verdict)` with `n/a` (no mechanism intervention used) treated as `pass`. If `combined = FAIL` (i.e., at least one sub-audit returned FAIL → max_severity propagates FAIL), no PASS/FAIL on the claim is meaningful — the claim is marked **INCONCLUSIVE** here and Phase 3 step 0 short-circuits the rest of verify (Phases 3–10) to Phase 11 for that claim only. The `inconclusive_reason` names which sub-audit failed so iteration knows whether to fix evaluation, mechanism, or both.
2. **Stage 2 — Run variants** (Phases 3–7). Phase 3 step 0 picks the top-K admitted claims by importance (K = `MAX_VERIFY_CLAIMS`, default 1) — un-picked ADMITTED claims are marked `INTEGRITY_ONLY` with `stage2_skip_reason: max_verify_claims_cap` and skip to Phase 11. For each picked claim, pick alternatives, critique the plan, implement and (optionally) code-review each variant, deploy. Stage 2 ends when all variants have completed and raw metrics are on disk — no LLM judgment yet. Stage 2's exit gate lets you eyeball raw variant numbers before letting Stage 3 interpret them.
3. **Stage 3 — Judge, Audit & Aggregate** (Phases 8–11). For each variant of each picked claim, invoke `/result-to-claim` to judge whether its data supports the claim (Phase 8). Then run the variant-level integrity audit per claim (Phase 9) — symmetric to Phase 2, `/experiment-audit` + `/mechanism-audit` both run on the variant directory; each variant's `integrity_status` is the combined `max_severity(exp, mech)`. Integrity-FAIL variants are excluded from both numerator AND denominator. Then compute `robustness` once on the post-audit eligible set and assign **PASS / FAIL / ZERO_ELIGIBLE_VARIANTS** (Phase 10). Finally write the report (Phase 11). If fewer than `MIN_VARIANTS_FOR_VERDICT` variants survive integrity (default `MIN_VARIANTS_FOR_VERDICT=1`, so only `N_eligible = 0` triggers this), the claim is marked **ZERO_ELIGIBLE_VARIANTS** — variants did run, they just all failed integrity, so the iteration loop's instruction is "fix the variant evaluation, do not touch the main experiment."

Each claim ends in one of five states — **PASS** (main-experiment verdict is robust, in either direction — supported-and-stable OR rejected-and-stable), **FAIL** (main-experiment verdict is fragile under swaps), **INCONCLUSIVE** (main-experiment evaluation method or mechanism rigor is broken at Phase 2; variants never ran), **ZERO_ELIGIBLE_VARIANTS** (variants ran but every one failed Phase 9 integrity; no robustness verdict computable), or **INTEGRITY_ONLY** (Stage 1 audit passed but Stage 2 was intentionally skipped — either `SWAP_VARIANTS=false` global mode, or per-claim `MAX_VERIFY_CLAIMS` cap; the two are distinguished by the `stage2_skip_reason` field). The pipeline's goal is objective correctness: PASS and FAIL are both valid scientific outcomes; INCONCLUSIVE and ZERO_ELIGIBLE_VARIANTS each flag a different methodology break that iteration must fix on a different surface (main experiment vs. variants); INTEGRITY_ONLY names what was checked (integrity) and what was not (robustness) so iteration can no-op cleanly.

**When `SWAP_VARIANTS=false` (audit-only mode)**, Phase 2 runs per-claim as usual; a new step 4 at the end of Phase 2 pre-writes each claim's `ROBUSTNESS.md` (`INTEGRITY_ONLY` with `stage2_skip_reason: swap_variants_false` when combined pass/warn, `INCONCLUSIVE` when combined fail — same semantics as the full-pipeline INCONCLUSIVE) and jumps to Phase 11. Phases 3–10 do not run. Only PASS / FAIL / ZERO_ELIGIBLE_VARIANTS are replaced by INTEGRITY_ONLY; INCONCLUSIVE is unchanged.

No cross-claim aggregation: each claim is reported independently.

```
Workflow 1.5 output:                  This skill (Stage 1 → 2 → 3):                              Workflow 2 input:
refine-logs/EXPERIMENT_RESULTS.md →   Stage 1 (Phases 1-2): parse + main-experiment audit                verify/VERIFY_REPORT.md
refine-logs/EXPERIMENT_PLAN.md           (experiment + mechanism, combined)                      with per-claim PASS / FAIL /
idea-stage/IDEA_REPORT.md                ├─ combined = FAIL → INCONCLUSIVE                          INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS /
                                         └─ combined = PASS/WARN → continue                          INTEGRITY_ONLY (SWAP_VARIANTS=false)
                                             │                                                    ready for /auto-iteration-loop
                                             ├─ SWAP_VARIANTS=false → INTEGRITY_ONLY (skip to Phase 11)
                                             └─ SWAP_VARIANTS=true  → Stages 2–3 below
                                       Stage 2 (Phases 3-7): pick swaps → run variants (raw metrics only)
                                       Stage 3 (Phases 8-11): /result-to-claim per variant
                                                              → variant integrity audit (per claim,
                                                                experiment + mechanism, combined)
                                                                (excludes untrusted variants from both
                                                                 numerator & denominator)
                                                              → robustness (single pass)
                                                              → PASS / FAIL                       (N_eligible ≥ 1)
                                                              → ZERO_ELIGIBLE_VARIANTS            (N_eligible = 0)
```

## Constants

- **DIMENSIONS = `model`** — Which swap axes to run, **and therefore how many variants per claim** (exactly one swap per listed axis). List or comma-separated subset of `{method, dataset, model}`. Examples:
  - default `model` → 1 variant/claim (model swap only)
  - `method,dataset` → 2 variants/claim
  - `method,dataset,model` → 3 variants/claim (broad stress test)

  Override: `— dimensions: method,dataset,model` to broaden. No separate "effort" multiplier — to test more variants, broaden DIMENSIONS (already capped at 3 axes); deeper analyses like multi-seed runs or 2-factor cross-axis swaps are out of scope for verify and belong in `/ablation-planner`.
- **VARIANTS_PER_CLAIM** — derived, equals `len(DIMENSIONS)`. Not a separately tunable constant.
- **TARGET_CLAIMS = `all`** — Claims to verify. Default `all` covers every claim in `EXPERIMENT_PLAN.md` regardless of main-experiment verdict — both supported claims (verify the support is robust across swaps) and not-supported claims (verify the rejection is robust). Other options: `passed` (only claims with `main_experiment_verdict = supported` from `refine-logs/main-experiment-verdicts.json`), `failed` (only claims with `main_experiment_verdict = not-supported` — useful when you want to verify just the negative findings), or a specific claim id (`C1`, `C2`, ...). Note `passed ∪ failed = all` with no overlap.
- **MAX_VERIFY_CLAIMS = 1** — Cap on how many claims proceed from Stage 1 (main-experiment integrity audit) into Stage 2 (swap variants). Stage 1 **always audits every target claim** — the cap only gates Stage 2 entry. If the Stage-1-admitted pool exceeds the cap, Phase 3 step 0 picks the top-K claims by importance judgment (reading each admitted claim's statement against upstream context like `IDEA_REPORT.md` / `## Rationale` sections; row order is **not** a priority signal). Un-picked admitted claims are marked `INTEGRITY_ONLY` with `stage2_skip_reason: max_verify_claims_cap`; user can swap-test them later via `/auto-verify <claim-id> — resume: true` (Stage 1 audit is reused via RESUME). Default `1` → exactly one swap-tested claim per pass (with default `DIMENSIONS=model`: 1 × 1 = 1 variant run per pass); raise via `— max-verify-claims: 3` to broaden coverage.
- **CODE_REVIEW = true** — external LLM reviewer checks each variant's code before deployment. Set `false` to skip.
- **SANITY_FIRST = true** — run the cheapest variant first (smallest split, fewest steps) before launching the rest.
- **AUTO_DEPLOY = true** — deploy variants automatically after implementation + review. Set `false` to manually inspect.
- **MAX_PARALLEL_RUNS = 4** — concurrent variant runs.
- **GPU_ID = `auto`** — GPU device(s) to use for variant runs. Options: `auto` (inherit from environment / let launcher decide), a single id (`0`), or a comma-separated list (`4,5,6,7`). When set to anything other than `auto`, the skill **passes `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional arg to `/run-experiment`** (sanity checks and reviewer-triggered re-runs same convention); the run-experiment skill exports it internally before launching the experiment subprocess. Do **not** treat the positional as a shell prefix — `/run-experiment` is a Skill, not a shell command. Override: `— gpu-id: 4,5,6,7`
- **ROBUSTNESS_THRESHOLD = 0.5** — Hyperparameter (configurable). A claim passes verify iff `robustness ≥ ROBUSTNESS_THRESHOLD`, where `robustness = #pass / N_eligible` over the variants that survived the integrity audit (Phase 9). Default `0.5` ≈ "at least half of eligible variants must `pass`". Discrete consequences at typical `N_eligible`:
  - `N_eligible = 1` (default under `DIMENSIONS=model`) → robustness ∈ {0, 1}; only 1/1 = 1.0 satisfies the threshold (any single fail ⇒ claim FAIL)
  - `N_eligible = 2` → need ≥1 of 2 variants to pass (1/2 = 0.5 satisfies `≥ 0.5`)
  - `N_eligible = 3` → need ≥2 of 3 variants to pass (2/3 ≈ 0.667 satisfies; 1/3 ≈ 0.333 does not)

  Tighten with `— robustness-threshold: 0.67` to require unanimity at N=3 (need 3/3, since 2/3 ≈ 0.667 < 0.67); loosen to `— robustness-threshold: 0.33` to admit any single passing variant at N=3 (1/3 ≈ 0.333 ≥ 0.33). Note: `N_eligible` excludes variants whose integrity check returned FAIL from **both** the numerator and the denominator (an untrusted variant means "we don't know what this variant says", not "this variant disagrees"). If `N_eligible < MIN_VARIANTS_FOR_VERDICT`, no PASS/FAIL verdict is issued — the claim is marked **ZERO_ELIGIBLE_VARIANTS** instead (distinct from INCONCLUSIVE; see Phase 10's final-state table).
- **MIN_VARIANTS_FOR_VERDICT = 1** — Minimum number of integrity-clean variants required to issue a PASS/FAIL verdict on a claim. Default `1` means even a single eligible variant still produces a verdict rather than ZERO_ELIGIBLE_VARIANTS. Set to `2` or `3` for stricter projects where you want at least two independent axes to agree before issuing PASS/FAIL. ZERO_ELIGIBLE_VARIANTS is only triggered when `N_eligible < MIN_VARIANTS_FOR_VERDICT` (i.e., default: every variant failed integrity → `N_eligible = 0`). Override: `— min-variants-for-verdict: 2`.
- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask for strict, high-rigor feedback.
- **COMPACT = false** — When `true`, write only `verify/VERIFY_REPORT.md` (skip per-claim `ROBUSTNESS.md`).
- **AUTO_PROCEED = true** — If user doesn't respond at a checkpoint, proceed with best option.
- **RESUME = false** — When `true`, each phase checks if its primary artifact already exists non-empty and skips itself if so (see "Resume protocol" below). Useful for picking up after a crash. Default `false` = every phase always runs from scratch and overwrites prior artifacts. Resume never deletes pre-existing files.
- **STOP_AFTER_STAGE = `none`** — Halt after completing the named stage. Options: `1` (stop after Phase 2 — main-experiment audits done, before any GPU spent on variants), `2` (stop after Phase 7 — variants deployed and completed, raw metrics on disk, before any LLM judgment / integrity audit / aggregation), `3` or `none` (default — run all 11 phases through the report). Useful for human-in-the-loop inspection: run Stage 1 only → review main-experiment audits → commit GPU → re-invoke; or stop at Stage 2 to eyeball raw variant metrics before letting LLMs interpret them. Override: `— stop-after-stage: 1`.
- **SWAP_VARIANTS = `true`** — Whether the swap-variant stress test (Stages 2–3) runs on top of Stage 1's main-experiment integrity audit. Default `true` = full 3-stage pipeline. Set `false` for **audit-only mode**: Phase 2 runs as usual and its new step 4 pre-writes each claim's `ROBUSTNESS.md` — `INTEGRITY_ONLY` with `stage2_skip_reason: swap_variants_false` when combined `pass`/`warn`, `INCONCLUSIVE` when combined `fail` (same semantics as the full-pipeline INCONCLUSIVE) — then jumps to Phase 11. Phases 3–10 do not run. Phase 11 renders an audit-only report shape with a `swap_variants: false` banner. Distinct from `STOP_AFTER_STAGE=1`: that flag is a human-in-the-loop halt that leaves no final report; `SWAP_VARIANTS=false` treats Stage 1 as the intended terminal deliverable and always writes the report. To upgrade later without re-auditing: `/auto-verify <same-args> — swap-variants: true, resume: true` (Phase 2 audits reused via RESUME; only Stages 2–3 execute). Override: `— swap-variants: false`.

> Standalone overrides: `/auto-verify C1 — robustness-threshold: 0.67, max-verify-claims: 5, dimensions: method,dataset, min-variants-for-verdict: 2, gpu-id: 4,5,6,7, stop-after-stage: 1`. (To restrict to only main-experiment-supported claims, pass `target-claims: passed`; for only main-experiment-rejected ones, `target-claims: failed`; default `all` is usually what you want. `stop-after-stage: 1` lets you inspect the per-claim main_experiment_audit/ results before committing GPU to Stages 2–3.)

## Inputs

This skill expects one or more of:

1. **`refine-logs/EXPERIMENT_PLAN.md`** — claim map with `C1`, `C2`, ... and evidence requirements (the `## Claim-to-Milestone Map` table)
2. **`refine-logs/EXPERIMENT_RESULTS.md`** — post-hoc per-claim conclusions written by `/auto-experiment` (canonical source for main-experiment verdicts; Phase 1 step 2(b) parses this into `refine-logs/main-experiment-verdicts.json`)
3. **`refine-logs/EXPERIMENT_TRACKER.md`** — milestone-level run status (M1a, M2b, ...); rows used by `/experiment-audit` and `/mechanism-audit` for per-claim scoping
4. **`refine-logs/FINAL_PROPOSAL.md`** — method description for implementation context
5. **`idea-stage/IDEA_REPORT.md`** or **`idea-stage/IDEA_CANDIDATES.md`** — prior research used to pick alternatives
6. **`refine-logs/main-experiment-verdicts.json`** (built lazily in Phase 1 step 2(b) if absent) — structured per-claim main-experiment verdict, read by Phases 1 / 8
7. **`EXPERIMENT_AUDIT.json`** + **`MECHANISM_AUDIT.json`** (both built by Phase 2 per claim; if pre-existing, their combined verdict — `max_severity(exp, mech)` — is reused as the per-claim integrity gate)

> **Resource-Fidelity Harness does NOT apply to verify.** `refine-logs/FINAL_PROPOSAL.md` / `EXPERIMENT_PLAN.md` may carry a `resource_fidelity: strict` marker (written by `/auto-claim` for the reproduction combination — `behavior-source:given` + `mechanism:given`). That marker binds the **main experiment** (`/auto-experiment`) only — it forbids cost-driven downscaling of the *main experiment* runs. Verify's whole job is to **deliberately swap** the model / dataset / method (the `DIMENSIONS` axes) to test robustness, so verify **ignores** this marker: do not treat a model/dataset swap as a harness violation, and do not refuse a swap because the main experiment was marked `strict`. Pick alternatives exactly as normal regardless of the marker.

If none exist, ask the user which claim to verify and accept a free-form claim statement.

## Workflow

### Resume protocol (only when `RESUME = true`)

Skip entirely if `RESUME = false` (default). When `true`, each phase begins with a **skip-if-present** check:

| Phase | Primary artifact (skip key) | Notes |
|---|---|---|
| 1    | always run (cheap argument parsing) | — |
| 2    | for each target Cx, ALL of `verify/<claim_dir>/main_experiment_audit/{EXPERIMENT_AUDIT.md, EXPERIMENT_AUDIT.json, MECHANISM_AUDIT.md, MECHANISM_AUDIT.json}` exist non-empty | Main-experiment integrity audit, **per claim**, **two cross-model audits**. Skip the `/experiment-audit` call for any Cx whose `EXPERIMENT_AUDIT.{md,json}` are present; skip the `/mechanism-audit` call independently when `MECHANISM_AUDIT.{md,json}` are present. Even on full skip, re-read both JSONs and recompute the combined verdict every invocation (cheap, deterministic) to decide whether Cx enters Stages 2–3 or is short-circuited to INCONCLUSIVE. |
| 3    | Step 0 always runs (re-reads `verify/INTEGRITY_AUDIT.md` to rebuild ADMITTED/REJECTED buckets, tops up FAIL claims' `ROBUSTNESS.md` stub, then re-uses `verify/STAGE2_PICK.json` if present-non-empty to skip the LLM importance-judgment call and rebuild the PICKED set). Step 1 (pick-alternatives) skips per claim if `verify/<claim_dir>/PLAN.md` already exists non-empty. | Re-reading from disk is the only safe re-entry mechanism after a `STOP_AFTER_STAGE=1` halt — Phase 3 cannot trust in-memory state from Phase 2. |
| 4    | always re-runs (no clean per-claim skip artifact in the current design) | Phase 4 is a single reviewer LLM call per claim — cheap, not GPU-bound. Skipping it would require Phase 4 to leave a deterministic sentinel (e.g., a `reviewed: true` frontmatter field in `PLAN.md`); since it doesn't, RESUME re-pays the LLM cost. Acceptable in practice. |
| 5    | `verify/<claim_dir>/variants/<variant-tag>/` has code committed | Per-variant: skip code generation for variants whose directory is already populated. |
| 6    | reviewer-approved marker per variant (e.g., `.code_review_passed`) | Per-variant. |
| 7    | per-variant run status — sanity row + `done` in tracker | Per-variant: don't redeploy completed variants. |
| 8    | per-variant `verify/<claim_dir>/variants/<variant-tag>/verdict.json` exists non-empty | Per-variant `/result-to-claim` judgment. Skip the call for any variant whose verdict.json is already on disk. |
| 9    | for each admitted claim Cx, ALL of `verify/<claim_dir>/variant_audit/{EXPERIMENT_AUDIT.md, EXPERIMENT_AUDIT.json, MECHANISM_AUDIT.md, MECHANISM_AUDIT.json}` exist non-empty AND every Cx variant has both `integrity_status` AND `integrity_breakdown` in its `verdict.json` | Variant-level integrity audit, **per claim** (symmetric to Phase 2, **two cross-model audits**). Skip the `/experiment-audit` call when its two artifacts are present; skip `/mechanism-audit` independently when its two artifacts are present. The main-experiment-integrity section of `INTEGRITY_AUDIT.md` is filled by Phase 2, not here. |
| 10   | `verify/<claim_dir>/ROBUSTNESS.md` exists non-empty with `verdict` field per claim | Per-claim robustness aggregation. Skip when ROBUSTNESS.md is fully populated. **Caveat (COMPACT mode):** when `COMPACT = true`, ROBUSTNESS.md is intentionally not written, so this skip key never matches and Phase 10 always re-runs on RESUME. That's acceptable because Phase 10 is pure arithmetic over already-on-disk `verdict.json` files (no LLM calls, no GPU). |
| 11   | `verify/VERIFY_REPORT.md` exists non-empty AND all per-claim `ROBUSTNESS.md` verdicts present AND `INTEGRITY_AUDIT.md` present (covering main experiment + variants) | Skip the final report if everything is already aggregated + audited. |

Log every skip as `[resume] phase <N> skipped — <reason>`. Resume never deletes pre-existing files. To force a variant to re-run, delete its directory under `verify/<claim_dir>/variants/`.

> **Two-audit rows (Phases 2 & 9) — top-level predicate vs per-sub-audit independence.** The "Primary artifact" column lists ALL of the four files for the full-skip case. That top-level `ALL of {…}` predicate decides whether the phase emits `[resume] phase <N> skipped` and does no work. The per-sub-audit clauses ("skip `/experiment-audit` … skip `/mechanism-audit` independently …") run **regardless** of the top-level predicate — they are the partial-state branch:
>
> - Both pairs present → full skip (top-level predicate true).
> - Only one pair present → phase runs, but skips that sub-audit's call; the other sub-audit runs to populate its missing files.
> - Neither pair present → phase runs both sub-audits.
>
> The combined-verdict computation (Phase 2 step 2 / Phase 9 step 2) always reads whichever JSONs end up on disk after the phase finishes, applying the Defensive Read rules described under Phase 2 step 2.

> **Path expansion in resume checks.** `<claim_dir>` is a glob, not a literal: when testing whether a per-claim artifact exists, expand with `ls -d verify/<claim_id>_*/ 2>/dev/null` (or `compgen -G "verify/<claim_id>_*"`), then test `[ -s "$dir/ROBUSTNESS.md" ]`. A naive `[ -s "verify/<claim_id>/ROBUSTNESS.md" ]` will never match — the on-disk directory is `verify/<claim_id>_<short_claim>/` (see the `<claim_dir>` notation block at the end of this file). The same expansion applies to every `<claim_dir>` reference in this skill.

### Phase 1: Parse Arguments and Identify Target Claims

1. Parse `$ARGUMENTS`:
   - Empty → `TARGET_CLAIMS = all` (default): verify every claim in `EXPERIMENT_PLAN.md`, regardless of whether the main experiment supported or rejected it
   - A claim id (e.g., `C1`, `C2`) → verify that one claim only
   - A free-form phrase → match against claim statements in `EXPERIMENT_PLAN.md`; if no match, ask user
   - `— target-claims: passed` → restrict to only main-experiment-supported claims (`main_experiment_verdict = supported` from `main-experiment-verdicts.json`)
   - `— target-claims: failed` → restrict to only main-experiment-rejected claims (`main_experiment_verdict = not-supported`)
   - `— dimensions: ...` override → parse the comma-separated axis list. Validate each entry is one of `method`, `dataset`, `model`; reject unknown axes. Empty list is illegal — fall back to default `model`. Store the resolved list as the effective `DIMENSIONS`.
   - `— stop-after-stage: <1|2|3|none>` override → parse the value. `1` halts after Phase 2; `2` halts after Phase 7; `3` and `none` (default) run all 11 phases. Other values reject with `[verify] invalid stop-after-stage: <value> — expected 1, 2, 3, or none`. Store as effective `STOP_AFTER_STAGE`.

2. Build the target-claim list:

   **(a) Read the plan.** Open `refine-logs/EXPERIMENT_PLAN.md` and parse the `## Claim-to-Milestone Map` table (columns: `Claim | Tests | Required milestones | Pass criterion`). Each row is one claim. The "Required milestones" column gives that claim's milestone IDs (e.g. `M1, M2`), which downstream phases use to scope per-claim audits via `EXPERIMENT_TRACKER.md` (whose rows are milestone sub-tasks like `M1a`, `M2b`, ...).

   **(b) Resolve per-claim main-experiment verdicts** — `refine-logs/main-experiment-verdicts.json` is the single source of truth for every downstream phase. Build it lazily:

   ```
   if refine-logs/main-experiment-verdicts.json exists:
       load it. Verify it covers every Cx in the plan; if any Cx is missing, treat as cache-miss and rebuild.
   else (cache-miss):
       Read refine-logs/EXPERIMENT_RESULTS.md (canonical post-hoc verdict source — written by /auto-experiment's final summary).
       Try to extract a per-claim verdict directly from its prose:
         - regex-friendly forms:
             * "C1 ... is supported"                                    → supported
             * "C3 ... is falsified | rejected | not supported"         → not-supported
             * "C2 ... is partially supported | mixed | inconclusive"   → not-supported
               (binary scheme: anything short of unambiguous support is treated as not-supported)
         - target vocabulary: {supported, not-supported}
       If extraction is ambiguous OR EXPERIMENT_RESULTS.md has no per-claim paragraphs,
       invoke /result-to-claim once on the whole results file to translate prose → structure:
           /result-to-claim "refine-logs/EXPERIMENT_RESULTS.md — extract per-claim verdicts only"
       /result-to-claim returns pass | fail per claim; map pass → supported, fail → not-supported.
       Persist the result as refine-logs/main-experiment-verdicts.json:
           {
             "C1": { "main_experiment_verdict": "supported",     "main_experiment_metric": "...", "confidence": "high"   },
             "C2": { "main_experiment_verdict": "not-supported", "main_experiment_metric": "...", "confidence": "medium" },
             ...
           }
   ```

   This file is read by Phase 1 (target-claim filtering + per-claim record building) and Phase 8 (carrying `main_experiment_verdict` into every variant's `verdict.json`). No later phase re-reads it: Phase 11 picks up `main_experiment_verdict` from `verdict.json` (which got it from Phase 8, which got it from this file). Never re-parse `EXPERIMENT_RESULTS.md` ad-hoc later in the pipeline.

   If `EXPERIMENT_RESULTS.md` itself is missing, abort with `[verify] no refine-logs/EXPERIMENT_RESULTS.md — run /auto-experiment first`. Do not invent verdicts.

   **(c) Build per-claim records.** For each target claim, collect:
     - `claim_id` — e.g. `C1`
     - `statement` — full claim text from the plan
     - `short_claim` — a **4-word snake_case slug** derived from the claim's section heading or statement in `EXPERIMENT_PLAN.md`, used to name the per-claim folder. Example: claim C1's heading "Silhouette Diagnostic & Polysemantic-by-Context Taxonomy" → `polysemantic_by_context`; C3's "Ablation-Rank Faithfulness" → `ablation_rank_faithfulness`. Stay descriptive over clever; see the `<claim_dir>` notation block at the end of this file for naming rules.
     - `linked_milestones` — list of milestone IDs from the plan's Claim-to-Milestone Map, e.g. `[M1, M2]`. Phase 2 uses this to scope `/experiment-audit — claim Cx`.
     - `minimum_evidence` — from the plan's pass criterion column
     - `main_experiment_metric`, `main_experiment_verdict` (`supported | not-supported`), `confidence` — read from `refine-logs/main-experiment-verdicts.json[Cx]`

   `main_experiment_verdict` for each Cx is fixed at this point and propagates unchanged through Phases 2, 8, 9, 10 — no phase re-derives it.

3. Present the target-claim summary:

```
🎯 Stage 1 audit targets: [N] claim(s)  (all target claims are audited; MAX_VERIFY_CLAIMS = [cap] gates Stage 2 entry only)

- C1: [one-line statement] — main-experiment verdict: supported / not-supported, confidence: high/medium
  main experiment: [method]+[dataset]+[model] → [metric = value]
- C2: ...

Dimensions to test: [DIMENSIONS list]
Variants per picked claim: [len(DIMENSIONS)]  (one swap per listed axis)
Stage 2 cap (top-K by importance): [MAX_VERIFY_CLAIMS]
Expected Stage 2 variant runs (upper bound): [min(cap, N_admitted) × len(DIMENSIONS)]  (N_admitted resolved after Phase 2)
Estimated GPU-hours: [X]

Proceeding to Phase 2 audit.
```

`VARIANTS_PER_CLAIM = len(DIMENSIONS)` — no scaling, no multiplier.

If the resolved target-claim list is empty after Phase 1 (e.g., `TARGET_CLAIMS = passed` but no claim is `supported`; `TARGET_CLAIMS = failed` but every claim was supported; or `EXPERIMENT_PLAN.md` is missing / has zero claims) → stop and report `[verify] no target claims — abort`. Do **not** invent claims or auto-relax `TARGET_CLAIMS` to fill the list. Return this to the orchestrator as a **Round-End Decision** (`ended-needs-decision (verify: no-target)`) so it writes the decision record and the user chooses the next round (see `auto/SKILL.md` → "Round-End Decision").

### Phase 2: Per-Claim Main-Experiment Integrity Audit (Stage 1 gate)

**Why this runs first.** Verify's PASS/FAIL is meaningful only if both (a) the main experiment's *evaluation method* is itself trustworthy AND (b) the interpretability mechanism backing the claim (if any) was actually tuned. If the main experiment derives its "ground truth" from another model's output, normalizes scores by the model's own max, claims numbers from files that don't exist, or generalizes from a handful of cases — or if the steering coefficient was copied verbatim from another paper without a sweep — then both supported-and-stable and rejected-and-stable verdicts are built on sand. Catching this **before** spending GPU on swap variants saves compute *and* prevents polluting the record with a confidently wrong verdict in either direction.

This is the gate for **Stage 1**. Two cross-model audits run per claim: `/experiment-audit` for evaluation-methodology honesty, `/mechanism-audit` for mechanism-intervention rigor. Each claim's evidence is scoped via `EXPERIMENT_PLAN.md`'s `## Claim-to-Milestone Map` (which gives each claim its required milestones) crossed with `EXPERIMENT_TRACKER.md` (whose rows are the milestone sub-tasks like `M1a`, `M2b`, ...). A clean claim is not punished by another claim's dirty evidence. Each claim's combined gate verdict (PASS/WARN/FAIL) is decided independently from `max_severity(exp.overall_verdict, mech.overall_verdict)`, with `n/a` treated as `pass` so non-mechanistic claims are not penalised by the mechanism audit. PASS/WARN claims advance to Stages 2–3 (Phases 3–10); FAIL claims become INCONCLUSIVE for this run and skip straight to Phase 11. The full workflow continues if at least one claim is admitted.

> **Cost note.** Per-claim auditing recomputes shared-infrastructure checks once per claim and now runs two cross-model audits (`/experiment-audit` + `/mechanism-audit`) per Cx — roughly `2 × N_target` LLM calls, where `N_target = |target claims|` (Stage 1 audits every target claim; `MAX_VERIFY_CLAIMS` does not shrink this set). For projects with `N_target > 10` or unusually large eval scripts, this can dominate verify cost; in that regime, consider a project-wide pre-check (`/experiment-audit "refine-logs/" — claim <any-Cx>` plus `/mechanism-audit "refine-logs/" — claim <any-Cx>`) as a cheap fast-fail before per-claim audits. The default `MAX_VERIFY_CLAIMS = 1` bites only at Stage 2 (variant GPU cost), not Stage 1.

#### 1. For each target claim Cx, invoke `/experiment-audit` AND `/mechanism-audit` scoped to Cx

Two cross-model audits run per claim, in sequence, into the same per-claim main_experiment_audit folder. `/experiment-audit` covers evaluation-methodology honesty (A–F: GT, normalization, file existence, dead code, scope, eval type); `/mechanism-audit` covers mechanism-intervention rigor (A: steering coefficient sweep; B–F reserved). The two are independent and write to disjoint filenames.

For each Cx in the target-claim list (from Phase 1), construct the per-claim folder slug `<claim_dir>` = `<claim_id>_<short_claim>` (see the `<claim_dir>` notation block at the end of this file) and run:

```bash
mkdir -p "verify/<claim_dir>/main_experiment_audit"
/experiment-audit "refine-logs/" — claim <Cx> — output-dir "verify/<claim_dir>/main_experiment_audit"
/mechanism-audit  "refine-logs/" — claim <Cx> — output-dir "verify/<claim_dir>/main_experiment_audit"
```

Both skills write directly to the per-claim location via `— output-dir`; no follow-up `mv` is required:

- `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md` — full A–F findings scoped to Cx's evidence
- `verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.json` — `overall_verdict` is Cx's methodology-integrity verdict
- `verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.md` — mechanism-rigor findings (steering coefficient sweep + reserved checks)
- `verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.json` — `overall_verdict` is Cx's mechanism-rigor verdict (may be `n/a` when Cx uses no mechanism intervention)

`/experiment-audit`'s 6 checks cover failure modes that would invalidate Cx's main-experiment verdict in either direction (i.e., regardless of whether the main experiment said supported or not-supported). Checks A/B/D/F audit the **shared infrastructure** (eval scripts, configs, dataset) that every claim uses; Checks C/E are **claim-scoped** to Cx:

- A. GT provenance — is "ground truth" loaded from the dataset, or derived from model output?
- B. Score normalization — is any metric divided by the model's own max/mean?
- **C. Result file existence (claim-scoped)** — do the numbers Cx cites in `EXPERIMENT_RESULTS.md` / `EXPERIMENT_TRACKER.md` exist at the claimed paths/keys?
- D. Dead code — are evaluation functions defined but never actually called?
- **E. Scope (claim-scoped)** — does Cx's wording ("comprehensive", "extensive") exceed Cx's actual number of scenes/seeds?
- F. Evaluation type — `real_gt | synthetic_proxy | ...`?

`/mechanism-audit`'s checks audit mechanism-intervention rigor for Cx:

- **A. Steering Coefficient Sweep** — was α swept across ≥ 3 orders of magnitude; σ_proj-scaled; logged alongside a capability/coherence metric; locked mid-plateau; controlled with random-direction baseline; sign pattern preserved for asymmetric protocols? Returns `n/a` when Cx's experiment uses no additive intervention on internal representations.
- **B–F. Reserved** — placeholders for future mechanism-rigor checks (direction-extraction quality, site / layer choice, n_effective sufficiency, probe-vs-causal disentanglement, intervention scope). Currently report `not_implemented`.

#### 2. Combine per-claim verdicts and decide per-claim gates

Read both `EXPERIMENT_AUDIT.json` and `MECHANISM_AUDIT.json` for each Cx, then compute the **combined per-claim integrity verdict** using `max_severity` over the two `overall_verdict` fields.

**Defensive read** — when a sub-audit's JSON is missing (file does not exist, empty, or unparseable):

- `MECHANISM_AUDIT.json` missing → treat `sev_mech := 0` (n/a-equivalent). Log `[main-experiment-audit] claim=<Cx> mech_audit missing — defaulting sev_mech=0 (n/a). Run /mechanism-audit to populate.` Do NOT abort the gate; the claim is then judged purely on `/experiment-audit`'s verdict. This is the expected path on legacy refine-logs/ trees from before mechanism-audit was deployed.
- `EXPERIMENT_AUDIT.json` missing → symmetric: `sev_exp := 0` and log the symmetric warning. This is rarer (Phase 2 invokes experiment-audit first), but a resume from a corrupted/hand-edited tree can hit it.
- BOTH missing on a non-skip path → hard abort with `[verify] no integrity audits for <Cx> — Phase 2 did not run cleanly`. Do not silently default to pass.

```
severity(fail) = 3
severity(warn) = 2
severity(pass) = 1
severity(n/a)  = 0          # n/a contributes no severity — a claim that uses
                            # no mechanism intervention is not penalised
inverse_severity = { 1: "pass", 2: "warn", 3: "fail" }   # defined only on {1,2,3};
                                                          # the s == 0 branch below
                                                          # is the only path to "pass"
                                                          # via severity 0.
combined_verdict =
    let sev_exp  = severity(exp.overall_verdict)         # 0 if exp JSON missing
    let sev_mech = severity(mech.overall_verdict)        # 0 if mech JSON missing
    let s        = max(sev_exp, sev_mech)
    if s == 0 then "pass"                # both n/a (or both missing) → pass
    else inverse_severity(s)             # 1→pass, 2→warn, 3→fail
```

Branch **independently** on `combined_verdict` for each Cx:

| Combined verdict | Action for Cx | Reason |
|---|---|---|
| `pass` | Admit Cx to Phases 3–10 normally. | Cx's evaluation method is trustworthy AND the mechanism (if any) was tuned with the necessary controls. |
| `warn` | Admit Cx, but Cx's row in `INTEGRITY_AUDIT.md` / `VERIFY_REPORT.md` carries `[MAIN-EXPERIMENT INTEGRITY: WARN]` with the offending sub-audit name (e.g., `[MAIN-EXPERIMENT INTEGRITY: WARN — mechanism]`). The final Cx PASS/FAIL is still issued. | Soft issue in at least one sub-audit (scope language slightly overclaims; α at plateau edge; …) — verdict still informative. |
| `fail` | **Mark Cx INCONCLUSIVE** with a sub-audit-specific `inconclusive_reason`: `main-experiment integrity broken` (exp = fail, mech ≠ fail), `main-experiment mechanism rigor broken` (mech = fail, exp ≠ fail), or `main-experiment integrity broken (experiment + mechanism)` (both fail). Each reason links to the relevant `*_AUDIT.md` (see step 3 below for the canonical strings). Skip Phases 3–10 for Cx only. Other claims continue independently. | Cx's main experiment cannot be trusted in either direction; running swaps on top would just compute robustness around a broken anchor. |

The all-FAIL short-circuit (when every Cx returns combined `fail`, skip Phases 3–10 and jump to Phase 11) is handled by Phase 3's Step 0 — see below. Phase 2 itself only writes per-claim verdicts; it does not branch the overall workflow.

Log per claim:

```
[main-experiment-audit] claim=<Cx> exp_verdict=<pass|warn|fail> mech_verdict=<pass|warn|fail|n/a> combined=<pass|warn|fail>
[main-experiment-audit] claim=<Cx> exp_source=verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.json
[main-experiment-audit] claim=<Cx> mech_source=verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.json
[main-experiment-audit] claim=<Cx> action=<continue|continue-with-warn|skip-to-inconclusive>
```

#### 3. Initialize `INTEGRITY_AUDIT.md` with per-claim main-experiment verdict rollup

Write `verify/INTEGRITY_AUDIT.md` with the **per-claim verdict table only** — this file is the index; per-claim A–F detail lives under each `<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md` and `<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.md`. Do not duplicate the per-claim reports here.

```markdown
# Integrity Audit

**Overall**: [PASS | WARN | FAIL]    ← max severity across main experiment + variants
**Main-experiment integrity (Phase 2)**: [PASS | WARN | FAIL]    ← max severity across main-experiment combined verdicts
**Variant integrity (Phase 9)**: [PASS | WARN | FAIL]     ← filled by Phase 9

## Main-experiment integrity (Phase 2, per-claim)

| Claim | Exp. audit | Mech. audit | Combined | Gate decision                   | Detail |
|-------|------------|-------------|----------|---------------------------------|--------|
| C1    | PASS       | PASS        | PASS     | continue                        | verify/C1_xxx/main_experiment_audit/ |
| C2    | PASS       | WARN        | WARN     | continue-with-warn (mechanism)  | verify/C2_yyy/main_experiment_audit/ |
| C3    | FAIL       | N/A         | FAIL     | INCONCLUSIVE (experiment broken)| verify/C3_zzz/main_experiment_audit/ |
| C4    | PASS       | FAIL        | FAIL     | INCONCLUSIVE (mechanism broken) | verify/C4_www/main_experiment_audit/ |

> Column glossary:
> - **Exp. audit** — `overall_verdict` of `/experiment-audit` on this claim.
> - **Mech. audit** — `overall_verdict` of `/mechanism-audit` on this claim. `N/A` when the claim uses no mechanism intervention.
> - **Combined** — `max_severity(exp, mech)` with `fail > warn > pass > n/a` and `n/a` treated as `pass`.
> - **Gate decision** — what Phase 2 does with this claim. The reason tag in parentheses points to which sub-audit drove a WARN/FAIL.

## Variant integrity (Phase 9)
[filled by Phase 9 — only for claims admitted by Phase 2]
```

For every Cx whose combined verdict is `fail`, also pre-write `verify/<claim_dir>/ROBUSTNESS.md` with `verdict: INCONCLUSIVE` and a sub-audit-specific `inconclusive_reason`:

- exp = fail, mech ≠ fail → `inconclusive_reason: main-experiment integrity broken — see verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md`
- mech = fail, exp ≠ fail → `inconclusive_reason: main-experiment mechanism rigor broken — see verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.md`
- both fail → `inconclusive_reason: main-experiment integrity broken (experiment + mechanism) — see verify/<claim_dir>/main_experiment_audit/{EXPERIMENT,MECHANISM}_AUDIT.md`

This keeps Phase 11's inputs consistent and tells the iteration loop exactly which sub-audit to fix.

If **all** claims fail, additionally emit a `[skipped — all main-experiment audits FAIL]` placeholder line under `## Variant integrity (Phase 9)` so the orchestrator's resume check (in `auto/SKILL.md`) sees a non-empty variant section and doesn't wrongly re-execute Phase 2.

#### 4. Audit-only short-circuit (when `SWAP_VARIANTS = false`)

Check `SWAP_VARIANTS` **before** the Stage 1 exit gate. When `false`:

1. For each target claim Cx, pre-write `verify/<claim_dir>/ROBUSTNESS.md` (per Phase 10's audit-only shape — see Phase 10 below) with the appropriate verdict:
   - Cx's Phase 2 combined verdict is `pass` or `warn` → `verdict: INTEGRITY_ONLY`, `stage2_skip_reason: swap_variants_false`
   - Cx's Phase 2 combined verdict is `fail` → `verdict: INCONCLUSIVE` (identical to the full-pipeline stub written in step 3 above)

2. Overwrite `verify/INTEGRITY_AUDIT.md`'s `## Variant integrity (Phase 9)` section with the sentinel `[skipped — SWAP_VARIANTS=false]`. This is **distinct** from `[skipped — all main-experiment audits FAIL]`; the orchestrator's resume check (`auto/SKILL.md`) must treat both as legitimate "Phase 9 did not run" markers. Update the top-level `Overall` line to reflect only the main-experiment section.

3. Log per claim:
   ```
   [audit-only] claim=<Cx> main_experiment_integrity=<pass|warn|fail> verdict=<INTEGRITY_ONLY|INCONCLUSIVE> stage2_skip_reason=<swap_variants_false|-> swap_variants_run=false
   ```

4. Jump to Phase 11 (`Write VERIFY_REPORT and Handoff`) with **all** target claims — including `pass`/`warn` claims that would normally advance to Stages 2–3. Phases 3–10 are entirely skipped: alternative-picking, variant implementation / review / deploy, per-variant judgment, Phase 9 variant integrity audit, and Phase 10's robustness arithmetic all no-op. `ROBUSTNESS.md` for every claim is already on disk from step 1 above, so Phase 11 renders directly from it.

5. Do **not** honor `STOP_AFTER_STAGE == 1` after step 4 — Phase 11 must still run so an audit-only `VERIFY_REPORT.md` lands on disk. `STOP_AFTER_STAGE == 1` is a human-in-the-loop halt for inspection *without* a final report; `SWAP_VARIANTS == false` is a policy decision that Stage 1 IS the final deliverable. If a user genuinely wants both (audit and then halt before the report), they can pass both flags and this step's Phase-11 jump still runs — the audit-only report is cheap to produce and safer for downstream tooling than an empty report slot.

#### Stage 1 exit gate

If `SWAP_VARIANTS == false`, this exit gate is unreachable (step 4 above already jumped to Phase 11). Otherwise, if `STOP_AFTER_STAGE == 1`, halt here. Print:

```
🛑 Stage 1 complete — halted by STOP_AFTER_STAGE=1.

Main-experiment integrity verdicts (per-claim, Exp / Mech → Combined):
- C1: PASS / PASS → PASS   → verify/C1_xxx/main_experiment_audit/
- C2: PASS / WARN → WARN   → verify/C2_yyy/main_experiment_audit/   (mechanism rigor warn)
- C3: FAIL / N/A  → FAIL   → verify/C3_zzz/main_experiment_audit/   (pre-marked INCONCLUSIVE — experiment broken)
- C4: PASS / FAIL → FAIL   → verify/C4_www/main_experiment_audit/   (pre-marked INCONCLUSIVE — mechanism broken)

Inspect each main_experiment_audit/ folder (contains EXPERIMENT_AUDIT.{md,json} + MECHANISM_AUDIT.{md,json}).
To continue with Stages 2–3:
  /auto-verify <same-args> — stop-after-stage: none, resume: true
(RESUME=true makes Phase 2 skip the already-completed audits.)
```

Do not write `VERIFY_REPORT.md` at this point — it is Phase 11's product and requires Stages 2–3 outputs to be meaningful.

### Phase 3: Pick Alternatives per Claim

**Stages 2–3 entry — read Stage 1 output first.** Phase 3 is the re-entry point after the Stage 1 gate, including the resume case where an earlier `STOP_AFTER_STAGE=1` run produced Stage 1 artifacts and a new invocation is now continuing. Always rebuild the admitted-claim list from `verify/INTEGRITY_AUDIT.md` on disk — do not rely on in-memory state from Phase 2, because Phase 2 may not have run in this invocation.

**Skip entirely when `SWAP_VARIANTS == false`.** Phase 2 step 4 already jumped to Phase 11 with per-claim verdicts written. On a resume from a prior audit-only run, Phase 3 branches on the *current* invocation's `SWAP_VARIANTS`:

- `swap-variants: true, resume: true` (upgrade path) → Phase 3 rebuilds ADMITTED from Phase 2's per-claim table normally; Stages 2–3 execute for the first time.
- `SWAP_VARIANTS=false` still → Phase 3 is a no-op. Log `[verify] SWAP_VARIANTS=false — Phases 3–10 skipped; audit-only ROBUSTNESS.md written by Phase 2 step 4.`

#### Step 0: Read Stage 1 output and route by per-claim main-experiment verdict

1. **Read** `verify/INTEGRITY_AUDIT.md`. If it does not exist or contains no per-claim "Main-experiment integrity (Phase 2, per-claim)" table, abort with `[verify] Stage 1 output missing at verify/INTEGRITY_AUDIT.md — re-run from Phase 2 (or invoke /auto-verify without — stop-after-stage)`. Stages 2–3 cannot start without the Stage 1 verdicts.

2. **Bucket the target claims** by parsing the per-claim verdict column (each row is one target Cx):

   | Phase 2 verdict | Bucket    | Action in Phases 3–10                                                        | Final state set by   |
   |-----------------|-----------|------------------------------------------------------------------------------|----------------------|
   | `PASS`          | ADMITTED  | continue into Phase 3 → 10                                                   | Phase 10             |
   | `WARN`          | ADMITTED  | continue into Phase 3 → 10 (variant findings inherit main-experiment warn caveat)   | Phase 10             |
   | `FAIL`          | REJECTED  | **skip Phases 3–10 entirely for this Cx** — already INCONCLUSIVE             | already set by Phase 2 |
   | anything else   | —         | abort with `[verify] unexpected main-experiment verdict for <Cx>: <value> — expected PASS/WARN/FAIL` | —                    |

3. **Safety net for REJECTED claims.** For each FAIL claim, confirm `verify/<claim_dir>/ROBUSTNESS.md` exists with `verdict: INCONCLUSIVE` and a sub-audit-specific `inconclusive_reason` pointing to whichever of `EXPERIMENT_AUDIT.md` / `MECHANISM_AUDIT.md` drove the FAIL (Phase 2 step 3 pre-writes this stub based on which sub-audit returned `fail`). If the file is missing — e.g., Phase 2 crashed mid-write before the stub was emitted, or this is a resume from a hand-edited tree — re-read both audit JSONs, recompute the combined verdict + reason, and write the stub here. Phase 11 reads `ROBUSTNESS.md` directly, so every claim must have one on disk before Phases 3–10 finish.

4. **Short-circuit when ADMITTED is empty.** If every target claim came out FAIL at Phase 2, print and jump straight to Phase 11:

   ```
   [verify] Stage 1 admitted 0/<N> claims — all FAIL → INCONCLUSIVE.
   Phases 3–10 skipped (variants would just compute robustness around a broken anchor).
   → Phase 11 (final report) only.
   ```

5. **Log the filtered list:**

   ```
   [verify] Stage 1 verdicts → admitted: [C1 (PASS), C2 (WARN)]; rejected → INCONCLUSIVE: [C3 (FAIL)]
   ```

6. **Pick the Stage-2 claim set (top-K by importance).** Compute `K = min(MAX_VERIFY_CLAIMS, |ADMITTED|)`. If `RESUME=true` and `verify/STAGE2_PICK.json` exists non-empty with a `picked_claims` field, load it and skip to step 8. Otherwise, decide the pick:

   - **Single-claim mode** (Phase 1 resolved `TARGET_CLAIMS` to one specific claim id): if that claim is in ADMITTED, `PICKED = [Cx]`; otherwise `PICKED = []` (the claim is already INCONCLUSIVE).
   - **`K == |ADMITTED|`**: no selection needed — `PICKED = ADMITTED` (all admitted claims proceed).
   - **`K < |ADMITTED|`**: pick K claims by **importance judgment**. Read each ADMITTED claim's statement (from the per-claim records built in Phase 1) alongside any upstream context that is present: `refine-logs/EXPERIMENT_PLAN.md`'s `## Rationale` / `## Motivation` / `## Contributions` narrative sections (if any), `idea-stage/IDEA_REPORT.md`, `refine-logs/FINAL_PROPOSAL.md`, and the orchestrator's Claim Ledger (`refine-logs/CLAIMS_LEDGER.md`) if it exists with per-claim `centrality` / `priority` fields. Judge which K claims are the most scientifically central to the research direction. **Row order in `EXPERIMENT_PLAN.md` is NOT a priority signal — do not use it as a proxy.** For each picked claim, write a one-sentence rationale.

7. **Persist the pick** to `verify/STAGE2_PICK.json`:

   ```json
   {
     "picked_claims": ["Cx", ...],
     "picked_rationale": {"Cx": "one-sentence why", ...},
     "admitted_pool": ["Cx", "Cy", "Cz"],
     "stage2_deferred": ["Cy", "Cz"],
     "rejected_pool": ["Cw"],
     "cap_source": "MAX_VERIFY_CLAIMS=<value>"
   }
   ```

8. **Pre-write `INTEGRITY_ONLY` stubs for un-picked ADMITTED claims.** For each Cx in `stage2_deferred = ADMITTED \ PICKED`, write `verify/<claim_dir>/ROBUSTNESS.md` with `verdict: INTEGRITY_ONLY` and `stage2_skip_reason: max_verify_claims_cap`. Phase 11 will render these from disk; Phases 4–10 skip them.

9. **Log the pick and continue:**

   ```
   [stage2-pick] admitted=<N_admitted>, cap=<MAX_VERIFY_CLAIMS>, picked=<Cx,...> (rationale: ...); stage2-deferred=<Cy,...>; rejected=<Cw,...>
   [verify] Phases 4–10 will process: <picked list>
   ```

   From this point on, "for each target claim" in Phases 4–10 means **for each claim in PICKED**. REJECTED and un-picked ADMITTED claims are not touched again until Phase 11 reads their pre-written `ROBUSTNESS.md`.

#### Step 1: Pick alternatives for each picked claim

For each claim in PICKED, follow the protocol in `./pick-alternatives/SKILL.md` (a sub-skill of this skill, not a top-level slash command). Read its `SKILL.md` and execute its steps inline, passing the claim id, claim statement, and the resolved `DIMENSIONS` from Phase 1 as inputs.

**What the sub-skill does** (full protocol in `./pick-alternatives/SKILL.md`):
- Reads `idea-stage/IDEA_REPORT.md` and any prior `research-lit` outputs for candidate methods/datasets/models
- When the claim is about **LLM internal mechanisms** or **LLM interpretability**, and `method` is in `DIMENSIONS`, also reads `skills/mechanism-skills/SKILL.md` and the **main experiment's family sub-skill** to surface **within-family** method-swap candidates (e.g., swap `probing/residual-stream-states` for `probing/sae-feature-activation-state`; `causal-attribution/ablation` for `causal-attribution/patching` or `causal-attribution/attribution-patching`; `vocabulary-projection/residual-stream-state` for `vocabulary-projection/attention-head-output`). **Hard constraint: the method swap MUST stay within the same mechanism family.** Cross-family candidates (e.g., probing → causal attribution) are filtered out — they answer a different question (does the claim survive a totally different mechanism?) and belong in a separate sweep, not this verify pass.
- If research coverage is thin for any of the three dimensions (fewer than 2 credible candidates), calls `/research-lit "alternative [method|dataset|model] for claim: [statement]" — extra: semantic-scholar` to fill the gap
- Asks the external LLM reviewer to rank candidates by "strongest independent test of the claim" (not "closest to the main experiment")
- Returns a structured variant list: exactly one swap per axis in `DIMENSIONS` (e.g., DIMENSIONS=method,dataset,model → one method swap + one dataset swap + one model swap; DIMENSIONS=method → method swap only)

Expected return per claim (written to `verify/<claim_dir>/PLAN.md`):

```markdown
## Claim [C1]: [statement]

### Main experiment (from /auto-experiment)
- Method: [M0], Dataset: [D0], Model: [Mdl0] → [metric = value]

### Variants
| # | Dimension | Swap | Replaces | Justification | Source |
|---|-----------|------|----------|---------------|--------|
| 1 | method | [M1] | [M0] | [why this tests the claim] | [paper/idea ref] |
| 2 | dataset | [D1] | [D0] | [different distribution, same construct] | [paper/idea ref] |
| 3 | model | [Mdl1] | [Mdl0] | [different scale/family] | [paper/idea ref] |

### Success Criterion (per variant)
Claim is supported if [metric] on variant is within [delta] of the main experiment, in the same direction.
```

### Phase 4: Reviewer Critique of the Verify Plan

Before writing any code, send the aggregated plan to the external reviewer for one critique pass. This catches "too easy" swaps (e.g., same dataset family, same model family) that would let the claim pass trivially.

```
mcp__llm-chat__chat:
  prompt: |
    You are a rigorous ML reviewer auditing a claim-verification plan.
    Our goal is to stress-test the following claim(s) by swapping method, dataset, and model —
    one swap per dimension, independently — and checking whether each variant reaches the
    SAME conclusion as the main experiment on the frozen claim. (Both "all reach supported" and
    "all reach not-supported" pass; only inconsistency fails.)

    Claims under verification:
    [paste each target claim's statement, main-experiment verdict (supported | not-supported), main-experiment setup, and chosen variants]

    For each variant, answer:
    1. Is this swap a GENUINE test of the claim, or a trivial re-run with cosmetic changes?
    2. Does the swap control the right confound? (e.g., dataset swap should change distribution,
       not just sample count)
    3. Are there obvious stronger swaps we missed that the research evidence supports?
    4. If the variant's conclusion diverges from the main experiment's on this swap, what would that
       tell us — and is the divergence informative?

    Then rank the full variant list by "how much a reviewer would trust the conclusion if it stayed consistent with the main experiment across this swap."

    Flag any variant as REJECT if it is a trivial or biased test. Propose a replacement.
    Be strict. Do not accept swaps that were picked for convenience.
```

Apply the reviewer's feedback:
- Replace rejected variants with the reviewer's proposals
- Re-rank the run order by the reviewer's trust ordering
- If the reviewer rejects ≥ 50% of variants, loop back to Phase 3 for that claim (max 2 rounds)
- If llm-chat MCP is unavailable, log `[pending external review]` on the plan and continue (graceful degradation)

Save the updated plan to `verify/<claim_dir>/PLAN.md`.

### Phase 5: Implement Variants

For each variant (ordered by reviewer trust), produce a runnable artifact with **minimum diff** from the main experiment.

1. **Start from the main experiment script/config** used in `experiment`. Locate it via `EXPERIMENT_TRACKER.md`'s reproduce command.
2. **Apply only the swap**:
   - Method swap → new module or loss; keep data pipeline and model backbone frozen. For mechanism/interpretability claims, take the swap template from the chosen within-family submethod's `skills/mechanism-skills/<family>/<submethod>/scripts/` and `references/` directories — adapt, do not copy verbatim.
   - Dataset swap → new dataset loader + splits; keep method and model frozen
   - Model swap → new checkpoint / architecture flag; keep method and dataset frozen
3. **Hold all other hyperparameters fixed.** If a hyperparameter is incompatible (e.g., batch size on a larger model), document the adjustment and ensure the main experiment is re-run with the same adjustment so the comparison stays fair.
4. **Fix seeds.** Use the main experiment's seed list (`seeds: [42]` by default; `[42, 43, 44]` if `EXPERIMENT_PLAN.md` specifies multi-seed).
5. Save per-variant artifacts under `verify/<claim_dir>/variants/<variant-tag>/`:
   - `config.yaml` — full config, diffed from the main experiment at top
   - `run.sh` — one-line reproduce command
   - `DIFF.md` — what changed vs the main experiment, one paragraph

### Phase 6: Cross-Model Code Review (when CODE_REVIEW = true)

**Skip if `CODE_REVIEW` is `false`.**

Before deploying, review each variant's diff:

```
mcp__llm-chat__chat:
  prompt: |
    Review this variant's code for correctness and fairness vs the main experiment.

    ## Claim being tested:
    [statement]

    ## Main-experiment setup:
    [method/dataset/model + metric]

    ## Variant diff (what changed):
    [paste DIFF.md + the actual code diff]

    Check:
    1. Does the variant implement the intended swap, and ONLY that swap?
    2. Are any hyperparameters silently different from the main experiment? List each and justify.
    3. Does evaluation still use the dataset's actual ground truth labels (not another model's output)?
    4. Is the metric computed the same way as the main experiment?
    5. If a hyperparameter MUST change (e.g., batch size for a larger model), is the main experiment
       also adjusted so the comparison is apples-to-apples?
    6. Any leakage risk introduced by the swap (e.g., model trained on the swapped dataset)?

    For each issue: CRITICAL / MAJOR / MINOR and the exact fix.
```

On results:
- No CRITICAL → proceed
- CRITICAL found → fix and re-submit (max 2 rounds)
- llm-chat MCP unavailable → skip silently, proceed

### Phase 7: Sanity Check, then Deploy

**GPU pinning.** If `GPU_ID` is not `auto`, pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional arg to every variant's `/run-experiment` invocation (sanity runs, the full sweep, and any re-runs triggered by reviewer feedback); the run-experiment skill exports it internally. Do **not** prepend it as a shell prefix. Record the effective `CUDA_VISIBLE_DEVICES` in each variant's `run.sh` so reproductions land on the same devices.

**If `SANITY_FIRST = true`**, run the cheapest variant on its smallest split first:

```
/run-experiment CUDA_VISIBLE_DEVICES=<GPU_ID> [cheapest-variant sanity command]
```

Verify training loop runs, metrics save, GPU memory stays in bounds. If sanity fails, follow the auto-debug protocol from `experiment/SKILL.md` Phase 3 (max 3 attempts; invoke `/codex:rescue` if available).

Then deploy the full variant sweep. **Route by total variant count** (same rule as `/auto-experiment` Phase 4.0):

- **`total_variants ≤ 5`** (small passes — e.g. 1 claim × 3 axes = 3, or 2 claims × 2 axes = 4): dispatch directly via `/run-experiment`, one call per variant, up to `MAX_PARALLEL_RUNS` concurrent. When `GPU_ID` lists multiple devices and `MAX_PARALLEL_RUNS > 1`, partition the devices across concurrent variants (e.g., `GPU_ID=4,5,6,7` with 2 parallel runs → variant A on `4,5`, variant B on `6,7`); do not co-schedule two variants on the same device unless memory measurements confirm it fits.

  ```
  /run-experiment CUDA_VISIBLE_DEVICES=<GPU_ID> [variant commands]
  ```

  Use `/monitor-experiment` to track progress.

- **`total_variants ≥ 6`** (large verify pass — e.g., an explicit `— max-verify-claims: 3, dimensions: method,dataset,model` combo yields 3 × 3 = 9 variants, and `— max-verify-claims: 5, dimensions: method,dataset,model` yields 15; the new defaults `MAX_VERIFY_CLAIMS=1 × DIMENSIONS=model = 1` do NOT reach this branch): dispatch via `/experiment-queue` instead, with one phase per claim (so OOM retry, stale-screen cleanup, and wave-transition GPU gate are active across the variant grid). Build a queue manifest with each claim's variants as a phase (no `depends_on:` between claims — they are independent), `max_parallel:` from `MAX_PARALLEL_RUNS`, `gpus:` from `GPU_ID`, `oom_retry: {delay: 120, max_attempts: 3}`. After the batch completes, invoke `/monitor-experiment` per variant to finalize `runs/<variant-id>/cost.json`.

The routing decision and threshold mirror `/auto-experiment` Phase 4.0; verify uses a slightly lower threshold (6 instead of 10) because verify variants tend to share GPU memory profile within a claim (same method, different swap axis), making OOM cascades more likely than in experiment's milestone runs. The downstream Stage 3 logic (Phase 8 judgment → Phase 9 audit → Phase 10 aggregation) runs unchanged on top of either dispatch path.

**🚦 Checkpoint (deploy gate):** Skip entirely when `AUTO_PROCEED = true` OR `AUTO_DEPLOY = true` — proceed straight to deploy. Only when `AUTO_PROCEED = false` AND `AUTO_DEPLOY = false`, call `AskUserQuestion` and **block indefinitely** until the user answers (no timeout — waiting is the intended human-in-the-loop behavior):

```
🔧 Variants ready to deploy:

Claim C1: [1 variant, ~X GPU-hours]
Total: ~X GPU-hours on [N] GPUs

AskUserQuestion:
  question: "Variants are ready. Proceed with the deploy plan above?"
  header:   "Deploy plan"
  options:  [approve (recommended), narrow scope, abort]
```

On answer:
- `approve` → continue to the deploy step.
- `narrow scope` → re-prompt for which claims/variants to keep (free-form), then re-open this gate with the trimmed plan.
- `abort` → halt verify, return a partial-completion summary to the orchestrator.

#### Stage 2 exit gate

If `STOP_AFTER_STAGE == 2`, halt here after every dispatched variant has completed (run.log written, result.json non-empty). Variants are **not yet judged** — no `/result-to-claim` calls, no `consistent_with_main_experiment`, no robustness. Print:

```
🛑 Stage 2 complete — halted by STOP_AFTER_STAGE=2.

Variants deployed and completed for [N] picked claims. Raw artifacts at:
  verify/<claim_dir>/variants/*/result.json   (raw metrics)
  verify/<claim_dir>/variants/*/run.log       (run logs)

No LLM judgment, integrity audit, or robustness aggregation has been done yet.
This gate exists so you can eyeball raw variant numbers before letting Stage 3
interpret them. To continue with Stage 3:
  /auto-verify <same-args> — stop-after-stage: none, resume: true
```

Do not write `verdict.json`, `ROBUSTNESS.md`, `INTEGRITY_AUDIT.md`'s variant section, or `VERIFY_REPORT.md` at this point — they are Stage 3 products.

### Phase 8: Per-Variant Claim Judgment

After each variant completes, invoke `/result-to-claim` scoped to that variant **with its literal question** (no main-experiment-comparison framing — that step is computed locally, see below):

```
/result-to-claim "variant [claim-id]/[variant-tag] — frozen claim: [statement] — does this variant's evidence support the claim?"
```

`/result-to-claim` returns its standard literal `claim_supported: pass | fail` — i.e., "does the data support the claim?" — exactly as in `/auto-experiment` usage. Binary scheme: anything short of unambiguous support (partial / mixed / narrow coverage / wrong magnitude) is `fail`. No semantic overload, no main-experiment mixed into the LLM's reasoning.

**Then compute `consistent_with_main_experiment` deterministically** (no LLM call) by projecting `claim_supported` through `main_experiment_verdict`. There are two projection cases — one per possible main-experiment verdict:

```
consistent_with_main_experiment =
  if main_experiment_verdict == "supported":     claim_supported              # pass→pass, fail→fail
  if main_experiment_verdict == "not-supported": flip(claim_supported)        # pass→fail, fail→pass
```

`flip(pass) = fail`, `flip(fail) = pass`. This is the field that drives robustness: variant matches main experiment's conclusion ⇔ `consistent_with_main_experiment = pass`. Two patterns count as agreement:

- main experiment = supported, variant supports (`claim_supported = pass`) → `consistent = pass` ✅ (robustly positive)
- main experiment = not-supported, variant rejects (`claim_supported = fail`) → `consistent = pass` ✅ (robustly negative)

Disagreement in either direction → `consistent = fail` ❌ (lowers `robustness`).

Save each verdict to `verify/<claim_dir>/variants/<variant-tag>/verdict.json`:

```json
{
  "variant_tag": "method-swap-contrastive",
  "dimension": "method",
  "claim_id": "C1",
  "claim_statement": "[frozen from the main experiment]",
  "main_experiment_verdict": "supported | not-supported",
  "variant_metric": "metric = value",
  "main_experiment_metric": "metric = value",
  "delta": "+X% / -X%",
  "claim_supported": "pass | fail",
  "consistent_with_main_experiment": "pass | fail",
  "confidence": "high | medium | low",
  "reasoning": "..."
}
```

> **Field semantics** (both fields needed — do NOT collapse them):
> - `main_experiment_verdict` — main experiment's own conclusion on the frozen claim (`supported | not-supported`), read from `refine-logs/main-experiment-verdicts.json` (built once in Phase 1 step 2(b) from `EXPERIMENT_RESULTS.md`). Same value for every variant under the same Cx.
> - `claim_supported` — **literal**: does *this variant's* data support the claim? Returned by `/result-to-claim` as `pass | fail`, same semantics as anywhere else in the pipeline.
> - `consistent_with_main_experiment` — **derived**: variant's conclusion matches main experiment's conclusion (`pass | fail`). Deterministic function of `(claim_supported, main_experiment_verdict)`, computed and written exactly once here in Phase 8. This is what feeds `robustness` in Phase 10; no downstream phase recomputes or re-checks it.

> **Phase-8-written vs Phase-9-appended fields.** Phase 8 writes exactly the fields shown in the JSON above and stops. The `integrity_status` and `integrity_breakdown` fields are **appended later by Phase 9** after the variant-level integrity audit runs (see Phase 9 → "Map per-variant audit verdict"). On a fresh Phase 8 run those fields are absent; that is correct, not a bug.

### Phase 9: Per-Claim Variant Integrity Audit

Runs for each claim Cx in `PICKED` (i.e., admitted by Phase 2 AND selected by the Phase 3 step 0 Stage-2 pick). Skipped for any Cx whose Phase 2 combined verdict was `fail` (already INCONCLUSIVE) OR whose Phase 3 step 0 outcome was `INTEGRITY_ONLY` (variants never ran). If every target claim failed Phase 2, this phase is skipped entirely.

This is the variant-level half of integrity auditing (the main experiment half was handled in Phase 2 on `refine-logs/`). It catches the failure modes that the rest of the pipeline can't see — phantom results, fake GT, dead metric code, scope over-claim, AND mechanism failure modes such as un-tuned steering coefficients in the variants — *before* robustness is computed in Phase 10. The two halves are symmetric: same `/experiment-audit` + `/mechanism-audit` pair, same per-claim scoping via `— claim Cx`, output written into symmetric subdirs (`main_experiment_audit/` for Phase 2, `variant_audit/` for Phase 9).

#### Invocation

For each picked claim Cx, invoke both audits on Cx's variant directory, scoped to Cx:

```bash
mkdir -p "verify/<claim_dir>/variant_audit"
/experiment-audit "verify/<claim_dir>/variants/" — claim <Cx> — output-dir "verify/<claim_dir>/variant_audit"
/mechanism-audit  "verify/<claim_dir>/variants/" — claim <Cx> — output-dir "verify/<claim_dir>/variant_audit"
```

Produces (mirrors Phase 2's per-claim output):
- `verify/<claim_dir>/variant_audit/EXPERIMENT_AUDIT.md` — full A–F findings on Cx's variants
- `verify/<claim_dir>/variant_audit/EXPERIMENT_AUDIT.json` — `overall_verdict` is Cx's variant-level methodology-integrity verdict
- `verify/<claim_dir>/variant_audit/MECHANISM_AUDIT.md` — mechanism-rigor findings on Cx's variants (e.g., did each variant re-sweep α on the swapped substrate?)
- `verify/<claim_dir>/variant_audit/MECHANISM_AUDIT.json` — `overall_verdict` is Cx's variant-level mechanism-rigor verdict (may be `n/a`)

#### Map per-variant audit verdict into `integrity_status`

For each variant under Cx, derive a per-variant severity. The audit skills' contract is **claim-level** (`overall_verdict` is one value for all of `<Cx>`'s scope); a per-variant breakdown is an optional extension. Phase 9 supports both:

```
# Per-variant breakdown — if available in the audit JSON
if exp.checks.per_variant exists:
    per_variant_exp  = exp.checks.per_variant[<variant-tag>]   (PASS / WARN / FAIL)
else:
    # Fallback: every variant under Cx inherits the claim-level verdict
    per_variant_exp  = exp.overall_verdict

if mech.checks.per_variant exists:
    per_variant_mech = mech.checks.per_variant[<variant-tag>]  (PASS / WARN / FAIL / N/A)
else:
    per_variant_mech = mech.overall_verdict

integrity_status = max_severity(per_variant_exp, per_variant_mech)
                   # n/a contributes 0; fail > warn > pass > n/a
```

> **Per-variant contract note.** Neither audit skill emits `checks.per_variant` today — that field is reserved for a future extension where the reviewer is asked to break its verdict down by variant tag. Until then, the fallback applies: a single broken variant under Cx propagates the failure to every variant under Cx (conservative, never silently lets a broken variant through; possibly over-inclusive). Per-variant attribution will tighten this when the audit contract grows.

Write that single `integrity_status` field into the variant's `verdict.json`. Also write an `integrity_breakdown` companion field documenting the two sub-verdicts (`{experiment: "...", mechanism: "..."}`) so iteration knows which sub-audit to fix.

- `pass` → variant is trusted; counts in both numerator and denominator of `robustness` in Phase 10
- `warn` → variant counts normally but is tagged `[INTEGRITY: WARN]` in `ROBUSTNESS.md` / `VERIFY_REPORT.md`, with the offending sub-audit shown in parentheses (`[INTEGRITY: WARN — mechanism]`)
- `fail` → variant is **excluded from BOTH numerator AND denominator** in Phase 10, tagged `[INTEGRITY: FAIL — <experiment|mechanism|both>]`, with the audit's specific reason logged. The symmetric exclusion is deliberate: a failed-integrity variant means "we don't know what this variant would have said", not "this variant disagrees". Counting it as 0 in the numerator while keeping it in the denominator would bias `robustness` toward FAIL, violating objective correctness — a broken variant must not push the verdict in any direction, only shrink the eligible set.

Log per variant (symmetric to Phase 2's `[main-experiment-audit]` block):

```
[variant-audit] claim=<Cx> variant=<tag> exp_verdict=<pass|warn|fail> mech_verdict=<pass|warn|fail|n/a> combined=<pass|warn|fail>
[variant-audit] claim=<Cx> variant=<tag> exp_source=verify/<claim_dir>/variant_audit/EXPERIMENT_AUDIT.json
[variant-audit] claim=<Cx> variant=<tag> mech_source=verify/<claim_dir>/variant_audit/MECHANISM_AUDIT.json
[variant-audit] claim=<Cx> variant=<tag> integrity_status=<pass|warn|fail> action=<include|include-with-warn|exclude>
```

#### Output: append `## Variant integrity (Phase 9)` to `verify/INTEGRITY_AUDIT.md`

Phase 2 already wrote the `## Main-experiment integrity` section. Phase 9 appends the variant section and updates the top-level `Overall` line:

```markdown
# Integrity Audit

**Overall**: [PASS | WARN | FAIL]    ← max severity across Phase 2 + Phase 9
**Main-experiment integrity (Phase 2)**: [PASS | WARN | FAIL]
**Variant integrity (Phase 9)**: [PASS | WARN | FAIL]    ← max severity across all per-variant combined outcomes

## Main-experiment integrity (Phase 2)
[unchanged — written by Phase 2]

## Variant integrity (Phase 9)

**Variants audited**: [N]  ([N_pass] pass, [N_warn] warn, [N_fail] fail)

### Per-claim audit verdicts

| Claim | Exp. audit (variants) | Mech. audit (variants) | Combined |
|-------|-----------------------|------------------------|----------|
| C1    | PASS                  | PASS                   | PASS     |
| C2    | WARN (1 variant)      | PASS                   | WARN     |
| C4    | 2 FAIL                | 1 FAIL                 | FAIL     |

### Findings (per variant)
- C1 / variant method-swap-X: [INTEGRITY: WARN — experiment] — scope language overclaim
- C2 / variant model-swap-Y: [INTEGRITY: FAIL — experiment] — phantom result (no run.log, result.json mtime predates run.sh)
- C4 / variant dataset-swap-W: [INTEGRITY: FAIL — mechanism] — variant re-uses the main experiment's α=3 without re-sweeping on the swapped dataset; capability metric crashed at locked α; variant excluded from numerator AND denominator
- C4 / variant method-swap-Z: [INTEGRITY: FAIL — both] — fake GT AND no coefficient sweep; excluded
```

Skip this file when `COMPACT = true`; the same content lives in `VERIFY_REPORT.md`'s integrity section.

### Phase 10: Compute per-Claim Robustness Score + Final State

For each picked claim Cx, fold its post-audit variant verdicts into a single robustness label. Phase 9 has already settled every variant's `integrity_status`, and Phase 8 has already settled every variant's `consistent_with_main_experiment`, so Phase 10 is a pure-arithmetic single pass over those fields. Un-picked ADMITTED claims already had `ROBUSTNESS.md` written in Phase 3 step 0 with `verdict: INTEGRITY_ONLY`; Phase 10 does not touch them.

#### Compute robustness on the post-audit eligible set

Each variant's `consistent_with_main_experiment` (written by Phase 8 from `claim_supported × main_experiment_verdict`) contributes:

```
N_eligible = count(variants where integrity_status ∈ {pass, warn})
#pass      = count(variants where consistent_with_main_experiment == "pass" AND integrity_status ∈ {pass, warn})
robustness = #pass / N_eligible
             (integrity-FAIL variants excluded from BOTH numerator and denominator)
```

#### Assign final state

Under `SWAP_VARIANTS = false` this phase is unreachable — Phase 2 step 4 already jumped straight to Phase 11 with `INTEGRITY_ONLY` / `INCONCLUSIVE` verdicts pre-written. The arithmetic below runs only under the full-pipeline path. Branch on `N_eligible`:

- `N_eligible < MIN_VARIANTS_FOR_VERDICT` (default 1 → triggers only when `N_eligible = 0`, i.e. every variant failed integrity) → **ZERO_ELIGIBLE_VARIANTS** (distinct from INCONCLUSIVE, which is reserved for Phase 2 main-experiment-integrity failures) with `zero_eligible_reason: <N_eligible>/<N_run> survived — breakdown: <N_exp_fail> experiment-FAIL, <N_mech_fail> mechanism-FAIL, <N_both_fail> both-FAIL` (counts derived by inspecting each failed variant's `integrity_breakdown` field — a variant is counted in `<N_both_fail>` iff BOTH `experiment` and `mechanism` are `fail`, otherwise it falls into whichever sub-audit was `fail`). No PASS/FAIL on zero signal. Iteration's job here is to fix the variant scripts (not the main experiment) and re-invoke `/auto-verify <claim-id> — resume: true`; the main experiment already passed Phase 2.
- `N_eligible ≥ MIN_VARIANTS_FOR_VERDICT`:
  - `robustness ≥ ROBUSTNESS_THRESHOLD` → **PASS** (main experiment's verdict is robust across swaps).
  - `robustness <  ROBUSTNESS_THRESHOLD` → **FAIL** (main experiment's verdict is fragile under swaps; send to iteration).

No cross-claim aggregation — each claim's state is reported independently.

**Important — PASS does NOT mean "claim is true", FAIL does NOT mean "claim is false".**

| State | Meaning | Example |
|---|---|---|
| **PASS** | Main experiment's verdict is *robust* — variants reach the same conclusion. Direction = whatever the main experiment said. | (a) main experiment supported + variants supported → robustly positive; (b) main experiment not-supported + variants not-supported → **robustly negative** (equally valid) |
| **FAIL** | Main experiment's verdict is *fragile* — variants disagree. Sent to iteration. | main experiment supported + variants split → support flips under swaps |
| **INCONCLUSIVE** | Phase 2 combined verdict failed — main-experiment evaluation methodology AND/OR mechanism rigor is broken; variants were never run because computing robustness around a broken anchor would be meaningless. Iteration instruction: **fix the failing main-experiment sub-audit (experiment / mechanism / both); do not change the claim.** Semantics are identical whether `SWAP_VARIANTS=true` or `false`. | main-experiment combined-FAIL at Phase 2 |
| **ZERO_ELIGIBLE_VARIANTS** | Variants ran but every one failed Phase 9 combined integrity, so `N_eligible = 0`. The main experiment is fine (Phase 2 was PASS/WARN); the problem is purely on the variant side. Iteration instruction: **fix the variant scripts that failed integrity and re-invoke `/auto-verify <claim-id> — resume: true`; do not touch the main experiment.** Unreachable under `SWAP_VARIANTS=false` (Phase 9 never runs). | every variant FAILed at Phase 9 (combined experiment OR mechanism) |
| **INTEGRITY_ONLY** | `SWAP_VARIANTS=false` AND Phase 2 combined verdict is `pass` or `warn`. Main experiment's evaluation methodology (and mechanism rigor, if any) is validated, but the swap stress test was intentionally skipped by policy. No robustness verdict; no PASS/FAIL. Iteration instruction: **no back-edge action** — record in Open Items with the suggestion to upgrade to full verify (`/auto-verify — swap-variants: true, resume: true`) when GPU budget allows. Never appears under the default `SWAP_VARIANTS=true`. | Stage 1 audit passed, Stage 2/3 skipped by policy flag |

#### Per-claim output: `verify/<claim_dir>/ROBUSTNESS.md`

Write the final per-claim summary (skip if `COMPACT = true`, **except** for the audit-only shape below which is always written — see note at the end of this subsection):

```markdown
## C1: robustness = [0.67] (threshold = [0.5], eligible = [3/3])  →  [✅ PASS | ❌ FAIL | 🟡 INCONCLUSIVE | 🟠 ZERO_ELIGIBLE_VARIANTS]

- swap_variants_run: true
- Main-experiment verdict on C1: [supported | not-supported]
- Variant counts (over `consistent_with_main_experiment`): [N_pass] pass, [N_fail] fail
  (of [N_eligible] eligible; [N_excluded] excluded for integrity reasons)
- Method dimension: matches the main experiment (consistent=pass, claim_supported=pass, delta +1.2%)
- Dataset dimension: matches the main experiment (consistent=pass, claim_supported=pass, delta -2.1%)
- Model dimension: diverges from the main experiment (consistent=fail, claim_supported=fail while main experiment=supported, delta -8.4% — conclusion flips under model-scale change)

Interpretation: [one paragraph — which dimension lowers `robustness` the most (or which variants are excluded and why), what the next iteration should do]
```

When state = INCONCLUSIVE (Phase 2 main-experiment-integrity failure), also write an `inconclusive_reason` field with the failing main-experiment sub-audit attributed:
- `main-experiment integrity broken — see verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.md`
- `main-experiment mechanism rigor broken — see verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.md`
- `main-experiment integrity broken (experiment + mechanism) — see verify/<claim_dir>/main_experiment_audit/{EXPERIMENT,MECHANISM}_AUDIT.md`

When state = ZERO_ELIGIBLE_VARIANTS (Phase 9 variants all integrity-FAIL), instead write a `zero_eligible_reason` field with the variant-side breakdown:
- `0/<N_run> variants survived — breakdown: <N_exp_fail> experiment-FAIL, <N_mech_fail> mechanism-FAIL, <N_both_fail> both-FAIL — see verify/<claim_dir>/variant_audit/{EXPERIMENT,MECHANISM}_AUDIT.md`

`inconclusive_reason` and `zero_eligible_reason` are disjoint by construction — never write both on the same claim. The two states route iteration to different surfaces (main-experiment scripts vs. variant scripts).

**Audit-only shape** (INTEGRITY_ONLY — written by Phase 2 step 4 for `SWAP_VARIANTS = false`, OR by Phase 3 step 0 for un-picked ADMITTED claims under `MAX_VERIFY_CLAIMS` cap). **Always emitted regardless of `COMPACT`**, because downstream `/auto-iteration-loop` reads its prose fields to route and there is no VERIFY_REPORT-side backup for the audit-only case.

```markdown
## C1: audit-only  (main-experiment integrity = [PASS|WARN], swap stress test skipped)  →  ⚪ INTEGRITY_ONLY

- stage2_skip_reason: [swap_variants_false | max_verify_claims_cap]
- swap_variants_run: false
- Main-experiment verdict on C1: [supported | not-supported]
- Main-experiment integrity: [pass | warn]
- warn_source: [experiment | mechanism | experiment+mechanism | null]   # null iff main_experiment_integrity == pass
- Variants: none  (Stage 2 skipped — see stage2_skip_reason)
- robustness: null
- n_eligible: 0
- n_pass: 0

Interpretation: Main experiment methodology (evaluation and, when applicable, mechanism intervention) was audited and found trustworthy at Phase 2. No swap stress test was attempted this pass — the main experiment's own verdict on C1 stands as-is, with the caveat that it has not been shown robust across method / dataset / model swaps. To upgrade to full verification without re-auditing:
- `stage2_skip_reason: swap_variants_false` → `/auto-verify C1 — swap-variants: true, resume: true`
- `stage2_skip_reason: max_verify_claims_cap` → `/auto-verify C1 — resume: true` (single-claim mode; Phase 2 audit is reused via RESUME)
```

For a Phase-2-combined-FAIL claim under audit-only mode (verdict = INCONCLUSIVE), the shape is exactly the standard INCONCLUSIVE shape above with **one extra prose field** `swap_variants_run: false` inserted between the header and `inconclusive_reason`. This flags to iteration that "this INCONCLUSIVE was detected under audit-only, not because full verify tried and failed" — the repair path itself is unchanged (fix the main experiment).

### Phase 11: Write VERIFY_REPORT and Handoff

Aggregate across claims:

```markdown
# Verification Report

**Date**: [today]
**Swap variants**: [true | false — audit-only pass (Stage 1 only; variant stress test skipped by policy)]
**Dimensions tested**: [DIMENSIONS list]  (variants/claim = len(DIMENSIONS); reported as `— (skipped)` when `swap_variants: false`)
**Threshold**: robustness ≥ [threshold], min eligible variants = [MIN_VARIANTS_FOR_VERDICT]
**Main-experiment integrity (Phase 2)**: per-claim combined verdict — see Summary table column; per-sub-audit breakdown in `INTEGRITY_AUDIT.md`.

## Summary

| Claim | Statement (short) | Main-experiment verdict | Main-experiment integrity (Phase 2, combined) | Variant integrity (Phase 9, combined) | Eligible variants (post-audit) | Robustness | State | Notes |
|-------|-------------------|------------------|----------------------------------------|---------------------------------------|--------------------------------|------------|-------|-------|
| C1 | [short] | supported     | PASS (exp PASS / mech PASS)  | clean                              | 3/3 | 0.67 | ✅ PASS | robustly positive — model-scale dimension diverges (1 of 3 fails) |
| C2 | [short] | supported     | WARN (exp PASS / mech WARN)  | clean                              | 3/3 | 0.33 | ❌ FAIL `[MAIN-EXPERIMENT INTEGRITY: WARN — mechanism]` | diverges on dataset and model; only method swap matches the main experiment |
| C3 | [short] | not-supported | WARN (exp WARN / mech N/A)   | clean                              | 3/3 | 1.00 | ✅ PASS `[MAIN-EXPERIMENT INTEGRITY: WARN — experiment]` | robustly negative |
| C4 | [short] | supported     | PASS (exp PASS / mech PASS)  | 2 FAIL (1 mechanism, 1 experiment) | 1/3 | 1.00 | ✅ PASS | only 1 variant survived integrity — rerun the 2 failed for confirmation |
| C5 | [short] | —             | FAIL (exp FAIL / mech N/A)   | —                                  | —   | —    | 🟡 INCONCLUSIVE | main-experiment integrity broken (Phase 2) — fix evaluation method |
| C6 | [short] | —             | FAIL (exp PASS / mech FAIL)  | —                                  | —   | —    | 🟡 INCONCLUSIVE | main-experiment mechanism rigor broken (Phase 2) — sweep steering coefficient |
| C7 | [short] | —             | FAIL (exp FAIL / mech FAIL)  | —                                  | —   | —    | 🟡 INCONCLUSIVE | main-experiment integrity broken (experiment + mechanism) (Phase 2) — fix both before re-running |
| C8 | [short] | supported     | PASS (exp PASS / mech PASS)  | 3 FAIL (2 experiment, 1 mechanism) | 0/3 | —    | 🟠 ZERO_ELIGIBLE_VARIANTS | every variant failed Phase 9 integrity — fix variant scripts and re-verify (the main experiment is fine) |
| C9 | [short] | supported     | PASS (exp PASS / mech PASS)  | skipped (SWAP_VARIANTS=false)      | —   | —    | ⚪ INTEGRITY_ONLY (skip=swap_variants_false) | main-experiment integrity validated; swap stress test not run this pass — upgrade with `— swap-variants: true, resume: true` |
| C10 | [short] | not-supported | WARN (exp PASS / mech WARN) | skipped (SWAP_VARIANTS=false)      | —   | —    | ⚪ INTEGRITY_ONLY (skip=swap_variants_false) `[MAIN-EXPERIMENT INTEGRITY: WARN — mechanism]` | main-experiment mechanism rigor has soft issue; swap stress test not run |
| C11 | [short] | supported     | PASS (exp PASS / mech PASS)  | skipped (MAX_VERIFY_CLAIMS cap)    | —   | —    | ⚪ INTEGRITY_ONLY (skip=max_verify_claims_cap) | admitted by Phase 2 but not the top-K picked by importance — run `/auto-verify C11 — resume: true` to swap-test |

> **Column glossary**:
> - **Main-experiment verdict** — main experiment's own conclusion on the claim (`supported` / `not-supported`), read from `refine-logs/main-experiment-verdicts.json`. `—` when the main-experiment audit failed before this could matter.
> - **Main-experiment integrity (Phase 2, combined)** — `max_severity(/experiment-audit, /mechanism-audit)` run on `refine-logs/` scoped to this claim, with the two sub-verdicts shown in parentheses. `PASS` / `WARN` admit the claim into Phases 3–10; `FAIL` short-circuits to INCONCLUSIVE (the parenthetical sub-verdict tells iteration *which* audit to fix — methodology or mechanism). `mech N/A` means the claim's experiment uses no mechanism intervention; the severity ordering `fail > warn > pass > n/a` then leaves combined = exp-side verdict.
> - **Variant integrity (Phase 9, combined)** — same `max_severity` rule on the per-claim variants. Reported as `clean` (every variant combined-PASS), `N WARN` (N kept but flagged, with which sub-audit), or `N FAIL (... breakdown ...)` (N demoted to `integrity_status=fail` and **excluded from BOTH numerator AND denominator** of robustness). `—` when Phase 9 didn't run for this claim (main-experiment FAIL → INCONCLUSIVE).
> - **Eligible variants (post-audit)** — `N_eligible / N_run` — how many of the dispatched variants survived Phase 9. Only the eligible set feeds the robustness formula; integrity-FAIL variants are dropped symmetrically (not counted as `fail`, just unknown). `—` when no variants were ever dispatched (main-experiment FAIL → INCONCLUSIVE). `0/<N_run>` (with robustness `—`) means every variant FAILed integrity → ZERO_ELIGIBLE_VARIANTS.
> - **Robustness** — `#pass / N_eligible`, counted over each eligible variant's `consistent_with_main_experiment` (binary `pass`/`fail`; = variant's conclusion matches main experiment's). Range `0..1`; threshold = `ROBUSTNESS_THRESHOLD` (default 0.5 → at least half of eligible variants must `pass`; e.g. at N=3 this means ≥2 of 3 to PASS). `—` when no robustness is defined (INCONCLUSIVE, ZERO_ELIGIBLE_VARIANTS, or INTEGRITY_ONLY).
> - **State** — final per-claim verdict, derived from robustness on the eligible set (or from Stage 1 alone under audit-only mode):
>   - **✅ PASS** — main experiment's verdict is robust under swaps (direction = whatever the main experiment said; both supported-and-stable and rejected-and-stable count as PASS).
>   - **❌ FAIL** — main experiment's verdict is fragile (variants diverge); send to iteration to investigate the divergence.
>   - **🟡 INCONCLUSIVE** — Phase 2 main-experiment-integrity failed; variants never ran (`SWAP_VARIANTS=true`) or were policy-skipped (`SWAP_VARIANTS=false`) — either way iteration must fix the failing main-experiment sub-audit (evaluation method and/or mechanism rigor), not the claim.
>   - **🟠 ZERO_ELIGIBLE_VARIANTS** — Phase 2 passed (the main experiment is fine), but every Phase 9 variant FAILed integrity, so no `robustness` can be computed. Iteration must fix the variant scripts and re-invoke `/auto-verify <claim-id> — resume: true`; do not re-run the main experiment. Unreachable under `SWAP_VARIANTS=false`.
>   - **⚪ INTEGRITY_ONLY** — Phase 2 main-experiment-integrity is `PASS`/`WARN` but Stage 2 was intentionally skipped. The `stage2_skip_reason` field distinguishes the two producers: `swap_variants_false` (global audit-only mode) or `max_verify_claims_cap` (this claim was admitted by Stage 1 but not selected as one of the top-K picked at Phase 3 step 0). Either way no PASS/FAIL is issued and iteration takes no back-edge action — records the claim in Open Items with a per-reason upgrade suggestion (see per-cell Notes column).
> - **Notes** — short free-text caveat per claim (which dimension drove the result, rerun suggestions, per-`stage2_skip_reason` upgrade command, etc).

## Integrity Audit

**Overall**: [PASS | WARN | FAIL] — see `verify/INTEGRITY_AUDIT.md` for full Phase 2 (main experiment) + Phase 9 (variants) findings.

## Stage-2 Selection (omit section if all admitted claims were picked)

Phase 3 step 0 picked [K] of [N_admitted] admitted claims for Stage 2 (cap = MAX_VERIFY_CLAIMS = [cap]).

**Picked** (with importance rationale):
- C1: [one-sentence rationale — why this claim is more central]

**Stage-2-deferred (marked INTEGRITY_ONLY with stage2_skip_reason: max_verify_claims_cap)**:
- C6: [one-line statement] — main-experiment verdict: [supported / not-supported] — swap-test later via `/auto-verify C6 — resume: true`
- C7: ...

## Details
- [claim-id]: link to `verify/<claim_dir>/ROBUSTNESS.md` (full directory form = `<claim_id>_<short_claim>/`)

## Next Step

→ **All claims PASS** → proceed to `/auto-iteration-loop "[topic]"`. The robustness story — positive or negative, whichever applies — goes into the next-round draft / paper polish.

→ **Any claim FAILs** (`robustness < ROBUSTNESS_THRESHOLD`, main-experiment verdict was fragile under swaps) → hand to iteration: `/auto-iteration-loop "[topic] — verify-failed: [claim-ids]"`. The iteration reviewer first checks whether any of the surviving variants themselves had integrity warnings; if not, the divergence is real and the iteration loop decides between fixing the variant-side scripts (when applicable) and re-entering the claim stage to rewrite the claim. Verify itself does not choose among iteration options.

→ **Any claim INCONCLUSIVE** (Phase 2 main-experiment integrity broken — variants never ran) → hand back with `/auto-iteration-loop "[topic] — verify-inconclusive: [claim-ids]"`. The instruction to iteration is explicit: **fix the failing main-experiment sub-audit; do not change the claim**. Specifically, read each claim's `inconclusive_reason` to route the fix:
   - `main-experiment integrity broken`: rerun `/auto-experiment` with a corrected evaluation script (fix fake GT, fix score normalization, replace phantom results, run sufficient scope).
   - `main-experiment mechanism rigor broken`: rerun `/auto-experiment` with a corrected mechanism sweep (sweep α across ≥ 3 orders of magnitude in σ_proj units, log a capability metric at every point, lock α mid-plateau, run the random-direction control). The evaluation code itself can stay; only the mechanism harness needs fixing.
   - `main-experiment integrity broken (experiment + mechanism)`: fix both before rerunning.

→ **Any claim ZERO_ELIGIBLE_VARIANTS** (Phase 2 main experiment was fine; Phase 9 variants all FAILed integrity, so `N_eligible = 0`) → hand back with `/auto-iteration-loop "[topic] — verify-zero-eligible: [claim-ids]"`. The instruction to iteration is explicit: **fix the variant scripts, do not touch the main experiment or the claim**. Specifically, read each claim's `zero_eligible_reason` and the per-variant `integrity_breakdown` field to route:
   - Re-run only the integrity-failed variants under `verify/<claim_dir>/variants/`. Inspect each one's `integrity_breakdown.{experiment, mechanism}` to decide what to fix in that variant's eval script or mechanism harness, then delete the variant directory and re-invoke `/auto-verify <claim-id> — resume: true`. Phase 1's argument parser and Phase 2's main-experiment audit will both skip on resume, so only the variant-side phases re-execute.
   - Do not invoke `/auto-experiment` for ZERO_ELIGIBLE_VARIANTS — the main experiment already passed Phase 2; rerunning it would be wasted compute and risks introducing main-experiment drift.
   - (Note: when at least 1 variant survived integrity, the claim still gets a regular PASS/FAIL verdict instead of ZERO_ELIGIBLE_VARIANTS.)

→ **Any claim INTEGRITY_ONLY** (Phase 2 PASS/WARN, Stage 2 intentionally skipped) → hand back with `/auto-iteration-loop "[topic] — verify-integrity-only: [claim-ids]"`. Instruction: **no back-edge action** — the main experiment is already validated; the swap stress test was intentionally not attempted. Iteration records each claim under `### Open Items — Unverified Under Swaps` in `AUTO_REVIEW.md` with a suggestion dispatched by `stage2_skip_reason`:
   - `swap_variants_false` → `/auto-verify <claim-id> — swap-variants: true, resume: true` (Phase 2 audit reused; Stages 2–3 execute)
   - `max_verify_claims_cap` → `/auto-verify <claim-id> — resume: true` (single-claim mode; Phase 2 audit reused; Stages 2–3 execute for this one claim)

   INTEGRITY_ONLY does not consume iteration budget and does not enter the reviewer's score-weighted narrative — it is a first-class terminal state carrying its own integrity caveat, not a soft-fail.

Verify never picks among the iteration options on its own — its job is to flag PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS / INTEGRITY_ONLY with the right diagnostic and hand control to the iteration loop's reviewer.
```

Save to `verify/VERIFY_REPORT.md` (fixed name) + timestamped copy, and append to root `MANIFEST.md`.

Present final status:

```
🔬 Verification complete:
- Mode: [full (Stages 1–3) | audit-only (Stage 1 only — SWAP_VARIANTS=false)]
- Claims processed: [N]
- ✅ PASS: [A]  (main-experiment verdict robust under swaps — direction noted per claim)
- ❌ FAIL: [B]  (main-experiment verdict fragile — sent to iteration)
- 🟡 INCONCLUSIVE: [C]  (main experiment broken at Phase 2 — exp-FAIL: [C_exp_p2], mech-FAIL: [C_mech_p2], both-FAIL: [C_both_p2])
- 🟠 ZERO_ELIGIBLE_VARIANTS: [D]  (Phase 2 passed; all variants FAILed Phase 9 integrity — fix variants only)     # 0 under audit-only mode
- ⚪ INTEGRITY_ONLY: [E]  (Stage 1 audit validated; swap stress test skipped — SWAP_VARIANTS=false)               # 0 under full mode
- Main-experiment integrity (Phase 2, combined): [PASS | WARN | FAIL]   (exp: [...], mech: [...])
- Variant integrity (Phase 9, combined): [PASS | WARN | FAIL | skipped]  # 'skipped' under audit-only mode
- GPU-hours spent: [X]                                                    # ~0 under audit-only mode

Report: verify/VERIFY_REPORT.md
Per-claim details: verify/<claim_dir>/ROBUSTNESS.md
Integrity audit: verify/INTEGRITY_AUDIT.md (main experiment + variants; per-claim Exp/Mech/Combined breakdown)

Next: [suggested follow-up based on PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS counts]
```

## Directory Layout

```
verify/
├── VERIFY_REPORT.md                          # fixed-name top-level summary
├── VERIFY_REPORT_YYYYMMDD_HHmmss.md          # timestamped history
├── INTEGRITY_AUDIT.md                        # per-claim verdict rollup (Phase 2 + Phase 9), no A–F detail
└── <claim_id>_<short_claim>/                 # one folder per verified claim
    ├── PLAN.md                               # variants chosen + justification
    ├── ROBUSTNESS.md                         # aggregated per-claim verdict (PASS / FAIL / INCONCLUSIVE / ZERO_ELIGIBLE_VARIANTS / INTEGRITY_ONLY);
    │                                         # audit-only shape (SWAP_VARIANTS=false) is always written even when COMPACT=true
    │                                         # (sole machine-readable verdict record downstream depends on)
    ├── main_experiment_audit/                       # Phase 2: /experiment-audit + /mechanism-audit on refine-logs/, scoped by — claim
    │   ├── EXPERIMENT_AUDIT.md               # full A–F findings (methodology) for this claim's main-experiment evidence
    │   ├── EXPERIMENT_AUDIT.json             # overall_verdict = methodology integrity
    │   ├── MECHANISM_AUDIT.md                # mechanism-rigor findings (A: steering coefficient sweep; B–F reserved)
    │   └── MECHANISM_AUDIT.json              # overall_verdict = mechanism rigor (may be n/a)
    │                                         # Phase 2's gate verdict = max_severity(exp, mech) with n/a treated as pass
    ├── variant_audit/                        # Phase 9: same pair, on this claim's variants
    │   ├── EXPERIMENT_AUDIT.md               # full A–F findings on variant runs
    │   ├── EXPERIMENT_AUDIT.json             # overall_verdict = variant methodology integrity
    │   ├── MECHANISM_AUDIT.md                # mechanism-rigor findings on variants
    │   └── MECHANISM_AUDIT.json              # overall_verdict = variant mechanism rigor
    └── variants/
        ├── method-swap-<tag>/
        │   ├── DIFF.md                       # what changed vs the main experiment
        │   ├── config.yaml
        │   ├── run.sh
        │   ├── result.json                   # raw metrics
        │   └── verdict.json                  # /result-to-claim output + integrity_status (combined) + integrity_breakdown {experiment, mechanism}
        ├── dataset-swap-<tag>/
        │   └── ...
        └── model-swap-<tag>/
            └── ...
```

### Per-claim folder naming

Use the format `<claim_id>_<short_claim>/`, where:

- `<claim_id>` — the Claim ID from `EXPERIMENT_PLAN.md` (e.g., `C1`, `C2`, …). Keeps the folder cross-referenceable with the plan, results, and verdicts.
- `<short_claim>` — **at most 4 snake_case words** summarizing what the claim asserts. Stay descriptive over clever.

Examples (good):

```
verify/C1_gasl_beats_baselines/
verify/C2_layer_localization/
verify/C6_ood_generalization/
verify/C8_seed_stability/
```

Examples (bad):

```
verify/C1/                            # opaque, no claim summary
verify/C1-gasl-beats-baselines/       # use underscores, not hyphens
verify/gasl_beats_baselines/          # missing claim_id — breaks cross-reference
verify/C1_method_beats_three_strong_random_baselines_at_best_layer/  # too long
```

Inside prose and tables (`VERIFY_REPORT.md`, `ROBUSTNESS.md`), the **`claim`** column still uses the bare ID (`C1`); path references use the full `verify/C1_gasl_beats_baselines/` form.

Variant subfolders under `variants/` keep their existing format: `<dimension>-swap-<tag>/` (hyphens, e.g., `method-swap-zero-ablation/`, `model-swap-gpt2-medium/`).

> **Notation in the rest of this file:** the placeholder `<claim_dir>` (e.g., `verify/<claim_dir>/PLAN.md`) is shorthand for the full `<claim_id>_<short_claim>` directory name defined above. JSON fields like `"claim_id"` continue to hold the bare ID (`"C1"`).

## Key Rules

- **Five terminal states.** Each claim ends in PASS, FAIL, INCONCLUSIVE, ZERO_ELIGIBLE_VARIANTS, or INTEGRITY_ONLY. PASS / FAIL are scientific results on the claim itself (robust support / robust rejection both count as PASS; fragile verdict = FAIL). INCONCLUSIVE is orthogonal — Phase 2 said the main experiment evaluation method or mechanism rigor is broken, so neither PASS nor FAIL would be honest and variants were never run. ZERO_ELIGIBLE_VARIANTS is also orthogonal but on a different surface — Phase 2 passed, variants ran, but every one failed Phase 9 integrity so `N_eligible = 0` and no `robustness` is computable. INTEGRITY_ONLY exists **only when `SWAP_VARIANTS=false`** — Phase 2 passed but Stages 2–3 were intentionally skipped by policy (distinct from ZERO_ELIGIBLE_VARIANTS, where the pipeline tried and every variant broke). Never collapse these states into one another; each hands a different instruction to iteration (investigate divergence / fix main-experiment scripts / fix variant scripts / no-op with upgrade suggestion).
- **Audit before swapping, per claim.** Phase 2 (the main-experiment integrity gate, Stage 1) runs *before* any GPU is spent on variants, and runs **two cross-model audits per target claim** — `/experiment-audit — claim Cx` (methodology honesty) followed by `/mechanism-audit — claim Cx` (mechanism rigor; returns N/A when no mechanism intervention is used). If a claim's evaluation method or mechanism is broken, swap variants for that claim cannot rescue it — they compute robustness around a broken anchor. A combined FAIL at Phase 2 short-circuits only that specific claim to INCONCLUSIVE; clean claims continue. The `inconclusive_reason` always names which sub-audit failed so iteration knows what to fix.
- **Integrity-failed variants are excluded from BOTH numerator AND denominator.** A variant with `integrity_status = fail` means "we don't know what this variant would have said", not "it disagrees with the main experiment". Counting it as 0 in the numerator while keeping it in the denominator would silently bias `robustness` toward FAIL, which violates objective correctness. Always shrink the eligible set symmetrically. If the eligible set drops below `MIN_VARIANTS_FOR_VERDICT` (default 1 → triggers only at `N_eligible = 0`), the claim becomes **ZERO_ELIGIBLE_VARIANTS** (a distinct terminal state from INCONCLUSIVE: INCONCLUSIVE means the main experiment is broken so iteration must fix the main experiment; ZERO_ELIGIBLE_VARIANTS means the main experiment was fine but every variant broke, so iteration must fix the variant scripts only). When `N_eligible = 1`, the verdict stands as a regular PASS/FAIL.
- **Stage 1 audit scope is not gated by `MAX_VERIFY_CLAIMS`.** Every target claim gets its Phase 2 main-experiment audit; the cap only chooses which Stage 1 admitted claims proceed to Stage 2. This preserves audit coverage across all claims even under the default `MAX_VERIFY_CLAIMS = 1`, and lets un-picked admitted claims be swap-tested later via `/auto-verify <id> — resume: true` without re-paying the audit cost.
- **Freeze the claim.** The claim statement from `/auto-experiment` + `/result-to-claim` is immutable during verification. Verify tests whether *the evidence* still supports *the same* claim under swaps — it does not revise the claim mid-flight.
- **One dimension per variant.** Method swaps swap only the method, dataset swaps swap only the dataset, model swaps swap only the model. Two-factor swaps are `beast`-only and must be justified explicitly.
- **DIMENSIONS strictly determines variant count.** One swap per listed axis, no more, no less — there is no EFFORT multiplier. Axes excluded from `DIMENSIONS` get zero variants. The VERIFY_REPORT must record the active dimension list so readers know which axes were NOT tested (an untested axis is a scope gap, not a positive signal). To run more thorough analyses (multi-seed within an axis, 2-factor cross-axis interactions), use `/ablation-planner` — these are not verify's job.
- **Main-experiment parity.** If a hyperparameter has to change for a swap to run (e.g., batch size on a larger model), the main experiment is re-run with the same adjustment before the comparison is trusted. No silent re-scaling.
- **Reviewer leads alternative selection.** The external LLM reviewer ranks candidates by "how hard this tests the claim," not by "closeness to the main experiment." CC does not pre-filter to comfortable swaps.
- **Every eligible variant must have a verdict.** Even `no`-verdict variants are recorded and counted (within the eligible set) — a negative result on a model swap is the signal that the claim is scale-bound. Only `integrity_status = fail` variants drop out.
- **Save everything as JSON/CSV.** Raw metrics → `result.json`; per-variant verdicts → `verdict.json` (with `integrity_status` = combined and `integrity_breakdown` = `{experiment, mechanism}`); aggregate → `ROBUSTNESS.md` + `VERIFY_REPORT.md`. Phase 2 writes `{EXPERIMENT,MECHANISM}_AUDIT.{md,json}` into `main_experiment_audit/`; Phase 9 writes the same pair into `variant_audit/`; both phases feed combined verdicts into `verify/INTEGRITY_AUDIT.md`.
- **Do not invent new claims.** If variants surface an interesting *new* claim (e.g., "method works only for long-context tasks"), record it in `findings.md` as a follow-up idea for `/idea-creator`, but do not add it to this verify run.
- **Respect compute budget.** Track GPU-hours against the plan. If a swap's pilot run projects ≥ 2× main-experiment compute, request user confirmation before launching the full run. Phase 2's and Phase 9's audit cost is negligible (LLM reviewer + a few file reads) and is *not* counted against the swap budget.

## Composing with Other Skills

```
/auto-claim "direction"              ← Workflow 1: find + refine + plan
/auto-experiment                     ← Workflow 1.5: implement + deploy
/auto-verify [claim-id]              ← you are here (Workflow 1.75: stress-test claims in both directions)
  ├── /experiment-audit (Phase 2)     ← Phase 2 audit 1/2: per-claim main-experiment methodology audit
  │                                     called once per target Cx with — claim Cx — output-dir verify/<claim_dir>/main_experiment_audit
  │                                     → output: verify/<claim_dir>/main_experiment_audit/EXPERIMENT_AUDIT.{md,json}
  ├── /mechanism-audit (Phase 2)      ← Phase 2 audit 2/2: per-claim main-experiment mechanism-rigor audit
  │                                     called once per target Cx with — claim Cx — output-dir verify/<claim_dir>/main_experiment_audit
  │                                     → output: verify/<claim_dir>/main_experiment_audit/MECHANISM_AUDIT.{md,json}
  │                                     → Phase 2 gate = max_severity(exp, mech); n/a treated as pass
  │                                     → combined FAIL short-circuits only that claim to INCONCLUSIVE
  ├── /result-to-claim                ← per-claim verdicts (auto-run if missing, plus per-variant)
  ├── ./pick-alternatives/SKILL.md    ← sub-skill (inline, not a slash command): choose method/dataset/model swaps (within mechanism family)
  ├── /research-lit                   ← called when candidate research is thin
  ├── /run-experiment                 ← launch each variant
  ├── /monitor-experiment             ← track variant progress
  ├── /analyze-results                ← compare variants vs the main experiment (optional)
  ├── /experiment-audit (Phase 9)     ← Phase 9 audit 1/2: per-claim variant methodology audit
  │                                     called once per admitted Cx with — claim Cx — output-dir verify/<claim_dir>/variant_audit
  │                                     → output: verify/<claim_dir>/variant_audit/EXPERIMENT_AUDIT.{md,json}
  └── /mechanism-audit (Phase 9)      ← Phase 9 audit 2/2: per-claim variant mechanism-rigor audit
                                        called once per admitted Cx with — claim Cx — output-dir verify/<claim_dir>/variant_audit
                                        → output: verify/<claim_dir>/variant_audit/MECHANISM_AUDIT.{md,json}
                                        → per-variant integrity_status = max_severity(exp, mech) — n/a treated as pass
                                        → integrity-FAIL variants excluded from BOTH numerator & denominator by Phase 10
/auto-iteration-loop "direction"     ← Workflow 2: review + iterate with verified claims

Or use /auto for the autonomous idea → experiments → verify chain.
```
