---
name: result-to-claim
description: Use when experiments complete to judge what claims the results support, what they don't, and what evidence is still missing. The external LLM reviewer (via llm-chat MCP) evaluates results against intended claims and routes to next action (pivot, supplement, or confirm). Use after experiments finish — before writing the paper or running ablations.
argument-hint: [experiment-description-or-wandb-run]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, mcp__llm-chat__chat
---

# Result-to-Claim Gate

Experiments produce numbers; this gate decides what those numbers *mean*. Collect results from available sources, get an external-LLM judgment (via llm-chat MCP), then auto-route based on the verdict.

## Context: $ARGUMENTS

## When to Use

- After a set of experiments completes (main results, not just sanity checks)
- Before committing to claims in a paper or review response
- When results are ambiguous and you need an objective second opinion

## Reviewer LLM Configuration (mandatory, read first)

This skill calls an external LLM reviewer. **Never hardcode a model name and never read the reviewer model from `task.md` / project READMEs / source comments.** Project-level files may list available API keys for unrelated purposes (e.g., LLM-as-judge inside experiment code); those are *not* the reviewer config.

Resolve `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` strictly in this priority order before any reviewer call:

1. **Project MCP config** — `${PROJECT_ROOT}/.mcp.json`, field `mcpServers["llm-chat"].env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}`.
2. **User MCP config** — `~/.claude/settings.json`, same field.
3. **Shell environment** — `$LLM_MODEL`, `$LLM_BASE_URL`, `$LLM_API_KEY`.

### Pre-flight check (run before Step 1, mandatory)

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

### Step 1: Collect Results

Gather experiment data from whatever sources are available in the project:

1. **W&B** (preferred): `wandb.Api().run("<entity>/<project>/<run_id>").history()` — metrics, training curves, comparisons
2. **EXPERIMENT_LOG.md**: full results table with baselines and verdicts
3. **EXPERIMENT_TRACKER.md**: check which experiments are DONE vs still running
4. **Log files**: `ssh server "tail -100 /path/to/training.log"` if no other source
5. **docs/research_contract.md**: intended claims and experiment design

Assemble the key information:
- What experiments were run (method, dataset, config)
- Main metrics and baseline comparisons (deltas)
- The intended claim these experiments were designed to test
- Any known confounds or caveats

### Step 2: External LLM Judgment

Send the collected results to the external LLM reviewer for objective evaluation. Always ask the external reviewer for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    RESULT-TO-CLAIM EVALUATION

    I need you to judge whether experimental results support the intended claim.

    Intended claim: [the claim these experiments test]

    Experiments run:
    [list experiments with method, dataset, metrics]

    Results:
    [paste key numbers, comparison deltas, significance]

    Baselines:
    [baseline numbers and sources — reproduced or from paper]

    Known caveats:
    [any confounding factors, limited datasets, missing comparisons]

    Please evaluate:
    1. claim_supported: pass | fail
       — `pass` means the data fully supports the claim as stated.
       — `fail` means the data does NOT fully support the claim. This includes:
           * the claim is refuted by the data
           * the claim is only partially supported (some sub-claims work, others don't)
           * coverage is too narrow for a general claim (e.g., only 1 dataset / 1 model / 1 seed)
           * the direction is right but the magnitude misses the pre-registered pass criterion
           * mixed results across metrics or splits
           * critical baselines / controls are missing
       Use `pass` only when the data unambiguously supports the claim. Anything borderline is `fail`.
    2. what_results_support: what the data actually shows
    3. what_results_dont_support: where the data falls short of the claim
    4. missing_evidence: specific evidence gaps
    5. suggested_claim_revision: if the claim should be strengthened, weakened, or reframed
    6. next_experiments_needed: specific experiments to fill gaps (if any)
    7. confidence: high | medium | low

    Be honest. Do not inflate claims beyond what the data supports.
    A single positive result on one dataset does not support a general claim — that is `fail`, not `pass`.
```

### Step 3: Parse and Normalize

Extract structured fields from the external reviewer's response:

```markdown
- claim_supported: pass | fail
- what_results_support: "..."
- what_results_dont_support: "..."
- missing_evidence: "..."
- suggested_claim_revision: "..."
- next_experiments_needed: "..."
- confidence: high | medium | low
```

### Step 3.5: Check Experiment Integrity (if audit exists)

**Skip this step if `EXPERIMENT_AUDIT.json` does not exist.**

```
if EXPERIMENT_AUDIT.json exists:
    read integrity_status from file
    attach to verdict output:
        integrity_status: pass | warn | fail

    if integrity_status == "fail":
        append to verdict: "[INTEGRITY CONCERN] — audit found issues, see EXPERIMENT_AUDIT.md"
        downgrade confidence to "low" regardless of external reviewer judgment

    if integrity_status == "warn":
        append to verdict: "[INTEGRITY: WARN] — audit flagged potential issues"
else:
    integrity_status = "unavailable"
    verdict is labeled "provisional — no integrity audit run"
    (this does NOT block anything — pipeline continues normally)
```

See `shared-references/experiment-integrity.md` for the full integrity protocol.

### Step 4: Route Based on Verdict

#### `fail` — Claim not (fully) supported

Covers both outright refutation AND partial / borderline support — under the binary scheme, anything short of unambiguous support routes here.

1. Record postmortem in findings.md (Research Findings section):
   - What was tested, what worked, what fell short, hypotheses for why
   - If the gap is narrow (right direction, wrong magnitude / narrow coverage): list what supplementary experiments would close it; re-run result-to-claim after they complete
   - If the gap is wide (claim refuted, wrong direction): list constraints for future attempts (what NOT to try again)
2. Update CLAUDE.md Pipeline Status
3. Decide between three routes:
   - **Narrow the claim** to the subset that IS supported, then re-evaluate
   - **Run supplementary experiments** to fill the gaps and re-evaluate
   - **Pivot** to the next idea from IDEA_CANDIDATES.md
4. **Multiple consecutive `fail` rounds on the same claim** → record analysis in findings.md and lean toward narrowing the claim scope or pivoting.

#### `pass` — Claim supported

1. Record confirmed claim in project notes
2. If ablation studies are incomplete → trigger `/ablation-planner`
3. If all evidence is in → ready for paper writing

## Rules

- **The external LLM is the judge, not CC.** CC collects evidence and routes; the external reviewer evaluates. This prevents post-hoc rationalization.
- Do not inflate claims beyond what the data supports. Borderline / partial results are `fail`, not `pass`; do not round up.
- A single positive result on one dataset does not support a general claim. Be honest about scope.
- If `confidence` is low, treat the judgment as inconclusive and add experiments rather than committing to a claim.
- If llm-chat MCP is unavailable (call fails), CC makes its own judgment and marks it `[pending external review]` — do not block the pipeline.
- Always record the verdict and reasoning in findings.md, regardless of outcome.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
