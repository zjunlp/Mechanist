---
name: mechanism-audit
description: "Audit the **mechanistic experiment rigor** for a specific claim. Catalogue currently has six slots A–F: A (steering coefficient sweep) is implemented; B–F are reserved for future checks (direction extraction quality, site/layer selection, n_effective sufficiency, probe-vs-causal disentanglement, intervention scope). Uses cross-model review (external LLM reviewer via llm-chat MCP). Complementary to `/experiment-audit` (which audits evaluation methodology, not mechanism tuning). The output `overall_verdict` (PASS/WARN/FAIL/N/A) is THIS claim's mechanism-rigor verdict — i.e., whether the interpretability mechanism backing this claim was tuned with the necessary controls. Returns N/A when the claim's experiment does not use any mechanism intervention (e.g., pure dataset evaluation). Does NOT judge methodology honesty (that is `/experiment-audit`'s job) or semantic claim support (that is `/result-to-claim`'s job)."
argument-hint: <experiment-dir-or-results-path> — claim <Cx> [— output-dir <path>]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__llm-chat__chat
---

# Mechanism Audit: Per-Claim Cross-Model Mechanism-Rigor Verification

Audit the mechanistic-experiment rigor for one claim: **$ARGUMENTS**

## Why This Exists

`/experiment-audit` audits **evaluation methodology** — did the experiment honestly measure what it claims to measure (GT provenance, score normalization, file existence, scope, eval type). It treats the interpretability machinery as a black box: if the pipeline runs and the numbers are reported faithfully, it passes. That leaves an entire failure surface unchecked — the **mechanism itself** can be mis-extracted, mis-sited, mis-scaled, or mis-applied, and the methodology audit will still wave the result through.

This skill is the **mechanistic-interpretability domain audit**. It asks a different question from `/experiment-audit`: *given that the evaluation was clean, was the mechanism under test actually exercised in a regime where its effect can be measured and trusted?* Mechanism rigor spans roughly six dimensions — direction extraction quality, site/layer selection, intervention scaling, control baselines, scope of intervention, and probe-vs-causal disentanglement — which map onto Checks A–F below. Most failures in this vertical do **not** look like fraud; they look like "the feature doesn't matter," "the random direction beat the learned one," or "specificity fails." The honest evaluation faithfully reports an artifact of an under-tuned mechanism, and downstream readers update on noise.

Each invocation scopes to one claim's runs and returns a PASS/WARN/FAIL/N/A verdict on that claim's mechanism rigor; non-mechanistic claims (e.g., pure dataset evaluation) return N/A and are not penalized downstream.

## Core Principle

**The executor (Claude) collects file paths scoped to the target claim. The external LLM reviewer reads code and judges mechanism rigor. The executor does NOT participate in the rigor judgment.**

This follows `shared-references/reviewer-independence.md` and mirrors `/experiment-audit`'s reviewer-independence pattern.

## Relationship to /experiment-audit

| Skill                | Audits                                  | Outputs                            |
|----------------------|-----------------------------------------|------------------------------------|
| `/experiment-audit`  | Evaluation methodology honesty (A–F: GT, normalization, file existence, dead code, scope, eval type) | `EXPERIMENT_AUDIT.{md,json}`       |
| `/mechanism-audit`   | Mechanism / intervention rigor (A: coefficient sweep; B–F reserved) | `MECHANISM_AUDIT.{md,json}`        |

Both write into the same per-claim audit directory (e.g., `verify/<claim_dir>/main_experiment_audit/`). The two verdicts are **combined by the caller** (e.g., `/auto-verify`) via `combined = max_severity(exp, mech)` where `fail > warn > pass > n/a`. **N/A is treated as PASS** for the purposes of combination (a claim that doesn't use any mechanism intervention should not be penalized).

## Check Catalogue

This catalogue is the **single source of truth** for what `/mechanism-audit` audits. Each row declares one check via five fields: `Trigger` (when does it apply?), `Required artifacts` (what files does the reviewer need?), `Audit questions` + `Criteria` (how is PASS/WARN/FAIL decided?), `Evidence` (what must the report cite?), and `Structured fields` (the named slots the reviewer fills in the JSON output). The Workflow below (Steps 2–4) walks this catalogue mechanically.

> **Extension recipe.** Adding a new check requires three template-level edits, all driven by this catalogue:
> 1. Add a row to the table above + a full five-field subsection below.
> 2. In Step 4's reviewer prompt, add one more dashed `## Check X` block following the same paste-verbatim recipe used for Check A — the loop is mechanical, no per-check logic.
> 3. In Step 5's report templates (Markdown + JSON), add a per-check section mirroring the new check's `Structured fields`.
>
> Steps 2–3 (trigger detection + artifact collection) iterate the catalogue and need **no** code change. The repeated paste-mimicry in Steps 4–5 is intentional: it keeps the LLM prompt and the report schema self-contained and inspectable.

| ID | Name                       | Trigger (one-line)                                                              | Required artifacts                                                                                              |
|----|----------------------------|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| A  | Steering coefficient sweep | Any additive activation intervention with a scalar coefficient α (steering, CAA, DAS, RepE, SAE feature scaling, activation patching, ROME). | intervention/hook script(s); sweep config or α grid; per-α run outputs with target + capability metrics; direction-extraction site (for σ_proj). |
| B  | Reserved                   | — (future: direction-extraction quality)                                        | —                                                                                                               |
| C  | Reserved                   | — (future: site / layer selection rationale)                                    | —                                                                                                               |
| D  | Reserved                   | — (future: n_effective sufficiency)                                             | —                                                                                                               |
| E  | Reserved                   | — (future: probe-vs-causal disentanglement)                                     | —                                                                                                               |
| F  | Reserved                   | — (future: intervention scope / multi-site coverage)                            | —                                                                                                               |

### Check A — Steering coefficient sweep

**Trigger keywords / signals** — scan EXPERIMENT_PLAN.md's `<Cx>` methodology section, the filtered `<Cx>` tracker rows, and scripts referenced by those rows. Check A fires if ANY match:
  - **plan declarations** — any methodology phrasing naming: steering vector, CAA, contrastive activation addition, DAS, interchange intervention, RepE, representation engineering, SAE feature scaling, activation patching, ROME.
  - **identifier keywords** (case-insensitive grep on scripts): `steer`, `steering_vector`, `\bCAA\b`, `contrastive_activation`, `\bDAS\b`, `interchange`, `\bRepE\b`, `representation_engineering`, `sae_feature`, `feature_scaling`, `activation_patch`, `\bROME\b`.
  - **code patterns**: a scalar (commonly `alpha`, `coeff`, `dose`, `magnitude`) multiplying an additive contribution to a hidden state, e.g. `activations += alpha * v`, `hidden_states[..., site] += alpha * direction`, `h = h + coeff * steering_vec`.

**Required artifacts** (Step 3 collects these only if triggered):
  1. Intervention / hook script(s) implementing the additive update.
  2. Sweep config or in-code α grid (yaml / json / Python list literal).
  3. Per-α run outputs containing the target metric AND any capability / coherence metric (perplexity, val-acc on an unrelated task, fluency, NaN rate, repetition rate, output-confidence).
  4. Direction-extraction code — wherever the steering direction is computed (and where `σ_proj = projections.std()` or equivalent would live).
  5. **Sampled post-steering output cases** — raw model completions for representative prompts at several α values (especially α = 0, mid-plateau, near-collapse, and the locked α), if logged. These let the reviewer eyeball whether the metric story matches the actual text — e.g., a target-metric "win" at large α paired with repetition / garbled output / off-topic drift indicates the metric is reading OOD collapse as behavior. If too many cases were logged, Step 3 samples a few per α value (e.g. 5 prompts × the α grid).

**Audit questions** (the reviewer answers all 8):
  1. Was a sweep performed (multiple α tried), not a single hardcoded value?
  2. Did the sweep span ≥ 3 orders of magnitude (e.g. [0.1, 0.3, 1, 3, 10] × σ_proj) and include α = 0 baseline?
  3. Was α expressed in σ_proj units (k · σ_proj), not raw unit-vector norm? (Look for `.std()` on a projection-like quantity next to the steering call.)
  4. Was BOTH a *target metric* AND an independent *capability / coherence metric* logged at every sweep point?
  5. Was a usable plateau identified — target clearly above baseline noise AND capability within tolerance (< ~10% degradation; no collapse)? (If raw post-steering output cases are available — artifact #5 — spot-check them: at the locked α the text should read coherently and express the target behavior; at near-collapse α the metric should track visible degradation. A capability metric that says "fine" while sampled outputs are garbled / repetitive / off-topic is a broken metric, not a successful steer.)
  6. Was the locked α placed in the MIDDLE of the plateau (not at its edge)?
  7. (Recommended) Was a random-direction control run at the locked α with n_random ≥ 30, and does the learned direction's effect statistically beat random?
  8. If the protocol is asymmetric across sites (+α at one group, −α at another), is the sign pattern preserved, not flattened into uniform-push?

**FAIL** if ANY of:
  - Single hardcoded α copied from another paper, no sweep at all.
  - Sweep done but NO capability metric logged (collapse cannot be detected; large-α "effect" may be OOD drift, not steering).
  - α chosen where capability has crashed (> 2× baseline degradation — collapse range).
  - α chosen where target effect is within baseline-noise floor (effect drowned out).
  - Asymmetric protocol flattened into uniform-push (sign pattern broken).

**WARN** if ANY of (and no FAIL):
  - Sweep performed but spans < 3 orders of magnitude, OR < 5 grid points.
  - α expressed in raw norm rather than σ_proj units (silently incomparable across runs / sites / papers).
  - Plateau identified but α sits at the plateau edge (not middle).
  - No random-direction control at the locked α.

**PASS** if all 8 questions are satisfied AND the chosen α is mid-plateau with both behavior expression and capability preservation evidence.

**Evidence to report**: file:line for the sweep-grid definition, the logged α values, the chosen α, plateau range [α_min, α_collapse], the capability metric used, random-baseline result (if any), and the σ_proj computation site.

**Structured fields** (the reviewer MUST return these named slots — they map 1:1 to the Check A JSON node in Step 5):

| Field                    | Type                                                                 | Example                                                                 |
|--------------------------|----------------------------------------------------------------------|-------------------------------------------------------------------------|
| `status`                 | `"pass" \| "warn" \| "fail"`                                         | `"warn"`                                                                |
| `intervention_type`      | `"steering" \| "CAA" \| "DAS" \| "RepE" \| "SAE_feature" \| "activation_patch" \| "ROME" \| "other"` | `"CAA"`                                                                 |
| `sweep_grid`             | `number[]` (α values tried; `[α₀]` if single-value)                  | `[0, 0.3, 1.0, 3.0]`                                                    |
| `sigma_proj_scaling`     | `bool`                                                               | `false`                                                                 |
| `capability_metric`      | `string \| null`                                                     | `"perplexity_holdout"` or `null` if none logged                         |
| `plateau_range`          | `[number, number] \| null`                                           | `[0.3, 3.0]`                                                            |
| `locked_alpha`           | `number \| null`                                                     | `3.0`                                                                   |
| `alpha_position`         | `"middle" \| "edge" \| "outside" \| "n/a"`                           | `"edge"`                                                                |
| `random_baseline`        | `{run: bool, n_random: number\|null, passed: bool\|null}`             | `{run: false, n_random: null, passed: null}`                            |
| `sign_pattern`           | `"preserved" \| "broken" \| "n/a"`                                   | `"n/a"`                                                                 |
| `output_case_spotcheck`  | `{cases_available: bool, verdict: "metric_text_consistent"\|"metric_text_mismatch"\|"no_cases_logged", note: string}` | `{cases_available: true, verdict: "metric_text_mismatch", note: "..."}` |
| `evidence`               | `string[]` (`"file:line"` or `"file:line-line"`)                     | `["src/steering.py:42-58", "configs/sweep.yaml:12"]`                    |
| `details`                | `string` (one-paragraph reviewer explanation)                        | `"Sweep done but α locked at plateau edge; no σ_proj scaling."`         |

When `triggered=false` for Check A (handled by executor on early N/A exit, not by reviewer), the JSON node degenerates to `{"status": "n/a", "triggered": false, "trigger_match": []}` — no structured fields are emitted.

### Checks B–F — Reserved

Not yet implemented. Fill in by mirroring Check A's five-field template (Trigger / Required artifacts / Audit questions + Criteria / Evidence / Structured fields). Until then they are recorded as `not_implemented` in the report and do not influence `overall_verdict`.

## Constants

- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback. Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP.

## Arguments

- **`<experiment-dir-or-results-path>`** (positional, **required**) — directory containing the experiment artifacts to audit. Typically `refine-logs/` (for main-experiment audit) or `verify/<claim_dir>/variants/` (for variant audit).
- **`— claim <Cx>`** (**required**) — the claim whose mechanism rigor is being audited. The skill is inherently per-claim: each invocation produces ONE PASS/WARN/FAIL/N/A verdict for the named claim. To audit N claims, call the skill N times.
- **`— output-dir <path>`** (optional) — directory to write `MECHANISM_AUDIT.{md,json}` into. Defaults to current working directory. When given, the skill creates `<path>` if needed and writes directly to `<path>/MECHANISM_AUDIT.md` and `<path>/MECHANISM_AUDIT.json`; callers do not need a follow-up `mv`.

Example invocations:
```
/mechanism-audit "refine-logs/"                    — claim C1 — output-dir verify/C1_polysemantic/main_experiment_audit
/mechanism-audit "verify/<claim_dir>/variants/"    — claim C1 — output-dir verify/<claim_dir>/variant_audit
```

If `— claim` is omitted, abort with:
> "mechanism-audit: `— claim <Cx>` is required. This skill is per-claim by design — to audit a whole project, run it once per claim."

## Reviewer LLM Configuration (mandatory, read first)

This skill calls an external LLM reviewer. **Never hardcode a model name and never read the reviewer model from `task.md` / project READMEs / source comments.** Project-level files may list available API keys for unrelated purposes (e.g., LLM-as-judge inside experiment code); those are *not* the reviewer config.

Resolve `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` strictly in this priority order before any reviewer call:

1. **Project MCP config** — `${PROJECT_ROOT}/.mcp.json`, field `mcpServers["llm-chat"].env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}`.
2. **User MCP config** — `~/.claude/settings.json`, same field.
3. **Shell environment** — `$LLM_MODEL`, `$LLM_BASE_URL`, `$LLM_API_KEY`.

### Pre-flight check (run before Step 4 — skip on Step 2 early N/A exit)

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

**Skip rule.** If Step 2 took the early N/A exit (no implemented check triggered), the reviewer call in Step 4 never runs — skip this pre-flight too. A pure-evaluation claim must not be aborted just because the project lacks a reviewer key it would never use.

**Hard-fail rule**: If the pre-flight runs (i.e., at least one check triggered) and `LLM_MODEL` is empty after this resolution (none of the three sources provides it), the skill MUST abort with:
> "Reviewer model not configured. Add `mcpServers.llm-chat.env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}` to `.mcp.json` (project) or `~/.claude/settings.json` (user)."

Do not guess a default. Do not fall back to a model name read from `task.md` or any other project file.

## Workflow

The workflow is a **mechanical walk over the Check Catalogue**. Step 1 scopes the file universe to claim `<Cx>` (mirrors `/experiment-audit`'s Step 1). Steps 2–3 iterate the catalogue: for each implemented check K, detect whether K's trigger fires; if it does, collect K's `Required artifacts`. Step 4 hands the per-check bundles to the reviewer with K's criteria block pasted verbatim from the catalogue. Step 5 writes the report; Step 6 prints a one-line summary to stdout for human / caller convenience.

> **No catalogue logic is embedded in this section.** Adding a new check (B–F) means editing only the catalogue above; Steps 2–4 pick it up automatically.

### Step 1: Collect `<Cx>`-scoped artifacts (Executor — Claude)

This skill is per-claim. Resolve `<Cx>` → milestones → scripts/outputs; the result is the search universe for the per-check Steps 2–3. Mirrors `/experiment-audit`'s Step 1 (sub-steps 1a/1b are identical in intent).

#### 1a. Resolve `<Cx>`'s linked milestones

```
1. Read EXPERIMENT_PLAN.md from the experiment-dir argument.
2. Locate the "## Claim-to-Milestone Map" table (columns typically:
   `Claim | Tests | Required milestones | Pass criterion`).
3. Find the row where the `Claim` column equals <Cx>.
4. Parse the `Required milestones` column → list of milestone IDs, e.g. ["M1", "M2"].
5. If <Cx> has no row in the map, abort with:
   "mechanism-audit: claim <Cx> not found in EXPERIMENT_PLAN.md's Claim-to-Milestone Map."
```

#### 1b. Filter the tracker to `<Cx>`'s milestone rows

```
1. Read EXPERIMENT_TRACKER.md from the experiment-dir argument.
2. Keep only rows whose `Milestone` column starts with any of <Cx>'s milestone IDs.
3. From those rows, collect:
     - scripts referenced (CX_SCRIPTS): a deduped list of source files.
     - result-file paths and run directories (CX_OUTPUTS).
     - the matching tracker row text itself (CX_TRACKER_TEXT).
```

`CX_SCRIPTS` and `CX_OUTPUTS` are the **search universe** for Steps 2–3. Per-check trigger detection and artifact collection look only inside this set.

### Step 2: Per-check trigger detection (Executor — Claude)

Walk the Check Catalogue. For each implemented check `K`, evaluate K's `Trigger keywords / signals` against three sources:

  1. The `<Cx>` methodology paragraph from EXPERIMENT_PLAN.md (Step 1a).
  2. `CX_TRACKER_TEXT` (Step 1b).
  3. `CX_SCRIPTS` — grep for K's keyword regex:
     ```bash
     # K_REGEX is K's trigger keyword regex from the catalogue
     grep -rlnE "$K_REGEX" $CX_SCRIPTS 2>/dev/null
     ```

Record `triggered[K] = true` if ANY source matches; otherwise `false`. Also stash the match locations (file:line) — they become the starting points for Step 3's collection.

**Early N/A exit.** If every implemented K has `triggered[K] = false`:
  - Set `overall_verdict = n/a`.
  - Skip Steps 3–4 entirely (no reviewer call needed; Pre-flight is also skipped — see "Reviewer LLM Configuration" above).
  - Go directly to Step 5 to write the N/A report (see "Early N/A exit rendering" there).

### Step 3: Per-check artifact collection (Executor — Claude)

For each `K` where `triggered[K] = true`, collect K's `Required artifacts` from the catalogue, scoped to `CX_SCRIPTS ∪ CX_OUTPUTS`. The catalogue row tells you what kinds of files to look for; the Step-3 match locations tell you where in the codebase to start.

**Large-file sampling.** If a required artifact is > ~500 lines or > ~200 KB, do not pass the whole file. Pass a sampled view and record the sampling method in the bundle:

  - **Tabular / JSONL run outputs** (e.g. per-α metric logs): stratified sample — one row per α / sweep point if the file is keyed by α; otherwise first 20 + last 20 + every 10th middle row.
  - **Long log files**: first 50 + last 50 lines.
  - **Code files**: pass whole (code is rarely the size problem; truncation breaks line-number evidence).

> **Catalogue-specific sampling overrides this generic rule.** When a check's `Required artifacts` entry specifies a sampling recipe (e.g. Check A artifact #5 says "5 prompts × the α grid" for raw output cases), follow the catalogue recipe instead of the generic rule above. The generic rule is the fallback when the catalogue is silent.

Assemble each K's bundle as:

```yaml
check_id: A
artifacts:
  - role: intervention_script
    path: src/steering.py
    sampling: full
  - role: sweep_config
    path: configs/sweep.yaml
    sampling: full
  - role: per_alpha_run_output
    path: runs/sweep_20260601/results.jsonl
    sampling: "stratified: one row per α (5 of 5)"
  - role: direction_extraction
    path: src/directions.py
    sampling: full
match_locations:    # from Step 2, for reviewer's reference
  - src/steering.py:42  # "activations += alpha * v"
  - configs/sweep.yaml:12  # "alpha: [0, 0.3, 1.0, 3.0]"
```

### Step 4: Reviewer call (external LLM via llm-chat MCP)

For each triggered `K`, **paste K's catalogue subsection verbatim** (Audit questions + FAIL/WARN/PASS criteria + Evidence-to-report) into the prompt, followed by K's bundle from Step 3. The reviewer reads bundled files directly and judges only against the pasted criteria. Always ask for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    You are a mechanistic-experiment rigor auditor. For each check block below,
    read the listed files and return ONE verdict (PASS | WARN | FAIL) judged
    strictly against that block's criteria.

    Audit scope: claim <Cx>, restricted to the milestones below.
    Triggering has ALREADY been decided by the executor. Do NOT skip a check
    you think shouldn't apply — every block below is one you must grade.

    Context:
    - claim: <Cx> — [claim statement]
    - milestones: [M1, M2, ...]

    (The mechanism in actual use is grounded by the trigger match locations
    inside each check block below — read those file:line citations rather
    than relying on the plan's self-description.)

    ──────────────────────────────────────────────────────────────────
    ## Check A — Steering coefficient sweep

    [PASTE VERBATIM from Catalogue §"Check A — Steering coefficient sweep":
       Audit questions (all 8)
       FAIL criteria
       WARN criteria
       PASS criteria
       Evidence to report]

    Artifacts for Check A:
      [paste the YAML bundle from Step 3 for K = A]

    Executor-found match locations (starting points):
      [file:line list from Step 2]
    ──────────────────────────────────────────────────────────────────

    [Repeat one dashed block per additional triggered check as B–F come online.]

    ## Output schema
    For each check block above, return ALL named slots listed in that block's
    "Structured fields" table — verbatim by field name and type. At minimum every
    check returns `check_id`, `status`, `evidence`, `details`; check-specific slots
    (e.g. Check A's `intervention_type`, `sweep_grid`, `sigma_proj_scaling`,
    `capability_metric`, `plateau_range`, `locked_alpha`, `alpha_position`,
    `random_baseline`, `sign_pattern`, `output_case_spotcheck`) are mandatory and
    must use the exact field names from that check's Structured fields table.
    If a slot is genuinely unknowable from the artifacts (e.g. `random_baseline`
    when no random-direction control was run), return the documented null shape
    (`{run: false, n_random: null, passed: null}`) — do NOT omit the field.

    Then return:
      - overall_verdict = max severity across the blocks above
        (fail > warn > pass).

    Be thorough. Read every artifact line by line. Do not infer from filenames.
```

### Step 5: Write report (Executor — Claude)

**Output path resolution.** If `— output-dir <path>` was given, write to `<path>/MECHANISM_AUDIT.md` and `<path>/MECHANISM_AUDIT.json` directly (create `<path>` with `mkdir -p` if needed); otherwise write to the current working directory.

**Status assignment per catalogue row** — walk the catalogue in order:

| Check state                                     | Reported `status`  | Counts toward `overall_verdict`? |
|-------------------------------------------------|--------------------|----------------------------------|
| Implemented, triggered, reviewer judged         | `pass / warn / fail` | yes                            |
| Implemented, **not triggered** (Step 2 = false) | `n/a`              | no                               |
| **Reserved** (B–F: no implementation yet)       | `not_implemented`  | no                               |

`overall_verdict = max_severity` over checks whose status ∈ {pass, warn, fail}. If that set is empty (all checks were n/a or not_implemented) → `overall_verdict = n/a`.

**Early N/A exit rendering** — when Step 2 took the early-N/A exit (no implemented check triggered), the reviewer never ran, so the per-check structured fields are unknowable by construction. Use this degenerate shape and **skip** the regular per-check field rendering below:

- **Markdown** — for each implemented check, write only:
  ```
  ### A. Steering Coefficient Sweep: N/A
  - Triggered: no (no catalogue trigger matched in <Cx>'s scope)
  ```
  Omit Intervention type / Sweep grid / Plateau / Output-case spot-check / Evidence / Verdict-reason rows entirely. The N/A reason already explains why every field is empty.

- **JSON** — for each implemented check, write:
  ```json
  "steering_coefficient_sweep": {
    "status": "n/a",
    "triggered": false,
    "trigger_match": []
  }
  ```
  No structured fields. Top-level: `"triggered_checks": []`, `"overall_verdict": "n/a"`.

When at least one check triggered, render the full per-check field block below as usual.

Write `MECHANISM_AUDIT.md`:

```markdown
# Mechanism Audit Report — Claim <Cx>

**Date**: [today]
**Auditor**: external LLM reviewer (cross-model, via llm-chat MCP)
**Project**: [project name]
**Claim**: <Cx> — [claim statement]
**Linked milestones**: [M1, M2, ...]

## Overall Verdict: [PASS | WARN | FAIL | N/A]
*This is `<Cx>`'s mechanism-rigor verdict. `N/A` means no catalogue check
was triggered for `<Cx>`'s scope — either the claim uses no mechanism
intervention, or its intervention lies outside the current catalogue coverage.*

## Triggered checks (this run): [list of K with triggered = true, e.g. "A"]

## Checks

### A. Steering Coefficient Sweep: [PASS | WARN | FAIL | N/A]
- Triggered: [yes — via "src/steering.py:42 (activations += alpha * v)" | no]
- Intervention type: [steering vector | CAA | DAS | SAE feature | ROME | n/a]
- Sweep grid: [α values tried, or "single hardcoded value: ..."]
- σ_proj scaling used: [yes | no | n/a]
- Capability metric logged: [perplexity | val-acc | fluency | ... | none]
- Plateau range: [α_min, α_collapse] = [..., ...]
- Locked α: [value]   (position in plateau: middle | edge | outside)
- Random-direction control: [yes (n=...) → passed/failed | no | n/a]
- Sign pattern (if asymmetric): [preserved | broken | n/a]
- Output-case spot-check: [coherent at locked α; degraded at near-collapse — metric tracks text | metric/text mismatch (e.g. "fluency ok" but cases garbled) | no cases logged]
- Evidence: [file:line references]
- Verdict reason: [one sentence]

### B–F. Reserved (not_implemented)
Status: not yet implemented. Future checks may cover direction-extraction
quality, site / layer selection, n_effective sufficiency, probe-vs-causal
disentanglement, intervention scope.

## Action Items
- [specific fixes if WARN or FAIL]
```

Also write `MECHANISM_AUDIT.json`:

```json
{
  "date": "2026-06-05",
  "auditor": "llm-chat",
  "audit_type": "mechanism",
  "claim_id": "C1",
  "linked_milestones": ["M1", "M2"],
  "triggered_checks": ["A"],
  "overall_verdict": "warn",
  "checks": {
    "steering_coefficient_sweep": {
      "status": "warn",
      "triggered": true,
      "trigger_match": ["src/steering.py:42 (activations += alpha * v)",
                        "configs/sweep.yaml:12 (alpha grid)"],
      "intervention_type": "CAA",
      "sweep_grid": [0, 0.3, 1.0, 3.0],
      "sigma_proj_scaling": false,
      "capability_metric": "perplexity_holdout",
      "plateau_range": [0.3, 3.0],
      "locked_alpha": 3.0,
      "alpha_position": "edge",
      "random_baseline": {"run": false, "n_random": null, "passed": null},
      "sign_pattern": "n/a",
      "output_case_spotcheck": {
        "cases_available": true,
        "verdict": "metric_text_mismatch",
        "note": "perplexity within tolerance at α=3.0 but sampled completions show repetition / topic drift on 3 of 5 prompts."
      },
      "evidence": ["src/steering.py:42-58", "configs/sweep.yaml:12"],
      "details": "Sweep done but α locked at plateau edge; no σ_proj scaling."
    },
    "check_b_reserved": {"status": "not_implemented"},
    "check_c_reserved": {"status": "not_implemented"},
    "check_d_reserved": {"status": "not_implemented"},
    "check_e_reserved": {"status": "not_implemented"},
    "check_f_reserved": {"status": "not_implemented"}
  }
}
```

> **N/A semantics.** A check with `triggered: false` reports `status: n/a` (not `not_implemented`). When `triggered_checks` is empty, set `overall_verdict: n/a`. Downstream `/auto-verify` treats `n/a` as `pass` for `max_severity` combination — claims with no mechanism intervention are not punished by this audit.

> **No `Claim Impact` section, no `claims` array.** This skill audits mechanism
> rigor for ONE claim; `overall_verdict` IS that claim's mechanism verdict.
> Methodology honesty is `/experiment-audit`'s job; semantic claim support is
> `/result-to-claim`'s job. To audit multiple claims, invoke this skill once
> per claim.

### Step 6: Print summary

```
🔧 Mechanism Audit Complete — Claim C1 (M1, M2)

  Triggered checks: A  (matches at src/steering.py:42, configs/sweep.yaml:12)

  A. Steering Coefficient Sweep: ⚠️ WARN — α at plateau edge, no σ_proj scaling
  B–F. Reserved:                 — not_implemented

  Overall (C1): ⚠️ WARN

  See <output-dir>/MECHANISM_AUDIT.md for details.
```

When no implemented check triggered (early N/A exit from Step 2):

```
🔧 Mechanism Audit Complete — Claim C1 (M1, M2)

  Triggered checks: (none)

  A. Steering Coefficient Sweep: — N/A (trigger not matched)
  B–F. Reserved:                 — not_implemented

  Overall (C1): — N/A (combination treats this as PASS)

  See <output-dir>/MECHANISM_AUDIT.md for details.
```

## Integration with Other Skills

### Automatic in /auto-verify (advisory, never blocks)

This skill runs **per claim**, paired with `/experiment-audit`, at every phase where `/experiment-audit` is invoked. Concretely in `/auto-verify`:

- **Phase 2** (main-experiment integrity gate): `/experiment-audit` followed by `/mechanism-audit`, both scoped to `Cx`, both writing to `verify/<claim_dir>/main_experiment_audit/`. The Phase 2 gate verdict is `combined = max_severity(exp.overall_verdict, mech.overall_verdict)` with the severity ordering `fail > warn > pass > n/a`.
- **Phase 9** (variant integrity audit): symmetric — both audits run on `verify/<claim_dir>/variants/`, both write to `verify/<claim_dir>/variant_audit/`. Each variant's `integrity_status` in `verdict.json` is set to the per-variant combined verdict.

```
/auto-experiment → results ready
    ↓
for each Cx:
    /experiment-audit → EXPERIMENT_AUDIT.{md,json}
    /mechanism-audit  → MECHANISM_AUDIT.{md,json}
    combined = max_severity(exp.overall_verdict, mech.overall_verdict)
        ├── PASS  → continue normally for Cx
        ├── WARN  → print ⚠️ warning, continue, tag Cx as [INTEGRITY: WARN]
        └── FAIL  → print 🔴 alert, continue, tag Cx as [INTEGRITY CONCERN]
    ↓
/auto-iteration-loop
```

**Never blocks the pipeline.** Even on FAIL, the pipeline continues — but the affected claim carries a visible integrity tag.

### Complementary with /experiment-audit and /result-to-claim

`/experiment-audit` answers **"is the evaluation methodology / reporting honest?"** (Checks A–F: GT, normalization, file existence, dead code, scope, eval type).
`/mechanism-audit` answers **"was the interpretability mechanism tuned with the necessary controls?"** (Check A: coefficient sweep; B–F reserved).
`/result-to-claim` answers **"do the numbers semantically support the claim?"** (statistical / scope reasoning).

The three are intentionally separate. Downstream skills typically read both audit JSONs and combine:

```
exp_verdict  = read EXPERIMENT_AUDIT.json.overall_verdict
mech_verdict = read MECHANISM_AUDIT.json.overall_verdict   # may be "n/a"
combined     = max_severity(exp_verdict, mech_verdict)     # n/a treated as pass

if combined == "fail":
    downgrade verdict display: "yes [INTEGRITY CONCERN]"
```

`/mechanism-audit` does NOT emit `claim_supported`. Its `overall_verdict` IS the target claim's mechanism-rigor verdict (PASS/WARN/FAIL/N/A); to cover N claims, invoke it N times.

## Key Rules

- **Reviewer independence**: executor collects paths, reviewer judges. Period.
- **Never block**: warn loudly, never halt the pipeline.
- **N/A is not a failure**: a check whose trigger does not fire in `<Cx>`'s scope reports `n/a`; if no implemented check triggers, the overall verdict is `n/a`. Downstream combination treats N/A as PASS, so claims out of catalogue coverage are not punished.
- **Catalogue is the API**: extension = add one row + one subsection to the Check Catalogue. Workflow, reviewer prompt, and report writer are mechanism-agnostic and pick up the new row automatically.
- **File-as-switch**: no MECHANISM_AUDIT.md = skill was never run = zero impact on existing behavior.
- **Cross-model**: the reviewer MUST be a different model family from the executor.
- **Honest about limits**: only Check A (steering coefficient sweep) is implemented. B–F are reserved placeholders for future mechanism-rigor checks. A PASS today only certifies that the coefficient was swept correctly; it does not certify direction quality, site choice, or sample-size sufficiency.

## Acknowledgements

Check A's failure-mode catalog and audit logic are concentrated from
`experiment-tips/steering-coefficient-tuning/SKILL.md`.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
