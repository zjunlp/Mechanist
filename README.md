<p align="center">
  <img src="docs/mechanist-logo.png" alt="Mechanist Logo" width="413" height="100">
</p>

<p align="center">
  <strong>Autonomous Research Agent for LLM Mechanistic Interpretability</strong>
</p>

<p align="center">
  <a href="#-overview">Overview</a> ·
  <a href="#-installation">Installation</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-usage-guide">Usage Guide</a> ·
  <a href="#-acknowledgements">Acknowledgements</a> ·
  <a href="http://mechanist.openkg.cn">Website</a> ·
  <a href="docs/README_zh.md">中文</a>
</p>

<p align="center">
  <a href="https://github.com/zjunlp/Mechanist/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
  </a>
  <a href="https://claude.ai/code">
    <img src="https://img.shields.io/badge/Claude%20Code-Plugin-orange?logo=anthropic" alt="Claude Code Plugin">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python" alt="Python 3.11+">
  </a>
  <a href="https://github.com/zjunlp/Mechanist">
    <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status: Active">
  </a>
</p>

---

## 📖 Table of Contents

- [📖 Overview](#-overview)
- [🔄 How It Works](#-how-it-works)
- [🔧 Installation](#-installation)
  - [1. Install Claude Code and uv](#1-install-claude-code-and-uv)
  - [2. Install the Mechanist Plugin](#2-install-the-mechanist-plugin)
  - [3. Configure the External Review Model](#3-configure-the-external-review-model)
  - [4. Prepare the Python Environment](#4-prepare-the-python-environment-optional)
- [🚀 Quick Start](#-quick-start)
  - [1. Create a Working Directory](#1-create-a-working-directory)
  - [2. Write `task.md`](#2-write-the-research-task-as-taskmd)
  - [3. Run `/auto`](#3-start-claude-code-and-run-auto)
  - [4. Follow the Run and Read Results](#4-follow-the-run-then-read-the-results)
- [📚 Usage Guide](#-usage-guide)
  - [`/auto` — The Autonomous Pipeline](#auto--the-autonomous-pipeline)
  - [`/msearch` — Literature Search](#msearch--literature-search)
  - [`/mhistory` — Topic History](#mhistory--topic-history)
- [📖 Further Reading](#-further-reading)
- [📄 Citation](#-citation)
- [🙏 Acknowledgements](#-acknowledgements)

---

## 📖 Overview

**Mechanist** converts a research question about the internal mechanisms of large language models into **evidence-backed findings**. It coordinates a complete research workflow: literature retrieval, hypothesis formulation, experiment implementation and execution, robustness validation, and iterative refinement — all within a single autonomous pipeline.

**Mechanist ships as a Claude Code plugin** — no repository clone required. Install it in minutes, hand it a research question, and it runs the experiments on your own machine and GPUs, then hands back a verifiable research report. (Codex support is coming soon.)

For the latest install and walkthrough, see the [Quick Start](http://mechanist.openkg.cn/#/quick-start) page on the website.

### Key Capabilities

| Stage | Description |
|:---|:---|
| **Literature Review** | Queries a 14k-paper interpretability corpus, a 157M-node cross-disciplinary citation graph, and web sources. |
| **Hypothesis Formulation** | Proposes novelty-checked claims, or extracts claims from user-provided material. |
| **Experiment Execution** | Generates experiment code, runs evaluations, and records results against a mechanism-aware plan. |
| **Verification** | Evaluates claims under alternate models, datasets, and methods for robustness. |
| **Iteration** | Reviews failed or weak results, updates the plan, and reruns the relevant stages. |

---

## 🔄 How It Works

```
 research question ──▶ claim ──▶ experiment ──▶ verify ──▶ iterate ──▶ findings
                    (hypothesis)  (execution) (validation) (refinement)
```

The `/auto` pipeline consists of an **orchestrator** that dispatches four sequential stages, each running in an independent sub-agent:

1. **Claim** — Searches literature, generates or captures hypotheses, assesses novelty and impact, and produces a detailed experiment plan.
2. **Experiment** — Routes to the appropriate mechanistic method, generates experiment code, runs sanity checks, deploys experiments, and collects results.
3. **Verify** — Tests robustness by swapping along method, dataset, and model axes; runs integrity audits on both main experiments and variants.
4. **Iteration** — External LLM review with structured repair routing (up to 6 rounds), converging claims toward publication-ready conclusions.

All results are tracked in a **Claim Ledger** (`CLAIMS_LEDGER.md`) that records every claim's journey from hypothesis to final verdict.

---

## 🔧 Installation

### 1. Install Claude Code and uv

Mechanist runs inside Claude Code — install the Claude Code CLI first:

```bash
# Install Claude Code, restart your terminal, then verify
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Mechanist's MCP servers use `uv` to manage Python environments — install uv next:

```bash
# Mechanist's MCP servers use uv to bootstrap temporary Python environments
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

### 2. Install the Mechanist Plugin

Inside a Claude Code session:

```text
/plugin marketplace add zjunlp/Mechanist
/plugin install mechanist@mechanist
```

Then activate and verify:

```text
/reload-plugins   # only if the install summary asked for it
/help             # listed as /mechanist:auto, /mechanist:msearch, /mechanist:mhistory
/mcp              # llm-chat and mechanic-db should both be "connected"
```

> Commands still missing after that? Restart Claude Code and try again.

### 3. Configure the External Review Model

Mechanist cross-validates its own ideas, experiment designs, and conclusions with an external reviewer at every stage — a second model, independent of Claude, so the same model never grades itself. **Do not use a Claude-series model for this role.** [GPT-5.4](https://platform.openai.com) is recommended — with a standard OpenAI key the defaults below are already correct. For Azure, DeepSeek, Qwen, or a third-party proxy, set all three variables to an OpenAI-compatible endpoint.

| Variable | Required | Default / Example | Purpose |
|:---|:---|:---|:---|
| `LLM_API_KEY` | **Yes** | `sk-…` | API key for the external review model (cross-validation). |
| `LLM_MODEL` | No | `gpt-5.4` | External review model name. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Base URL for the LLM provider. Set this to your proxy URL if you use one. |

Add the following to `~/.bashrc` (or `~/.zshrc`):

```bash
# --- Mechanist (add to ~/.bashrc or ~/.zshrc) ---
export LLM_API_KEY="sk-..."                       # required: external review model key
export LLM_MODEL="<your_model_name>"              # optional, default: gpt-5.4
export LLM_BASE_URL="<your_base_url>"             # optional, default: official endpoint
```

Load the new variables, then confirm the key is set:

```bash
source ~/.bashrc            # or open a brand-new terminal
echo "$LLM_API_KEY"         # should print your key, not an empty line
```

> [!NOTE]
> **Variables are read only when Claude Code starts.** Exporting them inside an already-running session changes nothing. Edit `~/.bashrc` → `source` it (or open a new terminal) → restart Claude Code.

### 4. Prepare the Python Environment (Optional)

Mechanist runs experiments in the Python environment the Claude session was started in. If you do not yet have the basic packages for running experiments (PyTorch, NumPy, scikit-learn, etc.), create a conda environment. The `scientist` environment covers the common tools Mechanist may need:

```bash
# Example: a dedicated conda env named scientist
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/zjunlp/Mechanist/main/requirements.txt)
```

Once the steps above are done, proceed to [Quick Start](#-quick-start).

---

## 🚀 Quick Start

Create a folder as the working directory, write a free-form Markdown file `task.md` to describe your research question, then open Claude Code and run `/auto` to start the autonomous research pipeline.

```
 task.md  ──▶  /auto  ──▶  CLAIMS_LEDGER.md + AUTO_PIPELINE_REPORT.md
 (your input)   (the engine)   (the findings)
```

### 1. Create a Working Directory

Create a new empty folder for your research task. Mechanist will work inside this folder and write all outputs here.

```bash
mkdir my-experiment && cd my-experiment   # one research question per directory
```

### 2. Write the Research Task as `task.md`

Place a free-form Markdown file named `task.md` in the project root. The file should contain your research question in natural language. Typical asks include:

| What you can ask | Idea |
|:---|:---|
| **Explore a mechanism** | A known model behavior — find which internal component causes it. |
| **Reproduce a paper** | Both the finding and the method are already known — re-run them faithfully. |
| **Validate a suspected phenomenon** | You have a concrete hypothesis, but no paper (or prior run) has confirmed it yet. |
| **Open-ended discovery** | Only a research direction — let Mechanist mine a new phenomenon, then investigate it. |

Minimal example:

```markdown
# Does GPT-2 use a dedicated "negation" direction in its residual stream?

We hypothesize that the model represents negation through a consistent,
localized direction in the residual stream of middle layers. Use probing
and activation patching to test this.

Model: GPT-2-small (HuggingFace)
```

> See [Writing `task.md`](#writing-taskmd) for the full reference — you can specify model paths, GPU budgets, hard constraints, and more.

### 3. Start Claude Code and Run `/auto`

> [!NOTE]
> **Use an Opus-series model.** We recommend Opus for best performance — switch inside a session with `/model opus`. Weaker models degrade the whole pipeline.

Start Claude Code in the project root:

```bash
claude --model opus
```

Inside the session, run bare `/auto`. It will read `task.md` and run the whole research pipeline automatically:

```text
/auto
```

### 4. Follow the Run, Then Read the Results

Mechanist executes four stages in order — **claim → experiment → verify → iteration** — and writes each stage's documents to disk before the next stage begins:

| Stage | Key artifacts |
|:---|:---|
| **claim** | `idea-stage/IDEA_REPORT.md` — ranked candidate ideas, or the behavior and claims from `task.md`<br>`refine-logs/FINAL_PROPOSAL.md` — refined method proposal<br>`refine-logs/EXPERIMENT_PLAN.md` — per-claim milestones, models, data, success criteria |
| **experiment** | `refine-logs/MECHANISM_ROUTING.md` — chosen interpretability method and why<br>`refine-logs/EXPERIMENT_RESULTS.md` — per-claim results and baseline verdicts<br>`runs/` — per-run code, logs, and GPU cost records |
| **verify** | `verify/VERIFY_REPORT.md` — robustness verdicts and cross-claim summary<br>`verify/INTEGRITY_AUDIT.md` — honesty audits on original and swap runs |
| **iteration** | `review-stage/AUTO_REVIEW.md` — round-by-round review log<br>`review-stage/AUTO_ITERATION_FINAL_REPORT.md` — what changed across fix loops |

When it finishes, read these two files at the project root:

| File | What's inside |
|:---|:---|
| `CLAIMS_LEDGER.md` | Per-claim scoreboard: final verdicts, robustness, and caveats. |
| `AUTO_PIPELINE_REPORT.md` | The run's journey, an index of every artifact, and any Open Items still needing your action. |

See [Pipeline Modes](#pipeline-modes) to control how behavior and mechanism discovery are handled. For archive / next-round workflows and advanced usage, see the [User Guide](docs/user_guide.md).

---

## 📚 Usage Guide

### `/auto` — The Autonomous Pipeline

`/auto` is driven by **two orthogonal parameter axes**, each controlling one stage:

| Axis | Values | Purpose |
|:---|:---|:---|
| **`behavior-source`** | `given` / `given-validation` / `discovery` | Controls where the behavior comes from and whether M0 (phenomenon validation) runs. |
| **`mechanism`** | `given` / `discovery` | Controls who selects the mechanistic method — you or the system. |

> Running `/auto` without arguments defaults to `behavior-source: given, mechanism: discovery`.

#### Pipeline Modes

The two axes are orthogonal — all 3 × 2 = 6 combinations are valid. The four most common patterns are listed below.

| Mode | Command | When to Use |
|:---|:---|:---|
| **Reproduction** | `/auto — behavior-source: given, mechanism: given` | Reproduce a paper: you specify the behavior, mechanism method, model, and data. Strict resource fidelity enforced. |
| **Given Behavior + Discover Mechanism** | `/auto — behavior-source: given, mechanism: discovery` | The behavior is already verified; the system explores which mechanism explains it. |
| **Validate Behavior + Discover Mechanism** | `/auto — behavior-source: given-validation, mechanism: discovery` | You propose a behavior but want it validated first (M0 gate) before mechanism exploration. |
| **Full Discovery** | `/auto — behavior-source: discovery, mechanism: discovery` | Fully autonomous: the pipeline discovers the phenomenon and routes to the appropriate mechanism. |

> [!NOTE]
> **Reviewing results:** After each `/auto` run, start with `CLAIMS_LEDGER.md` (per-claim scoreboard) and `AUTO_PIPELINE_REPORT.md` (run journey, artifact index, and Open Items) at the project root. Stage-level artifacts under `idea-stage/`, `refine-logs/`, `verify/`, `review-stage/`, and `runs/` are written as the pipeline progresses — see [Follow the Run](#4-follow-the-run-then-read-the-results).

#### Writing `task.md`

`task.md` is the **task specification** placed in each project directory. It is free-form natural language — there is no fixed schema.

**What `task.md` should contain:**

| Content | When Required | Notes |
|:---|:---|:---|
| **behavior** | `behavior-source: given` / `given-validation` | A specific, falsifiable phenomenon to investigate. |
| **topic** | `behavior-source: discovery` | A broad research direction; Mechanist will discover specific phenomena within it. |
| **family** | `mechanism: given` | A specific mechanistic method to use (e.g., Fisher information, steering vectors). |
| **model / data** | Recommended | The model and dataset for experiments (specify full paths). Required in reproduction mode. |
| **claim list / goal** | Optional | Assertions you want verified and the objective for this round. |

#### Declaring Compute Resources

Specify GPU budget and card limits in natural language within `task.md`:

```text
You have 8 hours of GPU budget. Do not pause or simplify experiments
due to GPU budget before reaching it. You may use at most 4 of the
8 available GPUs simultaneously.
```

- **A generous budget increases the agent's experimental ambition** — it tells the agent "don't cut corners," not just "don't exceed this."
- You can also allocate resources to specific stages (e.g., "main experiments up to 4 GPUs, verify variants up to 2").
- GPU budgets are **hard constraints**: the agent scales each experiment within budget before launching, and halts with a report if truly insufficient.

#### Declaring Hard Constraints

Use natural language in `task.md` to declare inviolable requirements. The orchestrator automatically classifies and dispatches each constraint to the relevant stage.

```text
Must strictly use Llama-3-8B for all experiments. Do not use Pythia 2.8B.
When verifying claim 3, only use Pythia 1B and 410M; do not run 2.8B yet.
```

The agent treats hard constraints as red lines. If genuinely impossible under the constraints, it halts and reports rather than silently breaking them. For details on classification, scoping, and the distinction between hard constraints and informational notices, see the [User Guide](docs/user_guide.md#reliability--best-practices).

#### Progress Notifications

Express notification intent in `task.md`:

```text
Send progress updates to example@gmail.com, syncing once per hour.
```

When enabled, the pipeline pushes briefings at key touchpoints (experiment completed / verify completed / pipeline finished / halted / needs human input) and syncs progress hourly. Without a notification statement, the feature is fully silent with zero pipeline impact.

> [!NOTE]
> You must configure your own notification channel. Mechanist only scans locally configured channels and sends through them; it does not install or recommend any specific notification tool.

#### Multi-Round Research

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

### `/msearch` — Literature Search

`/msearch` searches for relevant literature in the 14k-paper interpretability corpus, the 157M-node citation graph, and web sources, returning a curated, ranked list of papers for a given query. Use it to survey the state of the art on a topic or to check whether a hypothesis has already been explored.

```text
/msearch "sparse autoencoder feature absorption in large language models"
```

---

### `/mhistory` — Topic History

`/mhistory` generates a developmental history of a research field — tracing key papers, turning points, and how ideas evolved over time. The output is a structured narrative that helps you position your own work in the literature or identify underexplored directions.

```text
/mhistory "the evolution of circuit-level interpretability"
```

The resulting timeline covers foundational papers, methodological breakthroughs, major debates, and open problems — a compact map of the field's trajectory for a given topic.

---

## 📖 Further Reading

- **[User Guide](docs/user_guide.md)** — pipeline architecture deep-dive, full parameter reference, working with reference papers, literature management, hypothesis batch generation, experiment isolation, and reliability best practices.
- **[Developer Guide](docs/developer_guide.md)** — for contributors who want to modify skill prompts, agent definitions, or MCP server code locally.

<!-- ---

## 📄 Citation

If you use Mechanist in your research, please cite:

```bibtex
TODO
``` -->

---

## 🙏 Acknowledgements

We would like to express our heartfelt gratitude for the contribution of ARIS to our project, as we have utilized portions of their source code in our project. 
Many thanks to all the colleagues in the community for submitting issues and providing technical support. 
