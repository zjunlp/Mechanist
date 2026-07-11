---
name: impact-check
description: Assess whether the research problem/behavior is important — its potential value and reach. Use when user says "impact check", "check impact", or wants to judge whether an idea/behavior matters before committing.
argument-hint: [idea-or-behavior-description]
allowed-tools: WebSearch, WebFetch, Grep, Read, Glob, mcp__llm-chat__chat
---

# Impact Check Skill

Check whether a proposed idea studies an *important* problem/behavior — one worth committing effort to: **$ARGUMENTS**

## What Counts as Impact

An idea is high-impact to the extent it does ANY of the following:
- solves an important problem;
- is likely to be widely used or cited by follow-up research;
- could change the direction of a research area;
- helps real applications, industry, society, or cross-disciplinary research;
- reveals an important phenomenon, even if the method is simple.

## Constants

- REVIEWER_BACKEND = `llm-chat` — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback.

## Instructions

Given an idea / behavior description, systematically assess its importance:

### Phase A: Extract the Impact-Bearing Claims
1. Read the description and name the **behavior/phenomenon or problem** under study (not the method).
2. Extract the elements that determine its importance:
   - What problem does it address, and who actually has that problem?
   - What downstream research or applications would build on it if the result holds?
   - What would change — in the field or in practice — if it is true?
   - What is the reach: one narrow setting, a whole research area, or real-world / cross-disciplinary use?
3. State the single strongest one-line case for why it matters.

### Phase B: Assess Impact Along the Dimensions
For EACH impact dimension below, judge how strongly the idea scores and gather supporting evidence (use `WebSearch` / `WebFetch` to check whether the problem is an open/active question, how much attention it gets, and where it would be used):

1. **Important problem** — Is this a problem the field (or a real application) actually needs solved, or a niche curiosity?
2. **Uptake / citation** — Would follow-up research likely build on, use, or cite this? Does it produce a reusable artifact (dataset, method, finding, diagnostic)?
3. **Direction-shifting** — Could the result change how people think about or approach a research area?
4. **Real-world reach** — Does it help applications, industry, society, or cross-disciplinary work?
5. **Phenomenon value** — Even if the method is simple, does the result reveal an important phenomenon?

### Phase C: Cross-Model Verification
Call the external LLM reviewer via `mcp__llm-chat__chat`. Always ask for strict, high-rigor feedback.

Prompt should include:
- The idea / behavior description
- Your per-dimension assessment from Phase B
- Ask: "Is this problem important? Who would care, and how far would the result reach? What is the strongest 'so what?' objection?"

### Phase D: Impact Report
Output a structured report:

```markdown
## Impact Check Report

### Studied Problem/Behavior
[1-2 sentence description — the behavior/problem, not the method]

### Impact Dimensions
1. Important problem — HIGH/MEDIUM/LOW — [why]
2. Uptake / citation — HIGH/MEDIUM/LOW — [why]
3. Direction-shifting — HIGH/MEDIUM/LOW — [why]
4. Real-world reach — HIGH/MEDIUM/LOW — [why]
5. Phenomenon value — HIGH/MEDIUM/LOW — [why]

### Overall Impact Assessment
- Score: X/10
- Recommendation: PROCEED / PROCEED WITH CAUTION / DEPRIORITIZE
- Why it matters: [the strongest case, one sentence]
- "So what?" risk: [the strongest objection a reviewer would raise about importance]
- Who would care: [the audience that benefits most]
```

### Important Rules
- Be BRUTALLY honest — committing to an unimportant problem wastes months of research time.
- "Interesting" is not "important". Apply the **"so what?"** test: if the result came out either way, would anyone change what they do?
- A simple method can be high-impact if it reveals an important phenomenon — do not penalize simplicity.

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
