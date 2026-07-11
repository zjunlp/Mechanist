---
name: auto-experiment
description: "Workflow 1.5: Bridge between idea discovery and auto review. Reads EXPERIMENT_PLAN.md, routes mechanism family inline (Phase 1.5), implements experiment code, deploys to GPU, and collects initial results. Use when user says \"implement experiments\", \"experiment\", \"deploy the plan\", or has an experiment plan ready to execute."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, AskUserQuestion, Skill, mcp__llm-chat__chat
---

# Workflow 1.5: Experiment

Implement and deploy experiments from plan: **$ARGUMENTS**

## Overview

This skill bridges Workflow 1 (idea discovery + method refinement) and Workflow 2 (auto review loop). It takes the experiment plan and turns it into running experiments with initial results.

```
Workflow 1 output:                    This skill:                                    Workflow 2 input:
refine-logs/EXPERIMENT_PLAN.md   →   implement → LLM review → deploy → collect → initial results ready
refine-logs/EXPERIMENT_TRACKER.md     code        (cross-model)    /run-experiment     for /auto-iteration-loop
refine-logs/FINAL_PROPOSAL.md
```

## Constants

- **RESEARCH_DOMAIN = auto** — Project domain tag (free-form, e.g. `mechanistic-interpretability`, `vision-encoders`, `rl-policy-eval`). **Consumed by Phase 1.5 only** as a routing constraint to `/mechanism-skills` — see Phase 1.5 Step 2's `domain:` arg. When `null` or `auto`, Phase 1.5 infers from `FINAL_PROPOSAL.md`; on ambiguous inference, silently default to `general` and log `[research-domain] inference ambiguous — defaulted to general` (this fallback bypasses `AUTO_PROCEED` by design — see `/auto`'s flag-table row for the canonical statement). To force a specific domain, pass it explicitly on the CLI. (Note: Phase 1.1 routes through `/experiment-tips` using its own symptom-level trigger table and does **not** consume this constant.)
- **MECHANISM_ROUTING = auto** — Phase 1.5 mechanism-family routing mode. `auto` (default): invoke `/mechanism-skills`, write `refine-logs/MECHANISM_ROUTING.md`, present 2–3 candidates and let the caller pick (auto-select #1 when `AUTO_PROCEED=true`; otherwise block on the caller's `AskUserQuestion`). `skip`: assume routing already exists (or is not applicable) and proceed. `not-applicable`: explicitly mark behavioral-only proposal and skip without invoking. When called from `/auto`, the orchestrator's mini-prompt fills `CHOSEN_FAMILY` so this skill is re-entered with `MECHANISM_ROUTING=skip`.
- **CHOSEN_FAMILY = none** *(dynamic — not in config; forwarded by /auto's orchestrator — from `MECHANISM=given` (the user's `chosen_mechanism` captured by the claim stage), the `AUTO_PROCEED=false` family mini-prompt, or an explicit `family:` pin in `task.md` (cross-round Rule 2), after any settled-pin conflict is resolved)* — When set, commits this family/submethod combo from `MECHANISM_ROUTING.md` before implementation (Phase 1.5 Mode B).
- **CODE_REVIEW = true** — external LLM reviewer checks experiment code before deployment. Catches logic bugs before wasting GPU hours. Set `false` to skip.
- **AUTO_DEPLOY = true** — Automatically deploy experiments after implementation + review. Set `false` to manually inspect code before deploying. Treated as a *standing approval* for the deploy step: when `AUTO_DEPLOY=true`, the Phase 4 deploy proceeds even if `AUTO_PROCEED=false`.
- **AUTO_PROCEED = true** — Whether the Phase 4 Experiment Gate may skip the UI prompt. When `true` (default) and `AUTO_DEPLOY=true`, the gate proceeds silently. When `false` and `AUTO_DEPLOY=false`, the gate calls `AskUserQuestion` (approve / narrow-scope / abort) and blocks until the user answers. `AUTO_DEPLOY=true` overrides `AUTO_PROCEED=false` for this gate (standing approval). Forwarded from `/auto`.
- **SANITY_FIRST = true** — Run the sanity-stage experiment first (smallest, fastest) before launching the rest. Catches setup bugs early.
- **MAX_PARALLEL_RUNS = 4** — Maximum number of experiments to deploy in parallel (limited by available GPUs). For Phase 4's queue dispatch path (Phase 4.B), this becomes `max_parallel:` in the `/experiment-queue` manifest. For the direct dispatch path (Phase 4.A), it's the in-skill concurrency cap on `/run-experiment` calls.
- **BATCH_DISPATCH = `auto`** — Phase 4 dispatch routing rule. `auto` (default): per the Phase 4.0 table — milestones with ≥ 10 runs, `depends_on`, grid expansions, or ≥ 3-seed × ≥ 3-config multi-seed sweeps go to `/experiment-queue`; smaller ad-hoc milestones go to `/run-experiment`. `queue`: force every milestone to `/experiment-queue` (use when you know the workload benefits from OOM retry + stale cleanup even at small sizes). `direct`: force every milestone to `/run-experiment` (use only when debugging the queue scheduler itself; emits a warning if any milestone would have triggered the queue rule under `auto`). Forwarded from `/auto`.
- **BASE_REPO = null** — GitHub repo URL to use as base codebase. When set, clone the repo first and implement experiments on top of it. When `null`, write code from scratch or reuse existing project files.
- **COMPACT = false** — When `true`, (1) read `idea-stage/IDEA_CANDIDATES.md` instead of full `idea-stage/IDEA_REPORT.md` if available, (2) append experiment results to `EXPERIMENT_LOG.md` after collection.
- **RESUME = false** — When `true`, each phase checks if its primary artifact already exists non-empty and skips itself if so (see "Resume protocol" below). Useful for picking up after a crash. Default `false` = every phase always runs from scratch and overwrites prior artifacts. Resume never deletes pre-existing files.
- **GPU_ID = `auto`** — GPU device(s) to use for sanity and full-suite runs. `auto` (default) inherits from environment / launcher. A single id (`0`) or comma-list (`4,5,6,7`) causes Phase 3 (sanity) and Phase 4 (deploy) to **pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional argument to `/run-experiment`** — the run-experiment skill then exports this env var before launching the experiment subprocess (do not treat it as a shell prefix; `/run-experiment` is a Skill invocation, not a shell command). Also record the effective `CUDA_VISIBLE_DEVICES` into each run's `run.sh` so reproductions land on the same devices. Override: `— gpu-id: 4,5,6,7`. When `GPU_ID` lists multiple devices and `MAX_PARALLEL_RUNS > 1`, partition devices across concurrent runs (e.g., `GPU_ID=4,5,6,7` + 2 parallel → run A on `4,5`, run B on `6,7`); do not co-schedule two runs on the same device unless memory measurements confirm fit. Forwarded from `/auto` and from `agents/experiment.md`; `/auto-verify` follows the same convention for verify variants.

> Standalone overrides: `/auto-experiment "EXPERIMENT_PLAN.md" — compact: true, base-repo: https://github.com/org/project, research-domain: vision-encoders, mechanism-routing: auto`.

## Resource-Fidelity Harness (the reproduction combination)

**Active only when the `resource_fidelity: strict` marker is present** in the top metadata of `refine-logs/FINAL_PROPOSAL.md` / `refine-logs/EXPERIMENT_PLAN.md` — which `/auto-claim` stamps **iff `BEHAVIOR_SOURCE=given` AND `MECHANISM=given`** (the reproduction combination). There is no flag and no override: activation is purely marker-driven (only the reproduction combination stamps it; every other combination never does). When the marker is absent (any cost-aware combination), the existing cost-aware behavior is unchanged.

**Scope: the main experiment only.** The harness binds the main-experiment runs this skill (`/auto-experiment`) produces. It does **not** bind `/auto-verify`, whose deliberate model/dataset/method swaps are how it measures robustness — verify ignores the marker by design. When active, every phase of *this* skill obeys all five rules:

1. **Exact models.** Instantiate the precise model id(s) / size(s) the plan specifies. Never substitute a smaller / cheaper / distilled / quantized variant to save compute or memory (quantization or reduced precision is allowed only if the plan / `task.md` explicitly calls for it).
2. **Exact data.** Use the full specified dataset(s) and `used_n` / split. Never subset, down-sample, cap, or truncate the data to save time. A run that consumed less than the specified `used_n` is recorded **failed**, not `done`, and surfaced — never papered over with a subset note.
3. **No must-run skipped.** Run every must-run experiment at full specified scale (seeds, configs, grid points). Cost (GPU-hours) is not grounds to skip or thin a must-run milestone.
4. **OOM → auto-scale-up across GPUs, never downscale.** On OOM, resolve it **only** by science-neutral memory techniques — batch size ↓ (with gradient accumulation to preserve the effective batch), gradient checkpointing, sequence chunking, and **automatically adding more GPUs to the run**: query free GPUs (`nvidia-smi`, `memory.used < 500 MiB`), add them and enable sharding, relaunch. If the script is single-GPU (`model.cuda()` / `.to(device)`), auto-convert its loading to `device_map="auto"` / FSDP / CPU-or-disk offload — and before trusting it on the full model, verify the conversion is wired correctly with a **numeric-equivalence check on a fit-on-one-GPU proxy slice** (single-GPU vs sharded outputs/loss must match within tolerance; sharding is a mathematically equivalent transform, so this step only catches a mis-wired edit, not the sharding itself). Keep adding free GPUs up to `OOM_MAX_GPUS` (default 4) while leaving `MAX_PARALLEL_RUNS` headroom for sibling runs. **Only** when the cap is reached (or no free GPU remains) **and** CPU/disk offload is also exhausted do you **HALT and report** — write `Pipeline status = halted-at-experiment: strict-OOM-after-scaleup` with the scale-up trace (started on N GPUs, auto-expanded to M, sharding mode, equivalence-check result, final memory shortfall) and next-round options (add GPUs / bigger machine / explicitly authorize quantization in `task.md` / explicitly down-scope the plan / switch to discovery). **Never** shrink the model or subset the data to make it fit — that is the one forbidden remedy, even in full-auto.
5. **Sanity is exempt but not a substitute.** The `SANITY_FIRST` smoke test may run at a tiny scale (its only job is catching setup bugs). The real runs that produce results must use the exact resources above; never report a sanity-scale run as a reproduction result.

## Inputs

This skill expects one or more of:

1. **`refine-logs/EXPERIMENT_PLAN.md`** (best) — claim-driven experiment roadmap from `/experiment-plan`
2. **`refine-logs/EXPERIMENT_TRACKER.md`** — run-by-run execution table
3. **`refine-logs/FINAL_PROPOSAL.md`** — method description for implementation context
4. **`idea-stage/IDEA_CANDIDATES.md`** — compact idea summary (preferred when `COMPACT: true`) *(fall back to `./IDEA_CANDIDATES.md` if not found)*
5. **`idea-stage/IDEA_REPORT.md`** — full brainstorm output *(fall back to `./IDEA_REPORT.md` if not found)*

If none exist, ask the user what experiments to implement.

## Workflow

### Resume protocol (only when `RESUME = true`)

Skip entirely if `RESUME = false` (default). When `true`, each phase below begins with a **skip-if-present** check:

| Phase | Primary artifact (skip key) | Notes |
|---|---|---|
| 1    | `refine-logs/EXPERIMENT_PLAN.md` already loaded into memory (no separate file) | Always cheap; just re-parse. |
| 1.1  | `refine-logs/EXPERIMENT_TIPS.md` with `committed: true` | Skip routing if already committed; matched tips must still be re-read into the current context each Phase 2 invocation, since context doesn't survive across calls. |
| 1.25 | `refine-logs/EXPERIMENT_RESULTS.md` with `phenomenon_status:` set to a **terminal** value (`not-established`, or `inconclusive` after the retry budget) | The M0 gate already ran and ended the stage — do **not** re-run M0 or proceed to mechanism. Re-emit the same terminal `phenomenon_status` in the return so `/auto` re-applies the early exit. If `phenomenon_status` is `established` / `conditional` (or M0 partially ran), fall through and let Phase 1.5+ resume normally. Only applies when the plan has a milestone with `kind: phenomenon-validation` (`BEHAVIOR_SOURCE ∈ {given-validation, discovery}`); otherwise this phase doesn't exist. |
| 1.5  | `refine-logs/MECHANISM_ROUTING.md` with `committed: true` (or `routing: not-applicable`) **and** a `## Plan reconciliation` section whose `reconciliation_status` is set (`ok`/`escalate`/`n/a`) | Skip routing entirely only if both hold. If `committed: true` but reconciliation is missing (a prior run crashed between commit and Step 7), do **not** skip — resume at Step 7 to complete reconciliation before Phase 2. If `reconciliation_status: escalate`, HALT (do not proceed to build). |
| 2    | `runs/<run_id>_<short_purpose>/` directory non-empty for every run referenced by the plan | Per-run granularity: skip code generation for runs whose directory already has code. Path convention matches the "Output Directory Naming" section below. |
| 2.5  | reviewer-approved marker in run directory (e.g., `.code_review_passed`) | Per-run. |
| 3    | sanity run's results captured in `EXPERIMENT_TRACKER.md` | Skip sanity if its row is present. |
| 4    | per-run status in `EXPERIMENT_TRACKER.md` marked `done` | Per-run: don't redeploy completed runs. |
| 5    | `refine-logs/EXPERIMENT_RESULTS.md` exists non-empty AND `EXPERIMENT_TRACKER.md` has every plan run marked terminal | Skip collection when everything is already aggregated. |
| 5.5 / 5.6 / 6 | always run (cheap rewrites / handoff steps) | — |

Log every skip as `[resume] phase <N> skipped — <reason>`. Resume never deletes pre-existing files. To force a phase to re-run, delete its primary artifact (or, for Phase 4, the run directory).

### Phase 1: Parse the Experiment Plan

Read `EXPERIMENT_PLAN.md` and extract:

1. **Run order and milestones** — which experiments run first (sanity → baseline → main → ablation → polish)
2. **For each experiment block:**
   - Dataset / split / task
   - Compared systems and variants
   - Metrics to compute
   - Setup details (backbone, hyperparameters, seeds)
   - Success criterion
   - Priority (MUST-RUN vs NICE-TO-HAVE)
3. **Compute budget** — total estimated GPU-hours
4. **Method details** from `FINAL_PROPOSAL.md` — what exactly to implement
5. **Mechanism routing hints** (under `mechanism_strategy:`, written by the claim stage from cross-round memory) — the chosen `direction`; any `families_already_settled: [<families>]` (families already `confirmed`/`refuted` for this behavior+direction, to be **excluded** at routing — Phase 1.5); and any explicit `family:` pin. The list is absent (or omitted) when there is nothing to exclude — round 1, a new phenomenon, or a non-mechanism plan.

Present a brief summary:

```
📋 Experiment plan loaded:
- Milestones: [N] (sanity → baseline → main → ablation)
- Must-run experiments: [N]
- Nice-to-have: [N]
- Estimated GPU-hours: [X]

Proceeding to implementation.
```

**Data Rules — load and check now (data design).** Load `skills/data-rule/SKILL.md` and validate the plan's data against its four rules (provenance / splits / labels / sample-size floor). Loaded once here, it governs all data use through the rest of the workflow — unconditional, not the Phase 1.1 symptom routing. Surface any violation before proceeding.

### Phase 1.1: Experiment-Tips Routing 

Before any code is written, route the parsed plan through `/experiment-tips` — the routing entry point under `skills/experiment-tips/`. Tips encode hard-won conventions that prevent silent reproducibility / overclaim failure modes. Catching them at plan-implementation time is free; catching them after a full deploy wastes GPU hours.

**Routing flow:**

1. **Read** the artifacts that drive the routing: `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/FINAL_PROPOSAL.md`. Extract: task description, datasets, models, declared `n_pairs` / `n_examples`, intervention sites (block / layer / token / residue), steering parameter names (`α`, `dose`, `magnitude`, `scale`, `coefficient`), and any adapter-based fine-tune milestone (LoRA / QLoRA / PEFT).

2. **Invoke `/experiment-tips`** as the routing entry point. It matches the plan against the symptom-level trigger table in `skills/experiment-tips/SKILL.md` and returns a list of tip folders to load.

3. **For each matched tip**, load `skills/experiment-tips/<tip>/SKILL.md` in full into working memory. **Hard requirement:** the routing previews in `experiment-tips/SKILL.md` are deliberately thin — every implementation detail lives in the tip's `SKILL.md`, not in the routing file. Acting on the preview alone is forbidden.

4. **Write `refine-logs/EXPERIMENT_TIPS.md`** with the routing decision:

   ```markdown
   # Experiment Tips Routing

   <!-- Metadata block (parsed by /auto orchestrator resume check). -->
   committed: true
   matched_tips:
     - <tip-folder-1>
     - <tip-folder-2>

   ## Matches

   1. **<tip-folder>** — <one-line trigger that fired>
      - convention to adopt: <one-line summary from the tip>
   2. **<tip-folder>** — <one-line trigger that fired>
      - convention to adopt: <one-line summary>

   ## No-match log
   <if a borderline trigger didn't fire, note it here for audit>
   ```

   If no tip matches, write a stub `EXPERIMENT_TIPS.md` containing `committed: true` and `matched_tips: []` plus a one-line note explaining why none matched (e.g., "behavioral-only proposal, no representation interventions"). Always write the file — it's the audit anchor for Phase 2 to confirm tips were considered.

**Hard requirement**: before Phase 1.25, the experiment agent's transcript must show an actual `/experiment-tips` invocation. Bypassing the skill or fabricating `refine-logs/EXPERIMENT_TIPS.md` by hand is forbidden. If the transcript shows no invocation, or the file is absent or hand-written, re-run Phase 1.1.

### Phase 1.25: Phenomenon-Validation Gate (`BEHAVIOR_SOURCE ∈ {given-validation, discovery}`)

**Runs only when `EXPERIMENT_PLAN.md` contains a milestone carrying the machine marker `kind: phenomenon-validation`** (conventionally titled M0) — i.e. the claim stage ran with `BEHAVIOR_SOURCE ∈ {given-validation, discovery}`. **Detect by the `kind: phenomenon-validation` field, never by the milestone's title** (the title may be phrased or localized freely; only the field is the stable contract). If no milestone has that marker (a `BEHAVIOR_SOURCE=given` run, or any non-phenomenon plan), skip this phase entirely and set `phenomenon_status = n/a`. The principle: claim only *assumed* the phenomenon exists and proposed a mechanism for it — this gate is where the assumption is actually tested, **before** any mechanism compute is spent.


Run M0 **first and alone** at the plan's specified `used_n`, then decide a **four-state `phenomenon_status`**. Concretely:

- **Implement** only M0's code (the Phase 2 implementation step, scoped to M0's milestone). If `CODE_REVIEW=true`, M0's code gets one cross-model review pass (Phase 2.5) like any other run. M0's scale is set by the plan's `used_n` — the agent may not subset, cap, or down-sample M0's data to save compute. An M0 run that consumed less than the planned `used_n` is recorded **failed**, not `done` (Phase 5's `used_n` rule).
- **Deploy** M0 via `/run-experiment` (one run). This creates M0's `runs/<run_id>_*/` directory and flips its `EXPERIMENT_TRACKER.md` row to `done`/`failed` through the normal mechanism — so the later Phase 4 deploy **automatically skips re-running M0** (its per-run skip key is already satisfied), and resume is consistent. Do not hand-roll separate bookkeeping.
- Forward `GPU_ID` to M0's run exactly as Phase 4 would.

Then decide the verdict:

1. **Lightweight integrity check** on M0 before trusting its verdict: invoke `/experiment-audit` scoped to M0 (the same audit verify's Phase 2 uses). This separates "the phenomenon is genuinely absent" from "the M0 test itself was broken/underpowered".
2. Assign `phenomenon_status`:
   - **`established`** — M0 audit is clean AND the behavior reproduces per its pass criterion (paraphrase/seed/decoding robust, confounds controlled, adequate n, trivial-explanation ruled out). → **Proceed** to Phase 1.5 and the mechanism milestones (M1…Mn) normally.
   - **`conditional`** — M0 audit clean, but the behavior holds only under a subset of conditions. → **Runtime-scope; do not edit the plan** (`EXPERIMENT_PLAN.md` is owned by claim Phase 4.5). Run the mechanism milestones with inputs restricted to the condition subset where the phenomenon holds, record `phenomenon_status: conditional` + the boundary in `EXPERIMENT_RESULTS.md`, and tag the claim `conditional — holds under <X>` so `/auto` carries it into the ledger. Formally narrowing the claim text and re-planning is the iteration loop's type-③ job, not this stage. **`AUTO_PROCEED`**: `true` auto-continues with the narrowed scope; `false` → `AskUserQuestion` (`continue with narrowed scope` / `terminate`) and block.
   - **`inconclusive`**  — M0's integrity audit FAILs; the phenomenon is *untested*, not disproven. → Do not terminate. Diagnose, fix at the lowest sufficient level, and re-run M0. Log every fix under M0's block in `EXPERIMENT_RESULTS.md` (what changed, old → new, audit rationale).
     - **Script bug** (crash, wrong path, tensor-shape error, eval bug) → `auto-debug` M0 (≤ 3 attempts), then re-run.
     - **Run-level methodology** (under-sampled within plan limits, seed not fixed, decoding drift) → adjust the M0 **run invocation** only; leave the plan alone.
     - **Plan-level methodology** (wrong metric, `used_n` too low, mis-specified coefficient / threshold / hyperparameter, inadequate dataset size or split) → most commonly under-tuned knobs (finetune lr / LoRA rank / epochs / batch, steering α / target layer, thresholds, decoding temperature). **Re-invoke `/experiment-tips` explicitly for hyperparameter / coefficient tuning** — not a general re-audit — passing M0's realized evidence (loss / effect size / refusal rate / seed variance) and routing to the matching sub-skill: `experiment-tips/finetune-hyperparameter-sweep` for fine-tune knobs, `experiment-tips/steering-coefficient-tuning` for α / β / dose of any additive intervention (steering / CAA / DAS / SAE / ROME), `experiment-tips/steering-block-selection` for the target layer / site / window. Apply the returned scan grid by editing `EXPERIMENT_PLAN.md` in place, confined to the implicated field(s); do not touch the claim, phenomenon description, or milestone graph.

   - **`not-established`** — M0 audit clean AND behavior does **not** reproduce at adequate power. → Before settling a terminal negative, treat the null as a candidate hyperparameter / coefficient mis-setting: **re-invoke `/experiment-tips` for tuning** with M0's realized evidence, using the same sub-skill routing as the **plan-level branch** above. If a matching sub-skill returns a concrete scan or knob change, apply it under the `inconclusive` branch's script / run / plan rules and re-run M0; otherwise fall through to step 3.


3. **Tuning budget and terminal handling** (shared by `inconclusive` and `not-established`). Total Phase 1.25 iterations (initial deploy + tuning retries) ≤ **3**; the budget covers all tuning attempts across knobs, not one per knob. Terminate when any of the following holds:
   (a) the 3-iteration budget is exhausted and the verdict is still `not-established` / `inconclusive`,
   (b) no matching tuning sub-skill returns an actionable change, or
   (c) you diagnose a hyperparameter / coefficient as a likely contributor to the null but the remaining budget cannot cover the required search space.

   On termination: write terminal `refine-logs/EXPERIMENT_RESULTS.md` with `phenomenon_status: not-established` or `inconclusive` in the top metadata, M0's evidence framed as a negative result, and every retry (**knob, old → new value, resulting verdict**) logged under M0's block. **Append a mandatory entry to `claims_ledger.json`'s `open_items[]`** (rendered into `CLAIMS_LEDGER.md`'s Open Items section) of the form: *"Phase 1.25 stopped after `<n>` automated tuning iterations on `<milestone id>` (knobs tried: `<knob>=<v0>→<v1>`, …); phenomenon remained `<status>`, and hyperparameters / coefficients are a likely contributor. Recommend the user manually tune from the recorded scan bounds before re-invoking `/auto`."* This open-item entry is **required whenever tuning is a suspected cause** — trigger (c) covers the case where you stop before exhausting the budget because the automated sweep is not the right instrument. Set `phenomenon_status` in the Phase 6 return so `/auto` skips verify + iteration and ends as `ended-phenomenon-not-established` or `ended-phenomenon-inconclusive`. **`AUTO_PROCEED`**: `true` auto-terminates; `false` → `AskUserQuestion` (`terminate — accept the result and write the report` (recommended) / `re-run M0 — I will adjust the test/plan first`) and block. Do **not** offer "narrow scope" — that is a `conditional`-only action.

> 🚨 **Phase 1.25 hard constraints (non-negotiable):**
> 1. **~20 GPU-hours are pre-allocated.** Time/GPU cost is **not** a valid reason to skip a sweep or retry — only the terminal triggers below (3-iteration budget / no actionable sub-skill / trigger (c)) may stop iteration.
> 2. **Terminal `not-established` / `inconclusive` skips all downstream mechanism milestones (M1…Mn).** You **must** exhaust matching tuning sub-skills and retries within the 3-attempt budget before settling on either verdict.
3.**`finetune-hyperparameter-sweep` in Phase 1.25** — three rules you must obey:
   > 1. **Iteration order — LR first.** Change LR before anything else (rank, α, batch, wd, β, kl_coef, epochs).
   > 2. **The primary — and overriding — diagnostic is whether M0 now hits its own declared pass criteria** after the config change. This is what determines `phenomenon_status`; 
   > 3. **A prior `sweep_status: sanity_checked` / `swept` on the milestone does not exempt it from re-tuning.** If M0 still fails to clear the milestone's own criteria (verdict is `inconclusive` / `not-established`), you **must** change hyperparameters (LR first per rule 1) and re-run — regardless of what `sweep_status` reports and regardless of whether the current config is under- or over-tuned. The pilot's pass thresholds sit well below the downstream-success bar, so "already sanity-checked" is not evidence the config is right for M0's real gate.

Mechanism milestones declare `depends_on: [M0]`, so even outside this gate the queue will not launch them before M0 completes; the gate adds the *verdict-based* branch (run status alone is not enough — a clean M0 that shows no effect must stop the pipeline, which `depends_on` cannot express).

### Phase 1.5: Mechanism-Family Routing

A committed mechanism family is a **hard precondition** for any Phase 2 code that touches an internal object (layer, head, neuron, SAE feature, weight, input feature).

**`CHOSEN_FAMILY` takes precedence over `MECHANISM_ROUTING`.** Whenever `CHOSEN_FAMILY` is set to a real family (anything other than unset / `none` / `not-applicable`), go straight to the routing flow's **Mode-B commit (Step 6) regardless of the `MECHANISM_ROUTING` value** — Step 6 commits `CHOSEN_FAMILY` (and builds the routing scaffold around it when `MECHANISM_ROUTING.md` is absent or does not list it). This is what makes all three direct-commit sources work: the first-class `MECHANISM=given` path and the `family:` pin (no Mode A ran → file may be absent → Step 6 builds it), and the `AUTO_PROCEED=false` post-mini-prompt build call (Mode A already wrote the candidates → Step 6 flips `committed`). A bare `MECHANISM_ROUTING=skip` therefore **never** silently proceeds without a committed family when `CHOSEN_FAMILY` is set. **`CHOSEN_FAMILY = not-applicable`** is the behavioral-only sentinel (a behavioral-only proposal, incl. the `MECHANISM=given` behavioral-only reproduction): treat it exactly like `MECHANISM_ROUTING = not-applicable` — write the `routing: not-applicable` stub, run no mechanism milestone — regardless of the `MECHANISM_ROUTING` value.

When `CHOSEN_FAMILY` is **unset**, behavior is gated by `MECHANISM_ROUTING`:

- **`MECHANISM_ROUTING = skip`** — assume `refine-logs/MECHANISM_ROUTING.md` already exists (or is intentionally absent for a behavioral proposal). Read it if present, otherwise log `[routing] skipped — no manifest, proceeding without routing` and continue to Phase 2.
- **`MECHANISM_ROUTING = not-applicable`** — write a stub `refine-logs/MECHANISM_ROUTING.md` containing `routing: not-applicable` and a one-line justification pulled from `FINAL_PROPOSAL.md`, then continue.
- **`MECHANISM_ROUTING = auto`** (default) — run the routing flow below.

**Routing flow (auto mode):**

1. **Use the Phase 1 parse already in memory** to identify routing inputs: chosen claim(s), the internal objects the method targets (layer / head / neuron / SAE feature / weight / input feature), the read sites, any mechanism families already named in `FINAL_PROPOSAL.md`, and the **cross-round routing hints** from `EXPERIMENT_PLAN.md` (item 5) — the `families_already_settled: [<families>]` avoid-set (Rule 1) and any `family:` pin. No new file reads needed at this step.

2. **Invoke `/mechanism-skills` via the Skill tool — this is a hard requirement, not a description of behavior.** The manifest must be derived from the catalog this skill loads at routing time, not from prior training knowledge. You are not permitted to write `MECHANISM_ROUTING.md` until you have actually read, in this turn, via the Skill tool:
   - `skills/mechanism-skills/SKILL.md` (the routing entry point listing all eleven families)
   - The `SKILL.md` of every family you intend to list as a candidate
   - The `SKILL.md` of every submethod underneath those families

   If any of these files is unread, re-invoke `/mechanism-skills` before generating candidates — do not write the manifest from memory.

   Pass `RESEARCH_DOMAIN` as the routing constraint:
   - If set to a specific tag (e.g., `mechanistic-interpretability`), pass it as `— domain: <RESEARCH_DOMAIN>` so candidates are restricted to the matching families.
   - If `auto`, do not pass `— domain:`; ask `/mechanism-skills` to infer from `FINAL_PROPOSAL.md`. On ambiguous inference, fall back to `domain: general` silently (same rule as the Constants section).

3. **Produce 2–3 candidate family/submethod combinations from the catalog.** Each candidate must use the **canonical family name** as it appears in `skills/mechanism-skills/SKILL.md` — one of: Causal Attribution, Circuit Discovery, Probing, Magnitude Analysis, Gradient Detection, Feature Dictionary Learning, Representation and Parameter Analysis, Vocabulary Projection, SHAP, Neural Feature Learning, Multi-Modal.The `chosen_family` and `candidate_paths` metadata fields must use canonical catalog names.

   **Cross-round avoid-set (Rule 1):** if `families_already_settled` (item 5) lists any families, **exclude** them from the candidate list — they were already `confirmed`/`refuted` for this behavior+direction, so re-routing to them redoes settled work. A family left `inconclusive` is *not* settled and **may** still be proposed (ideally with a refined submethod). Note the exclusion in `## Rationale`. If excluding leaves no viable catalog candidate for the direction, do not silently fall back to a settled family — surface it (the direction may itself be exhausted; a signal to pick a different direction or behavior next round).

   For each candidate, record:
   - Canonical `family/submethod`
   - `path` of the form `skills/mechanism-skills/<family>/<submethod>/SKILL.md`. Verify each path exists on disk (Glob or `ls`) before writing the manifest; if any candidate path is missing, that candidate is a hallucination — re-invoke `/mechanism-skills` and reground.
   - Planned screen → decode → verify → recover composition
   - Cost notes (GPU-hours / wall-clock estimate)
   - One-line rationale tied to a specific claim
   - Effective domain (the resolved value from step 2)

   Pure downstream analysis steps — matrix factorization, low-rank decomposition, linear algebra on already-collected effect vectors, etc. — are **not** mechanism families and must not occupy the `chosen_family` slot. They belong in the composition plan as post-processing.

4. **Write `refine-logs/MECHANISM_ROUTING.md`** with: inputs read, candidate list (mark #1 as recommended), composition plan with cost notes, and the routing rationale. **The file MUST contain an explicit `committed:` line in its top metadata block** (see template below) — Mode A writes `committed: false`, Mode B (`CHOSEN_FAMILY` set) overwrites it to `committed: true`. The `/auto` orchestrator's four-branch resume protocol keys directly off this string, so omitting the line will break resume.

   **Required template for `refine-logs/MECHANISM_ROUTING.md`:**

   ```markdown
   # Mechanism Routing

   <!-- Metadata block (parsed by /auto orchestrator resume check). -->
   committed: <false|true>
   chosen_family: <canonical family/submethod | none>
   chosen_idea_title: <title | n/a>
   effective_domain: <resolved domain>
   candidate_paths:
     - skills/mechanism-skills/<family>/<submethod>/SKILL.md
     - skills/mechanism-skills/<family>/<submethod>/SKILL.md

   ## Candidates

   1. **[recommended]** <canonical family/submethod> — <rationale>
      - path: skills/mechanism-skills/<family>/<submethod>/SKILL.md
   2. <canonical family/submethod> — <rationale>
      - path: skills/mechanism-skills/<family>/<submethod>/SKILL.md
   3. <canonical family/submethod> — <rationale>
      - path: skills/mechanism-skills/<family>/<submethod>/SKILL.md

   ## Composition plan
   <screen → decode → verify → recover, with cost notes. Downstream analysis steps (decomposition, probing aggregation, …) belong here, not in the candidate slot.>

   ## Plan reconciliation
   <!-- Written by Step 7 once a family is committed. One row per method_sensitive field declared on the intervention milestone(s). -->
   - n_pairs: plan=<X> → <matches | re-bound <Y> — <why the committed submethod needs it> | conflict — <why this cannot be satisfied without changing the plan's scientific intent>>
   - sites: plan=<...> → <matches | re-bound <...> — <why> | conflict — <why>>
   - metric: plan=<...> → <matches | re-bound <...> — <why> | conflict — <why>>
   - gpu_hours: plan~<X> → revised ~<Y> — <what in the committed submethod's compute profile drives the change; may go up OR down, e.g. a gradient-based approximation adds a backward pass but avoids per-site forward passes, while exhaustive activation patching scales with the number of patched sites>
   reconciliation_status: <ok | escalate | n/a>   <!-- n/a when the milestone(s) declared no method_sensitive fields (incl. the reproduction combo, which pins them exact); escalate iff any field is `conflict`; else ok -->

   ## Rationale
   <why #1 is recommended; if aligned_with_tagging: no, explain why the prior was over-ruled>
   ```

   For the `routing: not-applicable` short-circuit, replace the metadata block with `routing: not-applicable` and `committed: true` (a behavioral-only proposal is "committed" to having no mechanism family) and keep a one-line justification under `## Rationale`.

5. **If `CHOSEN_FAMILY` is unset** — branch on `AUTO_PROCEED`:
   - `true` (default): auto-select the `[recommended]` candidate, flip `committed: true`, continue into Phase 2 in the same call. No mini-prompt. Log `[routing] auto-selected family=<name> submethod=<name>`.
   - `false`: write `committed: false`, return to caller (Mode A complete). Caller (`/auto` orchestrator or standalone CLI) prompts the user then re-enters with `CHOSEN_FAMILY` set.

6. **If `CHOSEN_FAMILY` is set (Mode B — build)** — commit that family. Two sub-cases:
   - **`MECHANISM_ROUTING.md` exists and already lists `CHOSEN_FAMILY` as a candidate** (the `AUTO_PROCEED=false` mini-prompt path, where Mode A ran first) — locate that candidate, **overwrite the metadata line `committed: false` to `committed: true`** (and set `chosen_family:` to it), and proceed to Phase 2.
   - **`MECHANISM_ROUTING.md` is missing, or exists but does not list `CHOSEN_FAMILY`** (the first-class `MECHANISM=given` path and the cross-round `family:` pin path — no Mode A ran, so the file may be absent or its auto-candidates may not include the user's pick) — **do not auto-select #1 and do not silently drop the user's choice.** Run steps 1–4 to build the routing scaffold (composition plan, `candidate_paths`, rationale) for `CHOSEN_FAMILY` specifically: **load `/mechanism-skills` and map `CHOSEN_FAMILY` to the nearest canonical catalog family/submethod** — the user may have written a free-text method name (e.g. `activation patching` → `Causal Attribution / activation patching`; `SAE` → `Feature Dictionary Learning / sparse-autoencoder`), so resolve it semantically against the catalog rather than requiring an exact string. If it resolves to a catalog entry, write `MECHANISM_ROUTING.md` with the **canonical** name as the sole committed candidate (`committed: true`, `chosen_family: <canonical name>`). If it plausibly maps to **no** catalog family/submethod, HALT with `[routing] CHOSEN_FAMILY="<x>" maps to no /mechanism-skills family/submethod — name a supported mechanism method in task.md`. This is the "commit the named family directly" behavior the `CHOSEN_FAMILY` sources note describes.

   In both sub-cases log `[routing] committed family=<name> submethod=<name>` and proceed to Step 7 (Plan reconciliation) then Phase 2.

   **`CHOSEN_FAMILY` sources.** `CHOSEN_FAMILY` is forwarded by `/auto`'s orchestrator from one of three places: **(1) `MECHANISM=given`** — the user named the mechanism method/family in `task.md` and the claim stage stamped it as `chosen_mechanism` in `FINAL_PROPOSAL.md` / `EXPERIMENT_PLAN.md` (this is the first-class mechanism-given path: no routing, no mini-prompt); **(2)** the `AUTO_PROCEED=false` family mini-prompt (`MECHANISM=discovery`); **(3)** an explicit `family:` pin in `task.md` (the cross-round Rule-2 path under `MECHANISM=discovery` — see `/auto` → Global Exploration Memory). Mode B treats all three identically: **commit the named family** (per Step 6 — auto-selection of a *different* family never happens; the scaffold is built around `CHOSEN_FAMILY`, not re-routed away from it). A pinned family that is itself in `families_already_settled` is **fine** — the orchestrator already confirmed the re-run with the user (`honor-pin`) before forwarding — so commit it rather than blocking.

7. **Plan reconciliation (runs whenever a family becomes committed — the auto-select in step 5 or the Mode B commit in step 6; skip for `routing: not-applicable`).** Now that a concrete submethod is locked, reconcile it against the fields the claim stage could only estimate before the method was known. Read the just-loaded submethod `SKILL.md` (already in context from step 2) for its real requirements, then for **every `method_sensitive` field** declared on the intervention milestone(s) in `EXPERIMENT_PLAN.md`, compare the plan's value to what this submethod needs and write the verdict into the `## Plan reconciliation` section of `MECHANISM_ROUTING.md`:
   - **`matches`** — the plan's value is fine for this submethod. Nothing else to do.
   - **`re-bound <new value> — <why>`** — the submethod needs a different value that still serves the milestone's *scientific intent* (e.g. attribution-patching's gradient estimate needs more `n_pairs` for a stable estimate; a method needs a different read `site`; the GPU-hours estimate moves up or down because the committed submethod's compute profile differs from the generic pre-routing estimate). Record the new value here; **do not edit `EXPERIMENT_PLAN.md`** (the plan stays the claim stage's audit reference — the realized value is captured downstream as planned-vs-actual in Phase 5). Phase 2 implements to the re-bound value; the Phase 4 gate displays the re-bound GPU-hours.
   - **`conflict — <why>`** — the submethod **cannot** satisfy the field without changing the plan's scientific intent (e.g. it structurally cannot measure the planned `metric`, or requires `sites` the plan explicitly excluded). This is a **plan defect, not a routing re-bind**, and is out of this stage's authority (this skill never rewrites the claim-authored plan). Set `reconciliation_status: escalate` and **stop before Phase 2** (do not build). The orchestrator surfaces this as a **Round-End Decision** (`ended-needs-decision`, never a crash halt and never an auto-rewrite of the plan), and the plan owner (the user) repairs the conflicting field in `EXPERIMENT_PLAN.md` — or picks a fitting submethod, or re-scopes the claim — and re-runs. Do **not** silently swap the metric/sites to make the method fit.

   **Resource-Fidelity Harness override (when active):** `method_sensitive` fields are absent under `resource_fidelity: strict`, so there is nothing to re-bind — the values are pinned exact. If the committed submethod genuinely cannot run at those pinned values, that is a `conflict` → HALT (never downscale), consistent with the harness.

   Log `[reconciliation] status=<ok|escalate> — re-bound: <fields or none>`. When `reconciliation_status: ok`, continue to Phase 2.

**Hard requirement**: before Phase 2 implements any code that touches an internal object, `refine-logs/MECHANISM_ROUTING.md` must exist and contain a committed candidate (or `routing: not-applicable`) **with a completed `## Plan reconciliation` whose `reconciliation_status: ok`** (or `n/a` when no `method_sensitive` fields were declared). If absent, fall back to `MECHANISM_ROUTING=auto` and re-run this phase; if `reconciliation_status: escalate`, HALT per Step 7.

### Phase 2: Implement Experiment Code

**Data precondition** — every data loader / split / labeling / sample-size choice obeys the four Data Rules already loaded in Phase 1 (`skills/data-rule/SKILL.md`). Re-read that file if it has fallen out of context.

**Routing precondition** — `refine-logs/MECHANISM_ROUTING.md` was produced by Phase 1.5; load the committed candidate and use its listed `scripts/` and `references/` as reference material. Do not copy verbatim. If the manifest says `routing: not-applicable`, skip mechanism-specific scaffolding.

**If `BASE_REPO` is set** — clone the repo first:
```bash
git clone <BASE_REPO> base_repo/
# Read the repo's README, understand its structure, find entry points
# Implement experiments by modifying/extending this codebase
```

**Script granularity** — default to one script per dispatch unit (model × dataset), not per milestone. Loads the model once, keeps activations in memory across phases, makes Phase 4.A trivially `nohup ... & wait`-parallel. As a reference pattern, a single ~400-line script that runs Block 1+2+3 together keeps activations resident across phases. Only split when milestones need different runtime stacks (e.g., one needs `vllm`, another `transformers` hooks) or share < 30% code.

For each dispatch unit (in plan order), write the experiment script(s):

1. **Check existing code** — scan the project (or cloned `base_repo/`) for existing experiment scripts, model code, data loaders. Reuse as much as possible.

2. **Implement missing pieces:**
   - Training scripts with proper argparse (all hyperparameters configurable)
   - Evaluation scripts computing the specified metrics
   - Data loading / preprocessing if needed
   - Baseline implementations if not already present
   - Fixed random seeds for reproducibility
   - Results saved to JSON/CSV for later analysis
   - Proper logging (wandb if configured in CLAUDE.md)

3. **Follow the plan's run order** — within a single monolithic script, the milestone sequence becomes function-call order (sanity sub-routine → baseline → main → ablations). Across scripts, dispatch order still matches the plan.

4. **Self-review before deploying:**
   - Are all hyperparameters from EXPERIMENT_PLAN.md reflected in argparse?
   - Is the random seed fixed and controllable?
   - Are results saved in a parseable format (JSON/CSV)?
   - Does the code match FINAL_PROPOSAL.md's method description?
   - Could two of the scripts you just wrote be merged into one `--mode {a,b}` script without losing clarity? (If yes, merge them — see granularity guidance above.)

### Phase 2.5: Cross-Model Code Review (when CODE_REVIEW = true)

**Skip this step if `CODE_REVIEW` is `false`.**

Before deploying, send the experiment code to the external LLM reviewer for review:

```
mcp__llm-chat__chat:
  prompt: |
    Review the following experiment implementation for correctness.

    ## Experiment Plan:
    [paste key sections from EXPERIMENT_PLAN.md]

    ## Method Description:
    [paste from FINAL_PROPOSAL.md]

    ## Implementation:
    [paste the experiment scripts]

    Check for:
    1. Does the code correctly implement the method described in the proposal?
    2. Are all hyperparameters from the plan reflected in the code?
    3. Are there any logic bugs (wrong loss function, incorrect data split, missing eval)?
    4. Is the evaluation metric computed correctly?
    5. **CRITICAL: Does evaluation use the dataset's actual ground truth labels — NOT another model's output as ground truth?** This is a common and severe bug.
    6. **Does the scorer match the answer format?** Strict exact-match on free-form QA, or a 0.5 binarization on a near-zero-variance label, will collapse the label distribution. If the experiment scores LLM-generated answers, the scorer must be chosen to match the answer format (e.g., multiple-choice → exact-match on the option token; short free-form → normalized exact-match or token-F1; long free-form → LLM-judge or substring containment with a documented rubric). Confirm a pilot **label-floor check** has been run: on a held-out 50–100 example slice, the score distribution should not collapse to a near-constant (variance ≥ 0.05 on a [0,1] metric). A collapsed pilot is **not** a normal halt — it is a **Round-End Decision** (`ended-needs-decision (experiment: scorer-invalid)`): stop before the full run, do **not** auto-swap in another scorer (choosing the scorer that matches the answer format is a judgment call — an auto-swap risks trading one bad scorer for another), and surface the collapse evidence (measured variance, the scorer/answer-format mismatch) plus the recommended scorer fix so the user fixes it and re-runs. See `auto/SKILL.md` → "Round-End Decision".
    7. Any potential issues (OOM risk, numerical instability, missing seeds)?

    For each issue found, specify: CRITICAL / MAJOR / MINOR and the exact fix.
```

**On review results:**
- **No CRITICAL issues** → proceed to Phase 3
- **CRITICAL issues found** → fix them, then re-submit for review (max 2 rounds)
- **llm-chat MCP unavailable** → skip silently, proceed to Phase 3 (graceful degradation)

### Phase 3: Sanity Check (if SANITY_FIRST = true)

**GPU pinning.** If `GPU_ID` is not `auto`, pass `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the first positional arg to every `/run-experiment` invocation from this phase onward (sanity below, the full suite in Phase 4, and any auto-debug re-runs). `/run-experiment` itself parses this leading positional and exports it as an env var in the experiment subprocess. Record the effective `CUDA_VISIBLE_DEVICES` in each run's `run.sh` so reproductions land on the same devices.

Before deploying the full experiment suite, run the sanity-stage experiment:

```
/run-experiment CUDA_VISIBLE_DEVICES=<GPU_ID> [sanity experiment command]
```

(When `GPU_ID = auto`, drop the `CUDA_VISIBLE_DEVICES=...` positional and let the launcher decide.)

Wait for completion. Verify:
- Training loop runs without errors
- Metrics are computed and saved correctly
- GPU memory usage is within bounds
- Output format matches expectations

If sanity fails → **auto-debug before giving up** (max 3 attempts):

1. **Read the error** — parse traceback, stderr, and log files
2. **Diagnose** — classify the failure:
   - OOM → reduce batch size or enable gradient checkpointing
   - ImportError → install missing package
   - FileNotFoundError → fix path or download data
   - CUDA error → check GPU availability, reduce model size
   - NaN/divergence → reduce learning rate, check data preprocessing

   > **Resource-Fidelity Harness override (when active):** the "reduce model size" remedy above is **forbidden**, and so is any data subsetting. Resolve OOM by the harness's **auto-scale-up** path — batch size ↓ / gradient accumulation / gradient checkpointing / sequence chunking, plus auto-adding free GPUs with sharding (auto-converting a single-GPU script to `device_map="auto"` / FSDP / offload, equivalence-checked on a fit-on-one-GPU proxy slice) up to `OOM_MAX_GPUS`. Only after the cap (or no free GPU) and offload are exhausted, HALT and report rather than swapping in a smaller model or trimming the data. (See "Resource-Fidelity Harness" rule 4.)
3. **Fix and re-run** — apply the fix, re-run sanity
4. **Attempt 2+ still failing? → Call in Codex rescue** (if Codex plugin installed):
   Before the next retry, invoke `/codex:rescue` to get a second opinion on the root cause. Codex independently reads the code and error logs — it may spot issues Claude missed (wrong tensor shapes, subtle import shadowing, config mismatches, etc.). Apply its suggested fix, then re-run.
   - If `/codex:rescue` is not available (plugin not installed), continue with Claude's own diagnosis
5. **Still failing after 3 attempts?** → stop, report the failure with all attempted fixes and error logs. Do not proceed with broken code.

> Never give up on the first failure. Most experiment crashes are fixable without human intervention.

### Phase 4: Deploy Full Experiments

Deploy experiments following the plan's milestone order. Carry forward the GPU pinning from Phase 3 — every command below gets `CUDA_VISIBLE_DEVICES=<GPU_ID>` as the leading positional arg to `/run-experiment` when `GPU_ID` is not `auto`:

```
/run-experiment CUDA_VISIBLE_DEVICES=<GPU_ID> [experiment commands]
```

#### Phase 4.0: Route by milestone size and dependencies

Before dispatching, classify **each milestone** into one of two dispatch paths:

| Condition (any one triggers) | Dispatch path |
|---|---|
| Milestone has ≥ 10 runs **OR** declares `depends_on:` in `EXPERIMENT_PLAN.md` **OR** uses a grid expansion (`seeds: [...]` × `params: [...]`) **OR** is a multi-seed sweep (≥ 3 seeds × ≥ 3 configurations) | **`/experiment-queue`** (this milestone) |
| All other milestones (≤ 5 ad-hoc runs, no dependencies, no grid) | **`/run-experiment`** (this milestone, one dispatch per run) |
| 6–9 runs, no dependencies | **`/experiment-queue` recommended; `/run-experiment` acceptable** — emit warning `[phase-4] milestone <name> has <N> runs (6-9): prefer /experiment-queue for OOM safety, falling back to /run-experiment per MAX_PARALLEL_RUNS=<n>`. Default behavior: still use `/run-experiment` (backward compatible). To force queue, set `BATCH_DISPATCH=queue` on the CLI. |

`BATCH_DISPATCH` knob (optional, forwarded from `/auto` or default `auto`):
- `auto` (default) — follow the table above.
- `queue` — force every milestone to `/experiment-queue` regardless of size.
- `direct` — force every milestone to `/run-experiment`; emit a `[phase-4] BATCH_DISPATCH=direct overriding the recommended /experiment-queue for <N>-run milestone — OOM safety net disabled` warning if any milestone would have triggered the queue rule. Use only when intentionally bypassing the queue (e.g., debugging the scheduler itself).

Log the routing decision per milestone: `[phase-4] milestone=<name> runs=<N> deps=<depends_on or none> → /<run-experiment|experiment-queue>`.

#### Phase 4.A: Direct dispatch (small milestones — `/run-experiment` path)

Launch all parallel runs of the milestone in ONE Bash call using `nohup ... & wait` (template in `/run-experiment` Step 4 "Parallel runs"). Shell `wait` joins direct children only — do not use `pgrep -f '<script>.py'` (it self-matches the polling bash's own cmdline). Remote/SSH: filter `screen -ls` by session name. After `wait` returns, call `/monitor-experiment` to finalize each `runs/<run-id>/cost.json`.

#### Phase 4.B: Queue dispatch (large milestones — `/experiment-queue` path)

For each milestone routed to the queue path:

1. **Build the manifest.** Derive a YAML grid spec from `EXPERIMENT_PLAN.md`'s milestone block. If the plan declares parameters as lists (e.g., `seeds: [42, 200, 201]`, `n_hidden: [64, 128, 256]`), pass them as `grid:` axes; otherwise expand each run as a single `jobs:` entry. Carry forward:
   - `gpus:` from `GPU_ID` (split into list; `auto` → omit and let the queue auto-discover)
   - `max_parallel:` from `MAX_PARALLEL_RUNS`
   - `gpu_free_threshold_mib: 500` (queue default; raise via plan if known shared)
   - `oom_retry: {delay: 120, max_attempts: 3}` (queue defaults)
   - `cwd:` and `conda:` from CLAUDE.md / environment
   - `depends_on:` from the plan, naming the upstream milestone(s)

2. **Invoke `/experiment-queue`** with the manifest:
   ```
   /experiment-queue <path-to-manifest.json or grid_spec.yaml>
   ```

3. **Wait for batch completion.** Poll `$REMOTE_RUN_DIR/queue_state.json` until every job is `completed` or `stuck` (see `/experiment-queue` Step 4 for the `jq` one-liner). Do NOT proceed to Phase 5 with `stuck` jobs unresolved — surface them in the deploy report.

4. **Finalize per-run cost manifests.** For each `completed` job in `queue_state.json`, invoke `/monitor-experiment` on its run ID to write `runs/<job-id>/cost.json` (Step 3.6 in monitor — see "Coordination with `cost.json` and `queue_state.json`" in `/experiment-queue` for why this split exists).

5. **Continue to Phase 5** with the union of all milestones' results.

> **Multi-GPU partitioning.** When `GPU_ID` lists multiple devices and `MAX_PARALLEL_RUNS > 1`, split the device list across concurrent runs (one disjoint subset per run). Example: `GPU_ID=4,5,6,7` with `MAX_PARALLEL_RUNS=2` → run A gets `CUDA_VISIBLE_DEVICES=4,5`, run B gets `CUDA_VISIBLE_DEVICES=6,7`. Do not co-schedule two runs on the same device unless memory measurements confirm it fits.
>
> **Auto-clamp when fewer devices than parallelism.** If `GPU_ID` is an explicit list with `len(GPU_ID) < MAX_PARALLEL_RUNS` (e.g., `GPU_ID=0` + default `MAX_PARALLEL_RUNS=4`), automatically lower the effective parallelism to `len(GPU_ID)` rather than co-scheduling — multiple runs on one GPU usually OOM. Log `[gpu-clamp] MAX_PARALLEL_RUNS lowered from <orig> to <len(GPU_ID)> — only <len(GPU_ID)> device(s) requested via GPU_ID`. Skip the clamp when `GPU_ID = auto` (the launcher decides).

**🚦 Experiment Gate (before deploy).** Branch on `AUTO_DEPLOY` × `AUTO_PROCEED`:

| `AUTO_DEPLOY` | `AUTO_PROCEED` | Action |
|---|---|---|
| `true`  | `true`  | Deploy silently. Log `[experiment-gate] proceeded — AUTO_DEPLOY=true, AUTO_PROCEED=true`. |
| `true`  | `false` | Deploy silently — `AUTO_DEPLOY=true` is treated as standing approval. Log `[experiment-gate] proceeded — AUTO_DEPLOY=true overrides AUTO_PROCEED=false`. |
| `false` | `true`  | Deploy silently — `AUTO_PROCEED=true` is full-auto and overrides `AUTO_DEPLOY=false`. Log `[experiment-gate] proceeded — AUTO_PROCEED=true overrides AUTO_DEPLOY=false (full-auto mode)`. (Print the checkpoint summary below into the deploy log for the human reader, but do **not** block.) |
| `false` | `false` | Call `AskUserQuestion` with three options — **approve** / **narrow scope** / **abort** — and block until the user answers. On `narrow scope`, ask which milestones to keep, then re-enter the gate. On `abort`, stop the skill with `[experiment-gate] aborted by user`. |

The checkpoint summary (logged in every cell for the human reader; only blocks in the `AUTO_DEPLOY=false AND AUTO_PROCEED=false` cell via `AskUserQuestion`):

```
🔧 Code implementation complete. Ready to deploy:

Milestone 0 (sanity): [status — passed/pending]
Milestone 1 (baseline): [N experiments, ~X GPU-hours]
Milestone 2 (main method): [N experiments, ~X GPU-hours]
Milestone 3 (ablations): [N experiments, ~X GPU-hours]

Total estimated: ~X GPU-hours on [N] GPUs

Deploy now? Or review the code first?
```

> **Use reconciled cost.** The GPU-hours shown here must be the **post-reconciliation** estimate (the `gpu_hours: ... → revised ~Y` value from `MECHANISM_ROUTING.md`'s `## Plan reconciliation`, Phase 1.5 Step 7), not the stale plan figure — the committed submethod may cost more or less than the claim stage could estimate before the method was known. When no field was re-bound, the plan figure stands.

> Implementation note: `AskUserQuestion` has no timeout. Only call it in the `AUTO_DEPLOY=false AND AUTO_PROCEED=false` cell so unattended overnight runs cannot deadlock here.

### Phase 5: Collect Initial Results

As experiments complete:

1. **Parse output files** (JSON/CSV/logs) for key metrics
2. **Training quality check** — if W&B data is available (CLAUDE.md has `wandb: true` and `wandb_project`), invoke `/training-check` to detect NaN, loss divergence, plateaus, or overfitting. If W&B is not configured, skip silently.
3. **Update `refine-logs/EXPERIMENT_TRACKER.md`** — `EXPERIMENT_TRACKER.md` is **owned by `/auto-claim` Phase 4.5** (it writes the initial plan-level table with every row at `Status: pending`). This phase **updates rows in place**: flip each plan run's `Status` column (`pending` → `running` → `done` / `failed`) and fill in `Notes` / result columns. Do **not** overwrite the file wholesale — the plan rows from Phase 4.5 are the audit trail. New rows are only appended by Phase 5.6 when ablations get planned post-baseline; never by Phase 5 itself.

   **Supersede on re-task (no parallel narratives).** When this run is a **re-task** of a rejected earlier attempt (the orchestrator re-dispatched under a corrected requirement, or a resume redoing a milestone), do **not** leave the old result standing beside the new one. Flip the milestone's tracker row to the **new** run's terminal status in place, and in `EXPERIMENT_RESULTS.md` **rewrite that milestone's section in place**, marking the prior narrative `superseded: <old run-id>` (one line naming what changed and why). The reader — and the downstream ledger — must see exactly one current narrative per milestone. Appending a second, contradictory result section is the dirty-data failure this rule exists to prevent.

   **Update cadence**: flip Status to `running` **before launch** and `done`/`failed` **immediately after each run returns** — never batch updates to the end of Phase 5. Makes hang detection possible (a row stuck on `running` past 2× ETA is the signal).
4. **Check success criteria** from EXPERIMENT_PLAN.md — did each experiment meet its bar?
5. **Record the data actually used** — for each claim/block, the realized `used_n` (the number of examples/pairs the runs actually consumed), reconciled against the plan's `available_n` and *planned* `used_n` from EXPERIMENT_PLAN.md. Carry over `provenance`/`source`; flag and correct them only if the realized data differed from plan, and note any subsetting. **Resource-Fidelity Harness (when active):** realized `used_n` MUST equal the specified `used_n` — any shortfall means the run is **failed**, not `done`; record it as failed and surface it rather than entering a subset note. (The "Subset note" column should read `—` for every row under the active harness; a non-empty subset note is a harness violation.)

   **Method-sensitive re-binds** — when Phase 1.5 Step 7 re-bound a `method_sensitive` field (e.g. `n_pairs`), the *planned* value in `EXPERIMENT_PLAN.md` and the value the runs actually used will legitimately differ. Record both as planned-vs-actual exactly like `used_n`: the realized figure goes in the results, and a short note points to `MECHANISM_ROUTING.md`'s `## Plan reconciliation` for why (e.g. `n_pairs: planned 200 / actual 400 — re-bound for attribution-patching, see MECHANISM_ROUTING.md`). This is the audit trail for the re-bind; the plan file itself is never edited.

   **Power-Fidelity check (cost-aware combinations only; `UNDERPOWER != off`; skipped under `resource_fidelity: strict`).** A weak main-experiment verdict from a cheap run can be an under-power artifact, not a real negative. For each claim whose verdict is `not-supported` / `partial` / null, compare realized vs *planned* scale (the `used_n` reconciliation above, plus seeds and grid/checkpoint points).

   First separate an **execution shortfall** from a genuine under-power situation: if the planned grid/scale was simply **not fully run** though it was feasible (the run stopped early, swept 2 of 8 planned α levels, or skipped planned seeds/points with budget and time to spare), that milestone is **incomplete, not negative** — treat it like an under-`used_n` run (recorded `failed`, not `done`, per the `used_n` rule) and **complete the planned scale first**: re-run the missing grid points / seeds to realize the plan as written, *before* assigning any verdict. Do **not** report a weak verdict off an incomplete plan. This is the in-stage form of the reject-and-re-task "realize plan A as written" case (`/auto` Key Rules); it edits nothing in the plan — it just finishes running it.

   Only when the plan **was** run as written but its scale is still genuinely under-powered (or completing it is infeasible on the available resources): set `suspected_under_power: true` for that claim in `EXPERIMENT_RESULTS.md` with the X/Y figures (`used_n X/Y, seeds A/B, grid P/Q`), and surface it in the return so `/auto` can run its Power-Fidelity Gate (`UNDERPOWER=tag` → tag the weak verdict **provisional** + proceed; `stop` → Round-End; under `AUTO_PROCEED=false`, ask: full re-run / targeted-milestone re-run / accept demo-scale). Do **not** silently present an under-powered null as a settled negative. (A weak verdict from a *full-scale* run is a genuine negative — not flagged.)
6. **Write initial results summary:**

```markdown
# Initial Experiment Results

**Date**: [today]
**Plan**: refine-logs/EXPERIMENT_PLAN.md

## Data Actually Used
Per claim/block, reconciled against the *planned* data in EXPERIMENT_PLAN.md (provenance: `existing` used as-is / `adapted` from existing / `constructed` from scratch):

| Claim/Block | Provenance | Source | Available N (total) | Used N (actual) | Subset note (if used < available) |
|-------------|-----------|--------|---------------------|-----------------|-----------------------------------|
| C1 / Block 1 | existing | [name] | [N] | [N] | [how/why subsetted, or —] |

## Results by Milestone

### M0: Sanity — PASSED
- [result]

### M1: Baselines
| Run | System | Key Metric | Status |
|-----|--------|-----------|--------|
| R001 | baseline_1 | X.XX | DONE |

### M2: Main Method
| Run | System | Key Metric | Status |
|-----|--------|-----------|--------|
| R003 | our_method | X.XX | DONE |

### M3: Ablations
...

## Summary
- [X/Y] must-run experiments completed
- Main result: [positive/negative/inconclusive]
- Ready for /auto-verify: [YES/NO]

## Next Step
→ /auto-verify
```

### Phase 5.5: Write Compact Log (when COMPACT = true)

**Skip entirely if `COMPACT` is `false`.**

Append each completed experiment to `EXPERIMENT_LOG.md`:

```markdown
## [Run ID] — [timestamp]
- **System**: [method name]
- **Config**: [key hyperparameters]
- **Result**: [primary metric = X.XX]
- **Verdict**: [positive / negative / inconclusive]
- **Reproduce**: `python train.py --config configs/run_id.yaml --seed 42`
```

This structured log survives session recovery — downstream skills read it instead of parsing screen output.

### Phase 5.6: Auto Ablation Planning

After main experiments (M2) complete with positive results, invoke `/ablation-planner` to design ablation studies:

- Read the main results and method description
- Generate a claim-driven ablation plan: which components to remove, what to compare, expected outcomes
- Append ablation blocks to `refine-logs/EXPERIMENT_PLAN.md` and `refine-logs/EXPERIMENT_TRACKER.md`
- If main results are negative or inconclusive, skip ablation planning and note in the summary

If `/ablation-planner` is not available, skip silently — the existing EXPERIMENT_PLAN.md ablation blocks (if any) remain unchanged.

### Phase 6: Handoff

Present final status:

```
🔬 Experiment bridge complete:
- Implemented: [N] experiment scripts
- Deployed: [N] experiments on [M] GPUs
- GPU devices: [effective CUDA_VISIBLE_DEVICES used, or "auto (inherited from launcher)" when GPU_ID=auto]
- Completed: [X/Y] must-run, [A/B] nice-to-have
- Main result: [one sentence]

Results: refine-logs/EXPERIMENT_RESULTS.md
Tracker: refine-logs/EXPERIMENT_TRACKER.md

Next step: /auto-verify to stress-test the passed claims.
```

## Output Directory Naming

Every run from this skill writes to a dedicated subdirectory under `runs/`. Use the format:

```
runs/<run_id>_<short_purpose>/
```

- `<run_id>` — the Run ID from the `Quick-Glance Run Order` table in `EXPERIMENT_PLAN.md` (e.g., `A1`, `B1`, `C1`). Keeps the directory cross-referenceable with the plan, tracker, and results tables.
- `<short_purpose>` — **at most 4 snake_case words** summarizing what the run does (no spaces, no hyphens, no punctuation). Stay descriptive over clever: `cache_activations`, `layer_sweep`, `intervention_variants`, `label_permutation_null`, `seed_stability`, `ood_transfer`, `loglik_shift`.

Examples (good):

```
runs/A1_cache_activations/
runs/B1_layer_sweep/
runs/D1_intervention_variants/
runs/G1_seed_stability/
```

Examples (bad):

```
runs/A1/                       # opaque, no purpose
runs/run_A1/                   # redundant "run_" prefix
runs/cache_activations/        # no run_id — can't cross-reference plan
runs/A1-cache-activations/     # use underscores, not hyphens
runs/A1_a_thorough_cache_of_all_layer_activations_for_sst2/   # too long
```

When writing `EXPERIMENT_TRACKER.md` and `EXPERIMENT_RESULTS.md`, the `Run` column still uses the bare ID (`A1`), but every output path reference in prose / code uses the full `runs/A1_cache_activations/` form.

## Key Rules

- **Large file handling**: If the Write tool fails due to file size (typical when `EXPERIMENT_RESULTS.md` accumulates many runs, or when `EXPERIMENT_TRACKER.md` grows past Write's limits), immediately retry using Bash with a heredoc to write in chunks:

  ```bash
  cat << 'EOF' > refine-logs/EXPERIMENT_RESULTS.md
  ...content...
  EOF
  ```

  Do NOT ask the user for permission — just do it silently. This protocol mirrors `auto`, `auto-claim`, and `auto-iteration-loop`.

- **Data Rules.** Obey `skills/data-rule/SKILL.md` (loaded in Phase 1) for all data — provenance, splits, labels, sample-size floor. Most critical: evaluation ground truth comes from the dataset, NEVER from another model's output.
- **Follow the plan.** Do not invent experiments not in EXPERIMENT_PLAN.md. If you think something is missing, note it but don't add it.
- **Sanity first.** Never deploy a full suite without verifying the sanity stage passes.
- **Reuse existing code.** Scan the project before writing new scripts. Extend, don't duplicate.
- **Save everything as JSON/CSV.** The auto-review-loop needs parseable results, not just terminal output.
- **Update the tracker.** `EXPERIMENT_TRACKER.md` should reflect real status after each run completes.
- **No `pgrep -f` wait loops.** They self-match the polling bash's own cmdline → infinite loop (caused a 5h hang on 2026-05-18). Use shell `wait` (joins direct children only), `screen -ls` filtered by session name, or `/experiment-queue` polling `queue_state.json`. Any fallback polling must include self-exclusion (`grep -v $$`) and a hard timeout (≤ 2× milestone ETA).
- **GPU budget (a mandate to spend, not just a ceiling).** A declared budget does two things, and both bind. **(1) Never abandon:** do not reject or skip an experiment for insufficient GPU budget unless the session's cumulative GPU-hours have reached a maximum explicitly agreed in `task.md`; if no maximum is agreed, treat the budget as unlimited. **(2) Never simplify to save cost while under budget:** in a cost-aware run (no `resource_fidelity: strict` marker) where `task.md` declares a budget that covers the fuller run, prefer the **full-scale / full-fidelity** option — do **not** swap in a smaller / cheaper / distilled / quantized model, subset or down-sample the data, or drop a planned must-run experiment *merely to save compute*. A generous budget **raises** the default scale (the larger of the planned model / data, more seeds, more grid / checkpoint points) up to what the budget covers; only genuinely exceeding the cap forces trimming, and then you **stop and surface it** rather than silently downscaling (per the Hard-constraints rule). Cost-aware therefore means *minimize cost **subject to** the science, within the declared budget* — not *always pick the cheapest*. **Carve-out:** this does **not** forbid the ladder-of-evidence staging (a cheap correlational / attribution screen *before* the causal confirmation) — that is a scientific design choice and each rung still runs at its proper scale; what's forbidden is shrinking the model / trimming the data / cutting must-run runs to save cost. Still track GPU-hours for the Phase 6 summary.
- **Vast.ai lifecycle.** If using vast.ai instances, destroy them after all experiments complete and results are downloaded. Running instances cost money every second — don't leave them idle. Use `/vast-gpu destroy` or `/vast-gpu destroy-all` when done.
- **Modal lifecycle.** If using `gpu: modal`, no cleanup is needed — Modal auto-scales to zero after each run. But always show cost estimates before running and verify the spending limit is set at https://modal.com/settings (NEVER through CLI).

## Composing with Other Skills

```
/auto-claim "direction"              ← Workflow 1: find + refine + plan
/mechanism-skills                    ← mechanism family + submethod routing — folded into this skill's Phase 1.5 (callable standalone for routing-only use; otherwise no need to chain separately)
/auto-experiment                     ← you are here (Workflow 1.5: route + implement + deploy)
/auto-verify                         ← Workflow 1.75: stress-test passed claims
/auto-iteration-loop "direction"     ← Workflow 2: review + iterate

Or use /auto for the autonomous idea → routing → experiments → verify → iteration chain.
```

