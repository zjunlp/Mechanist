---
name: novelty-check
description: Verify research idea novelty against recent literature. Use when user says "novelty check", "check novelty", or wants to verify a research idea is novel before implementing.
argument-hint: [method-or-idea-description]
allowed-tools: WebSearch, WebFetch, Grep, Read, Glob, mcp__llm-chat__chat
---

# Novelty Check Skill

Check whether a proposed method/idea has already been done in the literature: **$ARGUMENTS**

## What Counts as Novelty

An idea qualifies as novel if it does ANY of the following:
- proposes a new method, theory, or task;
- applies an existing method to a *different* domain/setting that has not been systematically studied — note that applying X to Y *within the same domain* is NOT novel unless the application reveals surprising insights;
- gives a new explanation, mechanism, or finding for an existing problem;
- uses a new experimental setting, problem definition, or dataset.

## Constants

- REVIEWER_BACKEND = `llm-chat` — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback.

## Instructions

Given a method description, systematically verify its novelty:

### Phase A: Extract Key Claims
1. Read the user's method description
2. Identify 3-5 core technical claims that would need to be novel:
   - What is the method?
   - What problem does it solve?
   - What is the mechanism?
   - What makes it different from obvious baselines?

### Phase B: Multi-Source Literature Search
For EACH core claim, search using ALL available sources:

1. **Web Search** (via `WebSearch`):
   - Search arXiv, Google Scholar, Semantic Scholar
   - Use specific technical terms from the claim
   - Try at least 3 different query formulations per claim
   - Use 2024–2026 year filters

2. **Known paper databases**: Check against:
   - ICLR 2025/2026, NeurIPS 2025, ICML 2025/2026
   - Recent arXiv preprints (2025-2026)

3. **Read abstracts**: For each potentially overlapping paper, WebFetch its abstract and related work section

### Phase C: Cross-Model Verification
Call the external LLM reviewer via `mcp__llm-chat__chat`. Always ask the external reviewer for strict, high-rigor feedback.

Prompt should include:
- The proposed method description
- All papers found in Phase B
- Ask: "Is this method novel? What is the closest prior work? What is the delta?"

### Phase D: Novelty Report
Output a structured report:

```markdown
## Novelty Check Report

### Proposed Method
[1-2 sentence description]

### Core Claims
1. [Claim 1] — Novelty: HIGH/MEDIUM/LOW — Closest: [paper]
2. [Claim 2] — Novelty: HIGH/MEDIUM/LOW — Closest: [paper]
...

### Closest Prior Work
| Paper | Year | Venue | Overlap | Key Difference |
|-------|------|-------|---------|----------------|

### Overall Novelty Assessment
- Score: X/10
- Recommendation: PROCEED / PROCEED WITH CAUTION / ABANDON
- Key differentiator: [what makes this unique, if anything]
- Risk: [what a reviewer would cite as prior work]

### Suggested Positioning
[How to frame the contribution to maximize novelty perception]
```

### Important Rules
- Be BRUTALLY honest — false novelty claims waste months of research time.
- Check both the method AND the experimental setting for novelty.
- If the method is not novel but the FINDING would be, say so explicitly.
- Always check the most recent 6 months of arXiv — the field moves fast.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
