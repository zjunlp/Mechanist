---
name: idea-creator
description: Generate and rank research ideas given a broad direction. Use when user says "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent, mcp__llm-chat__chat
---

# Research Idea Creator

Generate publishable research ideas for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research ideas. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

## Constants

- **PILOT_MAX_HOURS = 4** — Skip any pilot estimated to take > 4 hours per GPU. Flag as "needs manual pilot".
- **PILOT_TIMEOUT_HOURS = 6** — Hard timeout: kill pilots exceeding 6 hours. Collect partial results if available.
- **MAX_PILOT_IDEAS = 6** — Pilot at most 6 ideas in parallel. Additional ideas are validated on paper only.
- **MAX_TOTAL_GPU_HOURS = 10** — Total GPU budget for all pilots combined.
- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP for brainstorming (Phase 2 idea generation) and review (Phase 4 devil's-advocate critique). Model defers to `LLM_MODEL` env. Always ask the external reviewer for strict, high-rigor feedback. Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.

> 💡 Override via argument, e.g., `/idea-creator "topic" — pilot budget: 4h per idea, 20h total`.

## Workflow

### Phase 1: Load Landscape + Banlist (produced by /research-lit)

> **Division of labor.** `/research-lit` is the **canonical owner** of the landscape and banlist. Its **Step 0** reads any existing prior banlist and its **Step 5** synthesizes everything into `idea-stage/LANDSCAPE.md` — paper table + 3-5 paragraph narrative + structural gaps + a **`## 5. Banlist — Failed Ideas`** section. This skill does **not** survey the literature; it consumes that file.

**Path A — auto-claim chain (the normal path).**
If `idea-stage/LANDSCAPE.md` exists non-empty, **`Read` it**. Treat it as the canonical landscape, and treat its **`## 5. Banlist — Failed Ideas`** section as ideas NOT to regenerate. Do **not** re-survey. This is the explicit auditable source and avoids drift if an in-context survey would later be summarized away in a long session.

**Path B — standalone (`LANDSCAPE.md` absent).**
Run `/research-lit "$ARGUMENTS"` first — it owns the survey and banlist — then **`Read`** the `idea-stage/LANDSCAPE.md` it writes.

Log: `[phase-1] loaded landscape + banlist from idea-stage/LANDSCAPE.md`.

### Phase 2: Idea Generation (brainstorm with external LLM)

Use the external LLM via llm-chat MCP for divergent thinking. The landscape **and the banlist** were loaded in Phase 1 from `idea-stage/LANDSCAPE.md` — paste **both** into the brainstorm prompt below. The external model is **stateless** and sees only what you paste, so the banlist MUST be included or it will re-propose already-failed ideas. Always ask the external reviewer for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    You are a senior ML researcher brainstorming research ideas.

    Research direction: [user's direction]

    Here is the current landscape:
    [paste structured paper table + landscape narrative from LANDSCAPE.md (Phase 1)]

    Key gaps identified:
    [paste structural gaps from LANDSCAPE.md (Phase 1)]

    Already-tried ideas that FAILED — do NOT regenerate these or close variants:
    [paste the "## 5. Banlist — Failed Ideas" section from LANDSCAPE.md (Phase 1); write "(none — no prior banlist)" if empty]

    Generate 8-12 concrete research ideas. For each idea:
    1. One-sentence summary
    2. Core hypothesis (what you expect to find and why)
    3. Minimum viable experiment (what's the cheapest way to test this?)
    4. Expected contribution type: empirical finding / new method / theoretical result / diagnostic
    5. Risk level: LOW (likely works) / MEDIUM (50-50) / HIGH (speculative)
    6. Estimated effort: days / weeks / months

    Prioritize ideas that are:
    - Testable with moderate compute (8x RTX 3090 or less)
    - Likely to produce a clear positive OR negative result (both are publishable)
    - Not "apply X to Y" unless the application reveals genuinely surprising insights
    - Differentiated from the papers in the landscape, and NOT in the failed-ideas banlist above

    Be creative but grounded. A great idea is one where the answer matters regardless of which way it goes.
```

Save the full raw response verbatim. `llm-chat` is stateless — follow-up rounds must include a verbatim summary of this response in the new prompt.

### Phase 3: First-Pass Filtering

For each generated idea, quickly evaluate:

1. **Feasibility check**: Can we actually run this experiment with available resources?
   - Compute requirements (estimate GPU-hours)
   - Data availability
   - Implementation complexity
   - Skip ideas requiring > 1 week of GPU time or unavailable datasets

2. **Novelty quick-check**: For each idea, do 2-3 targeted searches to see if it's already been done. Full `/novelty-check` comes later for survivors.

3. **Impact estimation**: Would a reviewer care about the result?
   - "So what?" test: if the experiment succeeds, does it change how people think?
   - Is the finding actionable or just interesting?

Eliminate ideas that fail any of these. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + external LLM cross-verification) for each idea

2. **Critical review**: Use the external reviewer via `mcp__llm-chat__chat` (include Phase 2's verbatim ideas response in the prompt since llm-chat is stateless):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with novelty check results]

   For each, play devil's advocate:
   - What's the strongest objection a reviewer would raise?
   - What's the most likely failure mode?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually work on?
   ```

3. **Combine rankings**: Merge your assessment with the external reviewer's ranking. Select top 2-3 ideas for pilot experiments.

### Phase 5: Parallel Pilot Experiments (for top 2-3 ideas)

Before committing to a full research effort, run cheap pilot experiments to get empirical signal. This is the key differentiator from paper-only validation.

1. **Design pilots**: For each top idea, define the minimal experiment that would give a positive or negative signal:
   - Single seed, small scale (e.g., small dataset subset, fewer epochs)
   - Target: 30 min - PILOT_MAX_HOURS per pilot on 1 GPU
   - **Estimate GPU-hours BEFORE launching.** If estimated time > PILOT_MAX_HOURS, reduce scale (fewer epochs, smaller subset) or flag as "needs manual pilot"
   - Clear success metric defined upfront (e.g., "if metric improves by > 1%, signal is positive")

2. **Deploy in parallel**: Use `/run-experiment` to launch pilots on different GPUs simultaneously:
   ```
   GPU 0: Pilot for Idea 1
   GPU 1: Pilot for Idea 2
   GPU 2: Pilot for Idea 3
   ```
   Use `run_in_background: true` to launch all at once.

3. **Collect results**: Use `/monitor-experiment` to check progress. If any pilot exceeds PILOT_TIMEOUT_HOURS, kill it and collect partial results. Once all pilots complete (or timeout), compare:
   - Which ideas showed positive signal?
   - Which showed null/negative results? (eliminate or deprioritize)
   - Any surprising findings that suggest a pivot?
   - Total GPU-hours consumed (track against MAX_TOTAL_GPU_HOURS budget)

4. **Re-rank based on empirical evidence**: Update the idea ranking using pilot results. An idea with strong pilot signal jumps ahead of a theoretically appealing but untested idea.

Note: Skip this phase if the ideas are purely theoretical or if no GPU is available. Flag skipped ideas as "needs pilot validation" in the report.

### Phase 6: Output — Ranked Idea Report

Write a structured report to `idea-stage/IDEA_REPORT.md`:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [date]
**Ideas evaluated**: X generated → Y survived filtering → Z piloted → W recommended

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Recommended Ideas (ranked)

### Idea 1: [title]
- **Hypothesis**: [one sentence]
- **Minimum experiment**: [concrete description]
- **Expected outcome**: [what success/failure looks like]
- **Impact**: X/10 — why it matters: [importance + who would care]
- **Novelty**: X/10 — closest work: [paper]
- **Feasibility**: [compute, data, implementation estimates]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: empirical / method / theory / diagnostic
- **Pilot result**: [POSITIVE: metric +X% / NEGATIVE: no signal / SKIPPED: needs GPU]
- **Reviewer's likely objection**: [strongest counterargument]
- **Why we should do this**: [1-2 sentences]

### Idea 2: [title]
...

## Eliminated Ideas (for reference)
| Idea | Reason eliminated |
|------|-------------------|
| ... | Already done by [paper] |
| ... | Requires > 1 week GPU time |
| ... | Result wouldn't be interesting either way |

## Pilot Experiment Results
| Idea | GPU | Time | Key Metric | Signal |
|------|-----|------|------------|--------|
| Idea 1 | GPU 0 | 45 min | +2.3% CE | POSITIVE |
| Idea 2 | GPU 1 | 30 min | -0.1% CE | NEGATIVE |
| Idea 3 | GPU 2 | 1.5 hr | +0.8% CE | WEAK POSITIVE |

## Suggested Execution Order
1. Start with Idea 1 (positive pilot signal, lowest risk)
2. Idea 3 as backup (weak signal, may need larger scale to confirm)
3. Idea 2 eliminated by pilot — negative result documented

## Next Steps
- [ ] Scale up Idea 1 to full experiment (multi-seed, full dataset)
- [ ] If confirmed, invoke /auto-iteration-loop for full iteration
```

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- The user provides a DIRECTION, not an idea. Your job is to generate the ideas.
- Quantity first, quality second: brainstorm broadly, then filter ruthlessly.
- A good negative result is just as publishable as a positive one. Prioritize ideas where the answer matters regardless of direction.
- Don't fall in love with any idea before validating it. Be willing to kill ideas.
- Always estimate compute cost. An idea that needs 1000 GPU-hours is not actionable for most researchers.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "NLP", "computer vision", "reinforcement learning"), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the problem, domain, and constraint — e.g., "factorized gap in discrete diffusion LMs" or "sample efficiency of offline RL with image observations". Without sufficient specificity, generated ideas will be too vague to run experiments on.

## Composing with Other Skills

After this skill produces the ranked report:
```
/idea-creator "direction"     → ranked ideas
/novelty-check "top idea"     → deep novelty verification (already done in Phase 4, but user can re-run)
/research-review "top idea"   → external critical feedback
implement                     → write code
/run-experiment               → deploy to GPU
/auto-iteration-loop             → iterate until submission-ready
```

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
