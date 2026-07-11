---
name: verify-pick-alternatives
description: "Sub-skill of /auto-verify. Given a claim, choose one method swap, one dataset swap, and one model swap that most strongly stress-test the claim. Harvests candidates from existing research; calls /research-lit only when coverage is thin. Use when user says \"pick swaps for claim\", \"choose alternatives\", or when invoked by /auto-verify."
argument-hint: [claim-id — claim-statement]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, Skill, mcp__llm-chat__chat
---

# Verify: Pick Alternatives

Sub-skill of `/auto-verify`. Chooses the variants that will test claim robustness along three independent dimensions: method, dataset, model.

For: **$ARGUMENTS**

## Purpose

`/auto-verify` needs swap candidates that genuinely stress the claim — not cosmetic re-runs. This skill:

1. Harvests candidates from existing project research (idea-stage, refine-logs, findings.md, research-wiki if present)
2. Checks each dimension (method / dataset / model) for a minimum coverage threshold
3. Calls `/research-lit` only for dimensions below the threshold — a focused top-up, not a full survey
4. Hands the candidate pool to the external LLM reviewer, who picks and ranks the variants by "strongest independent test of the claim"
5. Emits a structured variant list that `/auto-verify` drops into `verify/<claim_dir>/PLAN.md`

## Constants

- **DIMENSIONS = `method,dataset,model`** — Comma-separated subset of `{method, dataset, model}`, passed through from `/auto-verify`. Dimensions not in the list get zero variants — no candidate harvesting, no reviewer prompts for them. Parse from `$ARGUMENTS` tail: the invoker passes `— dimensions: method,dataset`. If the parameter is absent, default to all three axes.

  **Variant count = `len(DIMENSIONS)`**, exactly. One swap per listed axis, no scaling. There is no separate "effort" knob; deeper analyses (multi-seed within an axis, 2-factor cross-axis interactions) belong in `/ablation-planner`, not here.
- **MIN_CANDIDATES_PER_DIMENSION = 2** — if fewer than 2 credible candidates exist in any ACTIVE dimension, invoke `/research-lit` for that dimension. Inactive dimensions are skipped entirely.
- **RESEARCH_LIT_SCOPE = `focused`** — when invoked, `/research-lit` runs in focused mode (≤ 6 papers, single dimension) to avoid a full-depth survey.
- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP. Always ask for strict, high-rigor feedback.

## Inputs

Parse `$ARGUMENTS` as `[claim-id] — [claim-statement] [— dimensions: <subset>]`. The trailing `— dimensions:` clause is optional; if present, split on `,`, lowercase each entry, validate against `{method, dataset, model}`, reject unknown axes, and store as the active dimension list. If absent, the active list defaults to all three axes.

If only a claim id is given, look up the statement in:

1. `refine-logs/EXPERIMENT_PLAN.md` (Claim Map section)
2. `refine-logs/FINAL_PROPOSAL.md` (claims list)
3. `research-wiki/claims/<claim-id>.md` (if present)

Also read:
- **Main-experiment setup** from `refine-logs/EXPERIMENT_LOG.md` or `EXPERIMENT_TRACKER.md`: the method / dataset / model that currently back the claim
- **Research harvest sources**:
  - `idea-stage/IDEA_REPORT.md` — ranked ideas, often includes rejected alternatives
  - `idea-stage/REF_PAPER_SUMMARY.md` — reference paper context (if present)
  - `refine-logs/round_*.md` — refinement notes mentioning alternatives considered
  - `findings.md` — cross-stage discoveries (append-only)
  - `.mechanist/traces/research-lit/` — raw traces from any prior `/research-lit` run
  - `research-wiki/` index (if present)
  - `skills/mechanism-skills/` — five mechanistic-interpretability method families (Magnitude Analysis, Vocabulary Projection, Probing, Gradient Detection, Causal Attribution). Consult when the claim is about LLM internals (a specific layer, head, neuron, feature, or circuit). Start from `skills/mechanism-skills/SKILL.md` to pick the family, then read the family's sub-skill for submethod candidates.

## Workflow

### Phase 1: Harvest Candidates from Existing Research

**Harvest only the active dimensions.** Iterate over the `DIMENSIONS` list parsed above and build a bucket table per active axis — if `DIMENSIONS = ["method"]`, produce only the Method table; skip the Dataset and Model tables entirely. Inactive dimensions are not mentioned in the candidate pool, skipped in Phase 2/3 coverage checks, omitted from the Phase 4 reviewer prompt, and excluded from the Phase 5 emitted output. For claims about LLM internals, treat `skills/mechanism-skills/` as a first-class source alongside `idea-stage/` and prior `research-lit` outputs — read the main experiment's family sub-skill and pick a different submethod from the **same family** (e.g., main experiment `probing/residual-stream-states` → swap to `probing/sae-feature-activation-state`; main experiment `causal-attribution/ablation` → swap to `causal-attribution/attribution-patching`). The verify pass deliberately constrains the method dimension to within-family swaps; cross-family comparisons are a separate evaluation and out of scope here.

```markdown
## Candidate Pool (harvested)

### Method candidates
| # | Name | Source | Notes (mechanism, compute, compatibility) |
|---|------|--------|-------------------------------------------|
| M1 | [method name] | IDEA_REPORT.md#idea-3 | [one line: what it does, why it might swap in] |
| M2 | [method name] | round_2_reviewer.md | [...] |

### Dataset candidates
| # | Name | Source | Notes (distribution, task framing, construct) |
|---|------|--------|-----------------------------------------------|
| D1 | [dataset] | REF_PAPER_SUMMARY.md | [distribution difference from the main experiment] |

### Model candidates
| # | Name | Source | Notes (family, scale, accessibility) |
|---|------|--------|--------------------------------------|
| Mdl1 | [model] | IDEA_REPORT.md#idea-7 | [different family/scale] |
```

**"Credible" means**: named in a source, tied to a mechanism or construct that actually differs from the main experiment, and implementable with available compute.

Drop candidates that:
- Are identical to the main experiment under a different name
- Require compute beyond the project budget
- Are paywalled / gated in a way the project can't satisfy

### Phase 2: Coverage Check per Dimension

For each dimension (method / dataset / model), count credible candidates.

```
if count(dimension_candidates) < MIN_CANDIDATES_PER_DIMENSION:
    mark dimension as "needs topup"
```

If any dimension needs topup, proceed to Phase 3. Otherwise skip to Phase 4.

### Phase 3: Focused Research Top-Up (only for gaps)

For each gap dimension, invoke `/research-lit` in focused mode:

```
/research-lit "alternative [method | dataset | model] to [main-experiment choice] that could test the claim: [claim statement]" — extra: semantic-scholar
```

**Guidance on queries:**
- **Method swap query** — emphasize "same family, different submethod." e.g., "alternative probing decoders for activation-based sentiment classification (SAE-feature probe vs residual-stream probe)" or "alternative causal-attribution submethods for neuron-level sentiment evidence (mean ablation vs activation patching)". For mechanism claims, the candidate **must** come from the main experiment's `skills/mechanism-skills/<family>/` sub-skill; cross-family alternatives are out of scope for this verify pass.
- **Dataset swap query** — emphasize "same construct, different distribution." e.g., "benchmarks measuring covert coordination beyond [main-experiment dataset]"
- **Model swap query** — emphasize "different family or scale, same modality." e.g., "open-weight LLMs in the 30B range comparable to Qwen3-32B-AWQ for multi-agent activation analysis"

For each returned paper, append to the candidate pool with `Source: research-lit/<query-id>`.

If `/research-lit` returns fewer than `MIN_CANDIDATES_PER_DIMENSION` for a dimension after top-up, accept the smaller pool and flag it in the reviewer prompt (Phase 4) so the reviewer knows the constraint.

### Phase 4: Reviewer Ranks and Selects

Send the **active-dimension** candidate pools to the external reviewer. Do not mention skipped dimensions in the prompt — it should not suggest selections in axes the user excluded. The reviewer's job is not to suggest candidates — it is to pick and rank from the pool we supply, restricted to the active dimension list. Always ask for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    You are a rigorous ML reviewer selecting variants to stress-test a claim.

    ## Claim
    [claim-id]: [claim statement]

    ## Main-experiment setup
    - Method: [M0] — [one-line description]
    - Dataset: [D0] — [construct, distribution, size]
    - Model: [Mdl0] — [family, scale]
    - Main-experiment metric: [name = value]

    ## Candidate pool
    [paste the three-bucket table from Phase 1, augmented by Phase 3 topups]

    ## Your task
    Pick exactly ONE variant per dimension (method / dataset / model) from the pool.
    Rank them by "how much a reviewer would trust the claim if it survived this swap."

    For each selection answer:
    1. selected_name — from the pool
    2. justification — why this is a STRONG independent test of the claim (not a trivial re-run)
    3. expected_if_claim_holds — what the variant's metric should look like if the claim is true
    4. expected_if_claim_fails — what would indicate the claim is confined to the main-experiment setup
    5. risk — what could confound the comparison (and how to control for it)
    6. trust_rank — 1 (strongest test), 2, 3

    Also:
    - If ANY dimension's pool is too weak for a strong test, say so and suggest what a strong
      candidate would look like — do NOT pick a weak swap just to fill the slot.
    - For the method dimension, the candidate MUST come from the main experiment's mechanism-skills family (e.g., Probing → Probing, Causal Attribution → Causal Attribution). Cross-family candidates are out of scope and must be rejected.
    - Do not select candidates that share the main experiment's core mechanism under a different name. Within-family swaps must still pick a genuinely different submethod (different fitting procedure, different intervention semantics, different evidence type) — not a renamed re-run.
    - Be strict. Reviewers will challenge weak verify setups.
```

Apply the reviewer's output:
- Record selected variants with their trust ranks
- If the reviewer flags any dimension as "pool too weak":
  - Loop back to Phase 3 with a more specific research query (max 1 extra round)
  - If still weak after the extra round, mark that dimension as `SKIPPED` in the output and document why — `/auto-verify` will see this and reduce the variant count for the claim
- If llm-chat MCP is unavailable, CC picks the candidate with the clearest mechanism-level difference from the main experiment and labels the selection `[pending external review]`

### Phase 5: Emit Structured Output

**Only write rows for active dimensions.** If `DIMENSIONS = ["method"]` the Variants table has a single row (method). Add a "Dimensions scope" line under Main-experiment that names the active list and lists the excluded axes explicitly (so downstream consumers of PLAN.md do not misread the missing rows as coverage gaps).

Write the final variant list to `verify/<claim_dir>/PLAN.md`. Format:

```markdown
## Claim [claim-id]: [statement]

### Main experiment
- Method: [M0], Dataset: [D0], Model: [Mdl0] → [metric = value]

### Variants

| # | Dimension | Swap (replaces) | Justification | Expected if claim holds | Expected if claim fails | Risk / confound control | Trust rank | Source |
|---|-----------|-----------------|---------------|-------------------------|-------------------------|-------------------------|------------|--------|
| 1 | method | [M1] (← [M0]) | [one line] | [metric trajectory] | [metric trajectory] | [control] | 1 | [source] |
| 2 | dataset | [D1] (← [D0]) | [one line] | [...] | [...] | [control] | 2 | [source] |
| 3 | model | [Mdl1] (← [Mdl0]) | [one line] | [...] | [...] | [control] | 3 | [source] |

### Skipped Dimensions (if any)
- [dimension]: pool too weak — strong candidate would be [description]. Topup needed before re-running /auto-verify on this claim.

### Success Criterion (inherited from /auto-verify)
Each variant's claim_supported verdict is judged by /result-to-claim against the frozen main-experiment claim statement.
```

Append the candidate-pool snapshot (from Phase 1 + Phase 3) to `verify/<claim_dir>/PLAN.md` under a collapsible "Candidate Pool" section so future re-runs have a traceable audit trail.

Return control to `/auto-verify` with a short status line:

```
✅ Variants selected for [claim-id]: [method:M1], [dataset:D1], [model:Mdl1]
   Skipped: [dimension] (reason) — if any
   Top-up research-lit calls: [count]
```

## Output Protocols

> Follow these shared protocols:
> - **[Output Versioning Protocol](../../shared-references/output-versioning.md)** — timestamped first, then fixed name
> - **[Output Manifest Protocol](../../shared-references/output-manifest.md)** — log PLAN.md writes to MANIFEST.md
> - **[Output Language Protocol](../../shared-references/output-language.md)**

## Key Rules

- **Harvest before you search.** Do not call `/research-lit` until the existing project research has been scanned. Most mature projects already have alternatives documented in IDEA_REPORT.md or refinement notes.
- **Focused top-ups only.** When `/research-lit` is invoked, constrain it to ≤ 6 papers on a single dimension. A full survey is not the goal — filling a specific gap is.
- **The reviewer picks from the pool.** Do not let the external reviewer invent candidates out of thin air; its job is selection + ranking, not research. This keeps the pool auditable.
- **One swap per dimension.** Default output is exactly `len(DIMENSIONS)` variants — three with the default `{method, dataset, model}`, one when narrowed to `method` alone. No EFFORT multiplier. Multi-seed runs or 2-factor cross-axis swaps live in `/ablation-planner`, not here.
- **Method swap stays within family — *unless* the main experiment is behavioral-only.** For mechanism claims, the method candidate MUST come from the main experiment's mechanism-skills family (Probing → Probing, Causal Attribution → Causal Attribution, etc.). A swap to a different family answers a different question (does the claim survive a totally different mechanism?) and belongs in a separate sweep — not here. **Carve-out**: when `refine-logs/MECHANISM_ROUTING.md` is `routing: not-applicable` (behavioral-only proposal — no mechanism family was committed in `/auto-experiment` Phase 0), the within-family constraint is dropped. Method swap candidates can come from any reasonable alternative method for the main experiment's task; the reviewer still ranks by "strongest independent test of the claim". The parent `/auto-verify` Phase 0.5 makes this routing decision and forwards the active mode to this skill.
- **Drop look-alikes.** A candidate that shares the main experiment's core mechanism under a different name is not a swap — it's a re-run. Reject it. Within-family swaps must still pick a genuinely different submethod, not a renamed re-run.
- **Fair-comparison control is part of the variant spec.** Every emitted variant must state its confound-control strategy (e.g., "re-run the main experiment with matched batch size on the larger model"). Without it, the variant is under-specified.
- **Weak-pool honesty.** If a dimension's pool is genuinely thin even after top-up, mark it `SKIPPED` and explain — do not pick a weak swap to fill the slot. `/auto-verify` will reduce the variant count, and the verify report will say so plainly.
- **DIMENSIONS is hard.** Axes the parent explicitly excluded via `— dimensions: ...` are not optional: zero variants, zero harvesting, zero reviewer prompts. Do not pad the output by promoting dropped axes to "optional" or "noted" swaps. The scope was the user's call; respect it.

## Composing with Parent and Siblings

```
/auto-verify [claim-id]                     ← parent
  └── /verify-pick-alternatives        ← you are here
        └── /research-lit              ← called only for dimensions below coverage threshold
```

This sub-skill is not meant to be called standalone often — it assumes `/auto-verify` has already parsed target claims and loaded project context. If invoked directly, it still works but will re-read the same inputs `/auto-verify` would read.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace per `shared-references/review-tracing.md` to `.mechanist/traces/verify-pick-alternatives/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
