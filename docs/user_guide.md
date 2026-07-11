# Mechanist — User Guide

**This document covers advanced usage tips for user's work.**

---

## `/auto` Parameters

All `/auto` parameters are appended to the command: start with ` — ` (em dash; `--` also accepted), then `key: value` pairs separated by commas.

```bash
/auto "direction" — auto-proceed: false                    # Stop at each gate for user approval
/auto "direction" — GPU_ID=4                               # Pin to a specific GPU
/auto "direction" — claim-model: opus, verify-model: sonnet # Per-stage model selection
/auto "direction" — dimensions: method,dataset             # Verify robustness axes (one variant per axis)
/auto "direction" — review-loop: false                     # Stop after verify; skip iteration
```

---

## Literature Directory

Drop must-read PDFs into a `literature/` folder inside your project directory. The literature review stage scans it every round as a **read-only curated channel** — the pipeline never modifies or deletes these files. PDFs with the same name as auto-downloaded papers take precedence over the pipeline's copies.

```bash
mkdir -p literature
cp ~/Downloads/*.pdf literature/    # All subsequent /auto runs will include these
```

---

## Hypothesis Batch Generation

Build a library of behavior + mechanism hypotheses for a topic without running a full pipeline. Results accumulate in `hypothesis_library.json` with novelty scores and LLM-based semantic deduplication.

```bash
# Discover both behaviors and mechanisms (default)
/hypothesis-batch "LLM beliefs"

# Fix behavior, only search for mechanisms — behavior can be free text or a node ID
/hypothesis-batch "LLM beliefs" — behavior: "the model maintains its initial stance across multi-turn dialogue"
/hypothesis-batch "LLM beliefs" — behavior: B3

# Control scale
/hypothesis-batch "LLM beliefs" — n-behaviors: 12         # New behaviors per round (discover mode only)
/hypothesis-batch "LLM beliefs" — rounds: 5               # Consecutive rounds; stops early if the topic is mined out

# Speed/accuracy trade-off for novelty scoring
/hypothesis-batch "LLM beliefs" — novelty-web: false      # Skip web retrieval; use model knowledge only (faster, may miss recent papers)
```

Each hypothesis gets a novelty score as a coarse filter. For rigorous verification, run `/novelty-check` on selected candidates.

---

## Experiment Isolation

When running the same experiment multiple times (e.g., `exp1`, `exp2`, `exp3`), the agent may inadvertently read artifacts from previous runs and contaminate the current run.

Two mechanisms are available to control the agent's file access scope. Use either or both.

### Tier 1: Prompt-level soft constraint

Add a prohibition to `task.md`:

```text
Do not read other experiment directories. Do not borrow data, experiment
designs, group assignments, or other information from previous runs.
```

The orchestrator injects this directive into every sub-agent's dispatch prompt. This is a prompt-level constraint — it depends on the model following instructions.

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
