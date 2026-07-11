---
name: research-review
description: Get a deep critical review of research from an external LLM reviewer via llm-chat MCP. Use when user says "review my research", "help me review", "get external review", or wants critical feedback on research ideas, papers, or experimental results.
argument-hint: [topic-or-scope]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, Agent, mcp__llm-chat__chat
---

# Research Review via llm-chat MCP

Get a multi-round critical review of research work from an external LLM.

## Constants

- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback.
- Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP.

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

## Context: $ARGUMENTS

## Prerequisites

- **llm-chat MCP Server** configured in `~/.claude/settings.json` with `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
- This gives Claude Code access to the `mcp__llm-chat__chat` tool.

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
