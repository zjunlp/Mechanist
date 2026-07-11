# Mechanist — Developer Guide

**For contributors modifying skill prompts, agent definitions, or MCP server code.**

> If you just want to **use** Mechanist to run experiments, this is the wrong document — go to the [main README](../README.md) instead. This guide is for developers who want to change how Mechanist works.

---

## Table of Contents

- [Setup](#setup)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone & Launch](#2-clone--launch)
  - [3. Verify](#3-verify)
- [Dev Workflow](#dev-workflow)
- [Experiment Isolation](#experiment-isolation)

---

## Setup

### 1. Prerequisites

Complete the base installation steps from the [main README](../README.md#-installation) first:

- Install Claude Code and log in
- Install uv
- Create the `scientist` conda environment
- Configure environment variables (`LLM_API_KEY`, etc.)

Come back here once those are done.

### 2. Clone & Launch

Clone the repository and launch Claude Code with `--plugin-dir` pointing at it:

```bash
git clone https://github.com/zjunlp/Mechanist.git
```

```bash
# Create a working directory (anywhere — recommended: next to the repo)
mkdir exp && cd exp

# Launch with --plugin-dir so Claude Code reads the plugin from your local clone
claude --model claude-opus-4-7 --plugin-dir ../Mechanist
```

```
<dir>/
├── Mechanist/   # your local clone (plugin source)
└── exp/         # your experiment working directory
    └── task.md
```

This is the key difference from user-mode: `--plugin-dir` tells Claude Code to load the plugin directly from your local filesystem, so any edits you make are picked up immediately.

### 3. Verify

Same checks as user-mode:

- Run `/help` — Mechanist skills should appear.
- Run `/mcp` — `llm-chat` and `mechanic-db` should be **connected**.

---

## Dev Workflow

When you edit Mechanist source files, what it takes for changes to take effect depends on what you changed:

| What you changed | How to apply |
|:---|:---|
| `skills/`, `agents/`, slash commands, prompt text | Run `/reload-plugins` in the Claude Code session. (Claude Code also auto-refreshes skills within 3–5 seconds; `/reload-plugins` is the manual force-reload.) |
| MCP / helper server Python code (`mcp-servers/`) | **Restart Claude Code.** `/reload-plugins` does not restart already-running server processes. |
| Plugin manifest (`plugin.json`) / MCP config | **Restart Claude Code.** |
| Environment variables (`LLM_API_KEY`, etc.) | Edit in the launching shell and **restart Claude Code** — already-running servers won't pick up changes mid-session. |

> [!IMPORTANT]
> When contributing changes back to the repository, **do not upload your experiment case contents** (`exp/` directories, `task.md` with private data, etc.).

---

## Experiment Isolation

When running the same experiment multiple times (e.g., `exp1`, `exp2`, `exp3`), the agent may inadvertently read artifacts from previous runs and contaminate the current run. In dev mode this is especially important since you are likely iterating on the same experiment.

Two mechanisms are available to control the agent's file access scope. Use either or both.

### Tier 1: Prompt-level soft constraint

Add a prohibition to `task.md`:

```text
Do not read other experiment directories. Do not borrow data, experiment
designs, group assignments, or other information from previous runs.
```

The orchestrator injects this directive into every sub-agent's dispatch prompt. This is a **prompt-level constraint** — it depends on the model following instructions.

### Tier 2: Config-file hard constraint

Place a `.claude/settings.local.json` in the **current experiment directory** to deny read access to all historical runs at the filesystem permission level.

Layout (assuming the current round is `exp/`):

```
<project-dir>/
└── exp/
    └── .claude/
        └── settings.local.json     ← only affects sessions launched from exp/
```

Example:

```json
{
  "permissions": {
    "deny": [
      "Read(/absolute/path/to/exp1/**)",
      "Read(/absolute/path/to/exp2/**)",
      "Read(/absolute/path/to/other_old_exp/**)"
    ]
  }
}
```

Key points:

- Paths must be **absolute** and end with `/**` to match all descendant files.
- For each new round, create a fresh `settings.local.json` in the new directory and append all historical experiment directories to `deny`.
- This file only affects Claude Code sessions launched from this directory; it does not affect other projects.

> [!WARNING]
> This is a soft preference, not a hard boundary. The agent can still read files via `Bash(cat ...)`, `Bash(head ...)`, `Grep`, and `Glob`. In practice, denying `Read` is usually sufficient.