---
name: research-review
description: "Get rigorous external-LLM criticism of research ideas, papers, plans, or experimental results."
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, Agent, mcp__llm-chat__chat
---

## Host compatibility

Before acting on a historical host tool name, read and apply the bundled `shared-references/host-compatibility.md`. Use the active host capability by meaning; never fabricate or call an unavailable literal tool name.

# Research Review via llm-chat MCP

Get a multi-round critical review of research work from an external LLM.

## Constants

- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback.
- Override with `— reviewer: oracle-pro` via Oracle MCP.

## Reviewer LLM Configuration (mandatory, read first)

Read and follow `../shared-references/reviewer-runtime.md`. The MCP server owns provider configuration and credentials; this skill never reads host config or project files for secrets.

## Context: $ARGUMENTS

## Prerequisites

- The active host exposes the bundled `llm-chat` MCP chat tool.
- Reviewer credentials are present in the environment that launched the host.

## Workflow

### Step 1: Gather Research Context
Before calling the external reviewer, compile a comprehensive briefing:
1. Read project narrative documents (e.g., STORY.md, README.md, paper drafts)
2. Read any memory/notes files for key findings and experiment history
3. Identify: core claims, methodology, key results, known weaknesses

### Step 2: Initial Review (Round 1)
Send a detailed prompt. Always ask the external reviewer for strict, high-rigor feedback.

```
mcp__llm-chat__chat:
  prompt: |
    [Full research context + specific questions]

    Please act as a senior ML reviewer (NeurIPS/ICML level). Identify:
    1. Logical gaps or unjustified claims
    2. Missing experiments that would strengthen the story
    3. Narrative weaknesses
    4. Whether the contribution is sufficient for a top venue
    Please be brutally honest.
```

### Step 3: Iterative Dialogue (Rounds 2-N)
`llm-chat` is stateless — every call is a fresh conversation. For follow-up rounds, include a verbatim summary of the prior round's review (criticisms, author responses, open questions) inside the new `mcp__llm-chat__chat` prompt.

For each round:
1. **Respond** to criticisms with evidence/counterarguments
2. **Ask targeted follow-ups** on the most actionable points
3. **Request specific deliverables**: experiment designs, paper outlines, claims matrices

Key follow-up patterns:
- "If we reframe X as Y, does that change your assessment?"
- "What's the minimum experiment to satisfy concern Z?"
- "Please design the minimal additional experiment package (highest acceptance lift per GPU week)"
- "Please write a mock NeurIPS/ICML review with scores"
- "Give me a results-to-claims matrix for possible experimental outcomes"

### Step 4: Convergence
Stop iterating when:
- Both sides agree on the core claims and their evidence requirements
- A concrete experiment plan is established
- The narrative structure is settled

### Step 5: Document Everything
Save the full interaction and conclusions to a review document in the project root:
- Round-by-round summary of criticisms and responses
- Final consensus on claims, narrative, and experiments
- Claims matrix (what claims are allowed under each possible outcome)
- Prioritized TODO list with estimated compute costs
- Paper outline if discussed

Update project memory/notes with key review conclusions.

## Key Rules

- Always ask the external reviewer for strict, high-rigor feedback
- Send comprehensive context in Round 1 — the external model cannot read your files
- Be honest about weaknesses — hiding them leads to worse feedback
- Push back on criticisms you disagree with, but accept valid ones
- Focus on ACTIONABLE feedback — "what experiment would fix this?"
- llm-chat is stateless — include prior-round context in every follow-up prompt
- The review document should be self-contained (readable without the conversation)

## Prompt Templates

### For initial review:
"I'm going to present a complete ML research project for your critical review. Please act as a senior ML reviewer (NeurIPS/ICML level)..."

### For experiment design:
"Please design the minimal additional experiment package that gives the highest acceptance lift per GPU week. Our compute: [describe]. Be very specific about configurations."

### For paper structure:
"Please turn this into a concrete paper outline with section-by-section claims and figure plan."

### For claims matrix:
"Please give me a results-to-claims matrix: what claim is allowed under each possible outcome of experiments X and Y?"

### For mock review:
"Please write a mock NeurIPS review with: Summary, Strengths, Weaknesses, Questions for Authors, Score, Confidence, and What Would Move Toward Accept."

## Review Tracing

After each `mcp__llm-chat__chat` reviewer call, save the trace following `shared-references/review-tracing.md`. Write files directly to `.mechanist/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
