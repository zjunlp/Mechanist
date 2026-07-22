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
  - [1. Install Claude Code](#1-install-claude-code)
  - [2. Install uv](#2-install-uv)
  - [3. Create a Conda Environment](#3-create-a-conda-environment)
  - [4. Configure Environment Variables](#4-configure-environment-variables)
  - [5. Install the Mechanist Plugin](#5-install-the-mechanist-plugin)
- [🚀 Quick Start](#-quick-start)
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

Mechanist is distributed as a **Claude Code plugin**. You do not need to clone this repository to use it (see [Installation](#-installation)).

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

### 1. Install Claude Code

Download and install Claude Code, then log in:

```bash
# Download and install Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# Restart your terminal, then verify
claude --version
```

> [!IMPORTANT]
> **Mechanist requires the Opus 4.7 model.** Launch each session with `--model claude-opus-4-7`, or select Opus 4.7 within a session using `/model`.
> ```bash
> claude --model claude-opus-4-7
> ```

### 2. Install uv

The Mechanist MCP servers use `uv` to bootstrap temporary Python environments:

```bash
# Download and install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal, then verify
uv --version
```

### 3. Create a Conda Environment

Create a dedicated conda environment `scientist` for experiment execution and install its dependencies:

```bash
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/zjunlp/Mechanist/main/requirements.txt)
```

### 4. Configure Environment Variables

Mechanist's two MCP servers read configuration from **environment variables**. Set the following values in `~/.bashrc` (or `~/.zshrc`):

| Variable | Required | Default / Example | Purpose |
|:---|:---|:---|:---|
| `LLM_API_KEY` | **Yes** | `sk-…` | API key for the external review model (cross-validation). |
| `LLM_MODEL` | No | `gpt-5.4` | External review model name. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Base URL for the LLM provider. If using a proxy, set this to the proxy URL. |
| `MECHANIC_DB_API_KEY` | No | `sk_…` | API key for the Mechanic-DB paper retrieval service. If unset, Mechanist falls back to local PDFs, Web Search, arXiv, and Semantic Scholar. |

#### External Review Model

The external review model independently cross-validates Claude's ideas, experiment designs, and conclusions at every pipeline stage, preventing correlated failure from same-model self-review. **Do not use a Claude-series model** for this role.

- **Recommended**: Use GPT-5.4 via `https://platform.openai.com`. With a standard OpenAI key in `LLM_API_KEY`, the `LLM_MODEL` and `LLM_BASE_URL` defaults suffice.
- **Alternative providers** (Azure / DeepSeek / Qwen / third-party proxies): configure all three — `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` — for an OpenAI-compatible endpoint.

#### Mechanic-DB API Key

Mechanic-DB is a self-hosted paper retrieval service backed by a 14k-paper interpretability corpus and a 157M-node cross-disciplinary citation network. It provides precise, domain-focused recall compared to general-purpose web search. Without a key, Mechanist skips Mechanic-DB and falls back to local PDFs, Web Search, arXiv, and Semantic Scholar.

**Step 1:** Register with your email address:

```bash
curl -X POST http://mechanist.openkg.cn/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com"}'
```

**Step 2:** Open the verification link in the email you receive. The page displays an API key starting with `sk_`.

> [!WARNING]
> **The key is shown only once.** Copy it immediately and set it as `MECHANIC_DB_API_KEY`.

#### Set the Variables

Add the following to `~/.bashrc` (or `~/.zshrc`):

```bash
# --- Mechanist ---
export LLM_API_KEY="sk-..."                       # Required: external review model key
export LLM_MODEL="gpt-5.4"                        # Optional, default: gpt-5.4
export LLM_BASE_URL="https://api.openai.com/v1"   # Optional, default: official endpoint
export MECHANIC_DB_API_KEY="sk_..."               # Optional: leave unset to skip Mechanic-DB
```

Then run `source ~/.bashrc` (or open a new terminal) and confirm with `echo "$LLM_API_KEY"`.

---

### 5. Install the Mechanist Plugin

Install directly from the Claude Code plugin marketplace:

```text
/plugin marketplace add zjunlp/Mechanist
/plugin install mechanist@mechanist
```

Once installed and the [environment variables](#4-configure-environment-variables) are set, **restart Claude Code**, then verify:

- Run `/help` and confirm that Mechanist skills appear — e.g. `/mechanist:auto`, `/mechanist:msearch`, `/mechanist:mhistory`.
- Run `/mcp` and confirm that both `llm-chat` and `mechanic-db` show as **connected**.

Once both checks pass, proceed to [Quick Start](#-quick-start).

---

## 🚀 Quick Start

Here is the big picture — every Mechanist run follows this loop:

```
 task.md  ──▶  /auto  ──▶  CLAIMS_LEDGER.md
 (your input)   (the engine)   (the findings)
```

- **`task.md`** is where you describe your research question. `/auto` reads it and uses it to drive every stage of the pipeline.
- **`/auto`** runs the full workflow and writes everything to disk as it goes.
- **`CLAIMS_LEDGER.md`** is the final report — open it to see what was discovered.

### Step 1: Create a Project and Write `task.md`

Each research question gets its own directory with a `task.md`:

```bash
mkdir my-experiment && cd my-experiment
```

Now create `task.md` inside it. Here is a minimal example:

```markdown
# Does GPT-2 use a dedicated "negation" direction in its residual stream?

We hypothesize that the model represents negation through a consistent,
localized direction in the residual stream of middle layers. Use probing
and activation patching to test this.

Model: GPT-2-small (HuggingFace)
```

> See [Writing `task.md`](#writing-taskmd) for the full reference — you can specify model paths, GPU budgets, hard constraints, and more.

### Step 2: Launch the Pipeline

Start Claude Code in your project directory and run `/auto`:

```bash
claude --model claude-opus-4-7
```

```text
/auto
```

`/auto` reads your `task.md` and runs the full four-stage workflow — formulating a testable claim, designing and executing experiments, validating robustness, and iteratively refining conclusions. When it finishes, open `CLAIMS_LEDGER.md` for the complete findings.

See [Pipeline Modes](#pipeline-modes) to control how behavior and mechanism discovery are handled.

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
> **Reviewing results:** After each `/auto` run, the scientific conclusions and final pipeline state are aggregated in `CLAIMS_LEDGER.md` at the root of your working directory. This claim-centric report records each claim's statement, data/model/method, main experiment results, verify verdict, and iteration outcome — a single file to review all outputs.

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

---

## 📄 Citation

If you use Mechanist in your research, please cite:

```bibtex
TODO
```

---

## 🙏 Acknowledgements

TODO