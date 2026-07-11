---
name: experiment-audit
description: "Audit the experimental **methodology** integrity for a specific claim (Checks A–F: GT provenance, score normalization, result-file existence, dead code, scope, eval-type). Uses cross-model review (external LLM reviewer via llm-chat MCP). The output `overall_verdict` (PASS/WARN/FAIL) is THIS claim's verdict — i.e., whether the claim's experimental process is methodologically sound. Does NOT judge whether the numbers semantically support the claim's hypothesis — that is `/result-to-claim`'s job."
argument-hint: <experiment-dir-or-results-path> — claim <Cx> [— output-dir <path>]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__llm-chat__chat
---

# Experiment Audit: Per-Claim Cross-Model Integrity Verification

Audit the experimental process for one claim: **$ARGUMENTS**

## Why This Exists

LLM agents can produce fraudulent experimental results through:
1. **Fake ground truth** — creating synthetic "reference" from model outputs, then reporting high agreement as performance
2. **Score normalization** — dividing metrics by the model's own max to get 0.99+
3. **Phantom results** — claiming numbers from files that don't exist or functions never called
4. **Insufficient scope** — reporting 2-scene pilots as "comprehensive evaluation"

These are NOT intentional deception — they are failure modes of optimizing agents that lack integrity constraints. This skill adds that constraint, **once per claim**: each invocation scopes to one claim's runs and returns a PASS/WARN/FAIL verdict on that claim's experimental process.

## Core Principle

**The executor (Claude) collects file paths scoped to the target claim. The external LLM reviewer reads code and judges integrity. The executor does NOT participate in integrity judgment.**

This follows `shared-references/reviewer-independence.md` and `shared-references/experiment-integrity.md`.

## Constants

- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback. Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP.

## Arguments

- **`<experiment-dir-or-results-path>`** (positional, **required**) — directory containing the experiment artifacts to audit. Typically `refine-logs/` (for main-experiment audit) or `verify/<claim_dir>/variants/` (for variant audit).
- **`— claim <Cx>`** (**required**) — the claim whose experimental process is being audited. The skill is inherently per-claim: each invocation produces ONE PASS/WARN/FAIL verdict for the named claim, derived from auditing only that claim's linked milestones/runs. To audit N claims, call the skill N times.
- **`— output-dir <path>`** (optional) — directory to write `EXPERIMENT_AUDIT.{md,json}` into. Defaults to current working directory. When given, the skill creates `<path>` if needed and writes directly to `<path>/EXPERIMENT_AUDIT.md` and `<path>/EXPERIMENT_AUDIT.json`; callers do not need a follow-up `mv`.

Example invocations:
```
/experiment-audit "refine-logs/"                    — claim C1 — output-dir verify/C1_polysemantic/main_experiment_audit
/experiment-audit "verify/<claim_dir>/variants/"    — claim C1 — output-dir verify/<claim_dir>/variant_audit
```

If `— claim` is omitted, abort with:
> "experiment-audit: `— claim <Cx>` is required. This skill is per-claim by design — to audit a whole project, run it once per claim."

## Reviewer LLM Configuration (mandatory, read first)

This skill calls an external LLM reviewer. **Never hardcode a model name and never read the reviewer model from `task.md` / project READMEs / source comments.** Project-level files may list available API keys for unrelated purposes (e.g., LLM-as-judge inside experiment code); those are *not* the reviewer config.

Resolve `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` strictly in this priority order before any reviewer call:

1. **Project MCP config** — `${PROJECT_ROOT}/.mcp.json`, field `mcpServers["llm-chat"].env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}`.
2. **User MCP config** — `~/.claude/settings.json`, same field.
3. **Shell environment** — `$LLM_MODEL`, `$LLM_BASE_URL`, `$LLM_API_KEY`.

### Pre-flight check (run before Step 2, mandatory)

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

## Workflow

### Step 1: Collect Artifacts (Executor — Claude)

This skill is per-claim. The executor's job is to (a) figure out which milestones / runs back the target claim `<Cx>`, (b) collect file paths for those, and (c) collect the shared infrastructure (eval scripts, configs, dataset paths) that any audit needs. DO NOT read or summarize file content; only collect paths.

#### 1a. Resolve `<Cx>`'s linked milestones

```
1. Read EXPERIMENT_PLAN.md from the experiment-dir argument.
2. Locate the "## Claim-to-Milestone Map" table (columns typically:
   `Claim | Tests | Required milestones | Pass criterion`).
3. Find the row where the `Claim` column equals <Cx>.
4. Parse the `Required milestones` column → list of milestone IDs, e.g. ["M1", "M2"].
5. If <Cx> has no row in the map, abort with:
   "experiment-audit: claim <Cx> not found in EXPERIMENT_PLAN.md's Claim-to-Milestone Map."
```

#### 1b. Filter the tracker to `<Cx>`'s milestone rows

```
1. Read EXPERIMENT_TRACKER.md from the experiment-dir argument.
2. Keep only rows whose `Milestone` column starts with any of <Cx>'s milestone IDs
   (e.g. M1 matches M1a, M1b, ...; M2 matches M2a, M2b, ...).
3. From those rows, collect the result-file paths and run directories they reference
   (look in the row's notes / output columns).
4. Also keep the matching tracker row text itself for Check C (number consistency).
```

#### 1c. Collect shared infrastructure (no filtering — same as before)

```
Scan the experiment directory for:
1. Evaluation scripts:    *eval*.py, *metric*.py, *test*.py, *benchmark*.py
2. Ground truth paths:    look in eval scripts for data loading (dataset paths, GT references)
3. Paper claims:          NARRATIVE_REPORT.md, paper/sections/*.tex, PAPER_PLAN.md
                          — keep ONLY the part(s) discussing <Cx>; ignore unrelated claims.
4. Config files:          *.yaml, *.toml, *.json configs with metric definitions
```

Checks A, B, D, F audit this shared infrastructure (since the same eval script is used by every milestone). Checks C and E are claim-scoped to <Cx>'s evidence collected in 1a/1b.

Pass to Step 2: `<Cx>`, the filtered tracker rows, the filtered result-file list, the shared eval/config/dataset paths, and the Cx-relevant portion of paper claims.

### Step 2: Send to Reviewer (external LLM via llm-chat MCP)

Pass ONLY file paths and the audit checklist to the reviewer. The reviewer reads everything directly. Always ask the external reviewer for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    You are an experiment integrity auditor. Read ALL files listed below
    and check for the following fraud patterns.

    Audit scope: claim <Cx> only.
    - Checks A, B, D, F audit the shared eval / config / dataset infrastructure that <Cx> uses.
    - Checks C, E are restricted to <Cx>'s linked milestones (provided as filtered tracker rows
      and result files below). Ignore other claims' evidence.
    - Your final overall_verdict is <Cx>'s integrity verdict (PASS/WARN/FAIL).

    Files to read:
    - Evaluation scripts: [list paths]
    - Result files (filtered to <Cx>'s milestones): [list paths]
    - Tracker rows (filtered to <Cx>'s milestones): [paste rows or path]
    - Paper claim text for <Cx>: [paste relevant section]
    - Config files: [list paths]

    ## Audit Checklist

    ### A. Ground Truth Provenance
    For each evaluation script:
    1. Where does "ground truth" / "reference" / "target" come from?
    2. Is it loaded from the DATASET, or generated/derived from MODEL OUTPUTS?
    3. If derived: is it explicitly labeled as proxy evaluation?
    4. Are official eval scripts used when available for this benchmark?
    FAIL if: GT is derived from model outputs without explicit proxy labeling.

    ### B. Score Normalization
    For each metric computation:
    1. Is any metric divided by max/min/mean of the model's OWN output?
    2. Are raw scores reported alongside any normalized scores?
    3. Are any scores suspiciously close to 1.0 or 100%?
    FAIL if: Normalization denominator comes from prediction statistics.

    ### C. Result File Existence
    For each claim in the paper/narrative:
    1. Does the referenced result file actually exist?
    2. Does the claimed metric key exist in that file?
    3. Does the claimed NUMBER match what's in the file?
    4. Is the experiment tracker status DONE (not TODO/IN_PROGRESS)?
    FAIL if: Claimed results reference nonexistent files or mismatched numbers.

    ### D. Dead Code Detection
    For each metric function defined in eval scripts:
    1. Is it actually CALLED in any evaluation pipeline?
    2. Does its output appear in any result file?
    WARN if: Metric functions exist but are never called.

    ### E. Scope Assessment
    1. How many scenes/datasets/configurations were actually tested?
    2. How many seeds/runs per configuration?
    3. Does the paper use words like "comprehensive", "extensive", "robust"?
    4. Is the actual scope sufficient for those claims?
    WARN if: Scope language exceeds actual evidence.

    ### F. Evaluation Type Classification
    Classify each evaluation as:
    - real_gt: uses dataset-provided ground truth
    - synthetic_proxy: uses model-generated reference
    - self_supervised_proxy: no GT by design
    - simulation_only: simulated environment
    - human_eval: human judges

    ## Output Format

    For each check (A-F), report:
    - Status: PASS | WARN | FAIL
    - Evidence: exact file:line references
    - Details: what specifically was found

    Overall verdict: PASS | WARN | FAIL
    
    Be thorough. Read every eval script line by line.
```

### Step 3: Parse and Write Report (Executor — Claude)

**Output path resolution.** If `— output-dir <path>` was given, write to `<path>/EXPERIMENT_AUDIT.md` and `<path>/EXPERIMENT_AUDIT.json` directly (create `<path>` with `mkdir -p` if needed); otherwise write to the current working directory.

Parse the reviewer's response and write `EXPERIMENT_AUDIT.md`:

```markdown
# Experiment Audit Report — Claim <Cx>

**Date**: [today]
**Auditor**: external LLM reviewer (cross-model, via llm-chat MCP)
**Project**: [project name]
**Claim**: <Cx> — [claim statement]
**Linked milestones**: [M1, M2, ...]

## Overall Verdict: [PASS | WARN | FAIL]
*This is `<Cx>`'s integrity verdict — whether `<Cx>`'s experimental process is methodologically sound.*

## Integrity Status: [pass | warn | fail]

## Checks

### A. Ground Truth Provenance: [PASS|WARN|FAIL]
[details + file:line evidence]

### B. Score Normalization: [PASS|WARN|FAIL]
[details]

### C. Result File Existence: [PASS|WARN|FAIL]
[details]

### D. Dead Code Detection: [PASS|WARN|FAIL]
[details]

### E. Scope Assessment: [PASS|WARN|FAIL]
[details]

### F. Evaluation Type: [real_gt | synthetic_proxy | ...]
[classification + evidence]

## Action Items
- [specific fixes if WARN or FAIL]
```

Also write `EXPERIMENT_AUDIT.json` for machine consumption:

```json
{
  "date": "2026-04-10",
  "auditor": "llm-chat",
  "claim_id": "C1",
  "linked_milestones": ["M1", "M2"],
  "overall_verdict": "warn",
  "integrity_status": "warn",
  "checks": {
    "gt_provenance": {"status": "pass", "details": "..."},
    "score_normalization": {"status": "warn", "details": "..."},
    "result_existence": {"status": "pass", "details": "..."},
    "dead_code": {"status": "pass", "details": "..."},
    "scope": {"status": "warn", "details": "..."},
    "eval_type": "real_gt"
  }
}
```

> **No `Claim Impact` section, no `claims` array.** This skill audits the experimental methodology and reporting honesty for ONE claim; `overall_verdict` IS that claim's integrity verdict. Whether the numbers semantically support the claim's hypothesis is a separate question handled by `/result-to-claim`. To audit multiple claims, invoke this skill once per claim.

### Step 4: Print Summary

```
🔬 Experiment Audit Complete — Claim C1 (M1, M2)

  A. GT Provenance:      ✅ PASS — real dataset GT used
  B. Score Normalization: ⚠️ WARN — boundary metric uses self-reference
  C. Result Existence:    ✅ PASS — all C1-linked files exist, numbers match
  D. Dead Code:           ✅ PASS — all metric functions called
  E. Scope (C1):          ⚠️ WARN — C1 wording "comprehensive" but only 2 scenes audited
  F. Evaluation Type:     real_gt

  Overall (C1): ⚠️ WARN

  See <output-dir>/EXPERIMENT_AUDIT.md for details.
```

## Integration with Other Skills

### Automatic in /auto (advisory, never blocks)

When integrated into the pipeline, this skill runs **per claim** after `/auto-experiment` and before `/auto-iteration-loop`. For each claim `Cx` in the project:

```
/auto-experiment → results ready
    ↓
for each Cx:
    /experiment-audit "refine-logs/" — claim Cx — output-dir results/audit/Cx/
        ├── PASS  → continue normally for Cx
        ├── WARN  → print ⚠️ warning, continue, tag Cx as [INTEGRITY: WARN]
        └── FAIL  → print 🔴 alert, continue, tag Cx as [INTEGRITY CONCERN]
    ↓
/auto-iteration-loop → proceeds with per-claim integrity tags visible to reviewer
```

**Never blocks the pipeline.** Even on FAIL, the pipeline continues — but the affected claim carries a visible integrity tag.

### Complementary with /result-to-claim (separate concerns)

`/experiment-audit` answers **"is the evaluation methodology / reporting honest?"** (Checks A–F).
`/result-to-claim` answers **"do the numbers semantically support the claim?"** (statistical / scope reasoning).

The two are intentionally separate. Downstream skills typically read both:

```
if EXPERIMENT_AUDIT.json exists:
    read integrity_status                      # methodology honesty
    attach to /result-to-claim verdict as a sidecar field, e.g.:
        {claim_supported: "yes", integrity_status: "warn"}
    if integrity_status == "fail":
        downgrade verdict display: "yes [INTEGRITY CONCERN]"
else:
    integrity_status = "unavailable"
    mark verdict as "provisional — no integrity audit"
```

`/experiment-audit` does NOT emit `claim_supported`. Its `overall_verdict` IS the target claim's integrity verdict (PASS/WARN/FAIL); to cover N claims, invoke it N times.

### Read by /paper-write (if exists)

```
if EXPERIMENT_AUDIT.json exists AND integrity_status == "fail":
    add footnote to affected claims: "Note: integrity audit flagged concerns with this evaluation"
```

## Key Rules

- **Reviewer independence**: executor collects paths, reviewer judges. Period.
- **Never block**: warn loudly, never halt the pipeline.
- **File-as-switch**: no EXPERIMENT_AUDIT.md = skill was never run = zero impact on existing behavior.
- **Cross-model**: the reviewer MUST be a different model family from the executor.
- **Honest about limits**: the audit catches common patterns, not all possible fraud. It is a safety net, not a guarantee.

## Acknowledgements

Motivated by community-reported integrity issues (#57, #131) where executor agents created fake ground truth and self-normalized scores.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
