# Mechanist — User Guide

**This document covers advanced usage — the commands behind `/mguide`, the full parameter reference, and day-to-day tips.**

---

## The Commands Behind `/mguide`

`/mguide` is the front door — it works out what you want, prepares the inputs, and dispatches to one of three commands. You can also call them directly:

| Command | What it does |
|:---|:---|
| `/auto` | The autonomous research pipeline: claim → experiment → verify → iteration. |
| `/msearch` | Literature search across the 14k-paper interpretability corpus, the 157M-node citation graph, and web sources. |
| `/mhistory` | Developmental history of a research field — key papers, turning points, and how ideas evolved. |

```text
/msearch "sparse autoencoder feature absorption in large language models"
/mhistory "the evolution of circuit-level interpretability"
```

---

## `/auto` — The Autonomous Pipeline

`/auto` is driven by **two orthogonal parameter axes**, each controlling one stage:

| Axis | Values | Purpose |
|:---|:---|:---|
| **`behavior-source`** | `given` / `given-validation` / `discovery` | Controls where the behavior comes from and whether M0 (phenomenon validation) runs. |
| **`mechanism`** | `given` / `discovery` | Controls who selects the mechanistic method — you or the system. |

> Running `/auto` without arguments defaults to `behavior-source: given, mechanism: discovery`, and reads the task from `task.md` in the project root.

### Pipeline Modes

The two axes are orthogonal — all 3 × 2 = 6 combinations are valid. The four most common patterns are listed below.

| Mode | Command | When to Use |
|:---|:---|:---|
| **Reproduction** | `/auto — behavior-source: given, mechanism: given` | Reproduce a paper: you specify the behavior, mechanism method, model, and data. Strict resource fidelity enforced. |
| **Given Behavior + Discover Mechanism** | `/auto — behavior-source: given, mechanism: discovery` | The behavior is already verified; the system explores which mechanism explains it. |
| **Validate Behavior + Discover Mechanism** | `/auto — behavior-source: given-validation, mechanism: discovery` | You propose a behavior but want it validated first (M0 gate) before mechanism exploration. |
| **Full Discovery** | `/auto — behavior-source: discovery, mechanism: discovery` | Fully autonomous: the pipeline discovers the phenomenon and routes to the appropriate mechanism. |

### Stage Artifacts

Each stage writes its documents to disk before the next stage begins:

| Stage | Key artifacts |
|:---|:---|
| **claim** | `idea-stage/IDEA_REPORT.md` — ranked candidate ideas, or the behavior and claims from `task.md`<br>`refine-logs/FINAL_PROPOSAL.md` — refined method proposal<br>`refine-logs/EXPERIMENT_PLAN.md` — per-claim milestones, models, data, success criteria |
| **experiment** | `refine-logs/MECHANISM_ROUTING.md` — chosen interpretability method and why<br>`refine-logs/EXPERIMENT_RESULTS.md` — per-claim results and baseline verdicts<br>`runs/` — per-run code, logs, and GPU cost records |
| **verify** | `verify/VERIFY_REPORT.md` — robustness verdicts and cross-claim summary<br>`verify/INTEGRITY_AUDIT.md` — honesty audits on original and swap runs |
| **iteration** | `review-stage/AUTO_REVIEW.md` — round-by-round review log<br>`review-stage/AUTO_ITERATION_FINAL_REPORT.md` — what changed across fix loops |

> [!NOTE]
> **Reviewing results:** After each `/auto` run, start with `CLAIMS_LEDGER.md` (per-claim scoreboard) and `AUTO_PIPELINE_REPORT.md` (run journey, artifact index, and Open Items) at the project root.

---

## Writing `task.md`

`task.md` is the **task specification** placed in each project directory. It is free-form natural language — there is no fixed schema. `/mguide` writes it for you; write it by hand when you want full control or plan to call `/auto` directly.

**What you can ask for:**

| What you can ask | Idea |
|:---|:---|
| **Explore a mechanism** | A known model behavior — find which internal component causes it. |
| **Reproduce a paper** | Both the finding and the method are already known — re-run them faithfully. |
| **Validate a suspected phenomenon** | You have a concrete hypothesis, but no paper (or prior run) has confirmed it yet. |
| **Open-ended discovery** | Only a research direction — let Mechanist mine a new phenomenon, then investigate it. |

**What `task.md` should contain:**

| Content | When Required | Notes |
|:---|:---|:---|
| **behavior** | `behavior-source: given` / `given-validation` | A specific, falsifiable phenomenon to investigate. |
| **topic** | `behavior-source: discovery` | A broad research direction; Mechanist will discover specific phenomena within it. |
| **family** | `mechanism: given` | A specific mechanistic method to use (e.g., Fisher information, steering vectors). |
| **model / data** | Recommended | The model and dataset for experiments (specify full paths). Required in reproduction mode. |
| **claim list / goal** | Optional | Assertions you want verified and the objective for this round. |

### Declaring Compute Resources

Specify GPU budget and card limits in natural language within `task.md`:

```text
You have 8 hours of GPU budget. Do not pause or simplify experiments
due to GPU budget before reaching it. You may use at most 4 of the
8 available GPUs simultaneously.
```

- **A generous budget increases the agent's experimental ambition** — it tells the agent "don't cut corners," not just "don't exceed this."
- You can also allocate resources to specific stages (e.g., "main experiments up to 4 GPUs, verify variants up to 2").
- GPU budgets are **hard constraints**: the agent scales each experiment within budget before launching, and halts with a report if truly insufficient.

### Declaring Hard Constraints

Use natural language in `task.md` to declare inviolable requirements. The orchestrator automatically classifies and dispatches each constraint to the relevant stage.

```text
Must strictly use Llama-3-8B for all experiments. Do not use Pythia 2.8B.
When verifying claim 3, only use Pythia 1B and 410M; do not run 2.8B yet.
```

The agent treats hard constraints as red lines. If genuinely impossible under the constraints, it halts and reports rather than silently breaking them.

### Progress Notifications

Express notification intent in `task.md`:

```text
Send progress updates to example@gmail.com, syncing once per hour.
```

When enabled, the pipeline pushes briefings at key touchpoints (experiment completed / verify completed / pipeline finished / halted / needs human input) and syncs progress hourly. Without a notification statement, the feature is fully silent with zero pipeline impact.

> [!NOTE]
> You must configure your own notification channel. Mechanist only scans locally configured channels and sends through them; it does not install or recommend any specific notification tool.

---

## Multi-Round Research

After a `/auto` run completes, use `/next-round` to archive the round's artifacts into `rounds/round_<N>/` and draft the next round's `task.md`. It reads `research_memory.json` to avoid re-exploring settled phenomena or mechanism directions.

```bash
# Explore a brand-new phenomenon
/next-round new-behavior
#   Recommended next: /auto — behavior-source: discovery, mechanism: discovery

# Keep the same behavior, explore a new mechanism
/next-round new-mechanism B1
#   Recommended next: /auto — behavior-source: given, mechanism: discovery

# Let it recommend based on the previous round's conclusions
/next-round
```

Before archiving, `/next-round` prints what will be moved and what will stay. Artifacts go into `rounds/round_<N>/`, while `task.md`, `research_memory.*`, `.claude/`, `.mcp.json`, and `.git` remain in the root. The `new-mechanism` variant additionally preserves `data/` and `cache/` to reuse activations from the same behavior.

**Multi-round guard:** Each `/auto` start checks for unarchived artifacts from the previous round in the root directory. If found, it halts and prompts you to either run `/next-round` (archive and proceed — recommended), `resume: true` (continue the unfinished round), or manually delete the listed artifacts. This guard fires even in fully automatic mode — it will never silently overwrite a previous round's work.

**Revisiting settled directions:** By default, `/auto` avoids re-exploring behaviors or mechanisms already marked as settled in `research_memory.json`. If you pin a settled direction in `task.md` without authorization, the pipeline treats it as a probable oversight and silently picks a fresh alternative (in auto mode) or asks you to confirm (in interactive mode). To force a re-run, add to `task.md`:

```markdown
retry-settled: true
```

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

# Control how much of each round is generated unprimed
/hypothesis-batch "LLM beliefs" — cold-n: 4               # How many of the round's behaviors are generated BEFORE the
                                                          # discovery-strategy taxonomy is shown (default: n-behaviors / 5).
                                                          # Raise it when the pool keeps collapsing onto one framing;
                                                          # 0 disables the cold pass (not recommended).

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
