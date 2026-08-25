<p align="center">
  <img src="docs/mechanist-logo.png" alt="Mechanist Logo" width="413" height="100">
</p>

<p align="center">
  <strong>Autonomous Research Agent for LLM Mechanistic Interpretability</strong>
</p>

<p align="center">
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
  - [2. Install Mechanist plugin for Claude Code](#2-install-mechanist-plugin-for-claude-code)
  - [3. Configure the external review model](#3-configure-the-external-review-model)
  - [4. Prepare the Python environment where experiments run](#4-prepare-the-python-environment-where-experiments-run-optional)
- [🚀 Quick Start](#-quick-start)
  - [1. Create a working directory](#1-create-a-working-directory)
  - [2. Start Claude Code](#2-start-claude-code)
  - [3. Tell `/mguide` what you want](#3-tell-mguide-what-you-want)
  - [4. Follow the run, then read the results](#4-follow-the-run-then-read-the-results)
- [📖 Further Reading](#-further-reading)
- [🙏 Acknowledgements](#-acknowledgements)
- [📄 Citation](#-citation)

---

## 📖 Overview

**Mechanist** converts a research question about the internal mechanisms of large language models into **evidence-backed findings**. It coordinates a complete research workflow: literature retrieval, hypothesis formulation, experiment implementation and execution, robustness validation, and iterative refinement — all within a single autonomous pipeline.

**Mechanist ships as a Claude Code plugin** — no repository clone required. Install it in minutes, hand it a research question, and it runs the experiments on your own machine and GPUs, then hands back a verifiable research report. (Codex support is coming soon.)

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

The research pipeline consists of an **orchestrator** that dispatches four sequential stages, each running in an independent sub-agent:

1. **Claim** — Searches literature, generates or captures hypotheses, assesses novelty and impact, and produces a detailed experiment plan.
2. **Experiment** — Routes to the appropriate mechanistic method, generates experiment code, runs sanity checks, deploys experiments, and collects results.
3. **Verify** — Tests robustness by swapping along method, dataset, and model axes; runs integrity audits on both main experiments and variants.
4. **Iteration** — External LLM review with structured repair routing (up to 6 rounds), converging claims toward publication-ready conclusions.

All results are tracked in a **Claim Ledger** (`CLAIMS_LEDGER.md`) that records every claim's journey from hypothesis to final verdict.

---

## 🔧 Installation

### 1. Install Claude Code and uv

Mechanist runs inside Claude Code — install Claude Code CLI.

```bash
# Install Claude Code, restart your terminal, then verify
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Mechanist's MCP servers use uv to manage Python environments — install uv next.

```bash
# Mechanist's MCP servers use uv to bootstrap temporary Python environments
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

### 2. Install Mechanist plugin for Claude Code

Inside a Claude Code session:

```text
/plugin marketplace add zjunlp/Mechanist
/plugin install mechanist@mechanist
```

Then activate and verify it:

```text
/reload-plugins   # only if the install summary asked for it
/help             # listed as /mechanist:auto, /mechanist:msearch, /mechanist:mhistory
/mcp              # llm-chat and mechanic-db should both be "connected"
```

> Commands still missing after that? Restart Claude Code and try again.

### 3. Configure the external review model

Mechanist cross-validates its own ideas, experiment designs, and conclusions with an external reviewer at every stage — a second model, independent of Claude, so the same model never grades itself. **Do not use a Claude-series model for this role.** GPT-5.4 via [platform.openai.com](https://platform.openai.com) is recommended — with a standard OpenAI key the defaults below are already correct. For Azure, DeepSeek, Qwen, or a third-party proxy, set all three variables to an OpenAI-compatible endpoint.

| Variable | Required | Default / example | Purpose |
|:---|:---|:---|:---|
| `LLM_API_KEY` | **Yes** | `sk-…` | API key for the external review model (cross-validation). |
| `LLM_MODEL` | No | `gpt-5.4` | External review model name. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Base URL for the LLM provider. Set this to your proxy URL if you use one. |

To set the variables above, add the following lines to `~/.bashrc` (or `~/.zshrc`):

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

### 4. Prepare the Python environment where experiments run (Optional)

Mechanist runs experiments in the Python environment the Claude session was started in. If you do not yet have the basic packages for running experiments (PyTorch, NumPy, scikit-learn, etc.), use the commands below to create a conda environment. The `scientist` environment we provide covers the common tools Mechanist may need while running experiments.

```bash
# Example: a dedicated conda env named scientist
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/zjunlp/Mechanist/main/requirements.txt)
```

Once the steps above are done, proceed to [Quick Start](#-quick-start).

---

## 🚀 Quick Start

Create a folder as working directory, start Claude Code inside it, and tell `/mguide` what you want in plain language. It works out your research requirements with you and writes `task.md` — the task spec everything downstream builds on — then starts the autonomous pipeline once you confirm. Here are the details:

```
 /mguide "what you want"
     │   it works out your research requirements with you
     ▼
 task.md
     │   the task spec it writes for you — the run starts once you confirm
     ▼
 claim ──▶ experiment ──▶ verify ──▶ iteration
     │   the autonomous pipeline: hypothesize → run → validate → refine
     ▼
 CLAIMS_LEDGER.md + AUTO_PIPELINE_REPORT.md
     (the findings)
```

### 1. Create a working directory

Create a new empty folder for your research task. Mechanist will work inside this folder and write all outputs here.

```bash
mkdir my-experiment && cd my-experiment   # one research question per directory
```

### 2. Start Claude Code

> [!NOTE]
> **Use an Opus-series model.** We recommend `claude-opus-4-8` for good performance — inside a running session you can switch with `/model claude-opus-4-8`. Weaker models degrade the whole pipeline.

Start Claude Code in the project root (i.e. the folder you created in step 1):

```bash
claude --model claude-opus-4-8
```

### 3. Tell `/mguide` what you want

`/mguide` is Mechanist's entry point. Type it at the Claude Code prompt and describe your task in plain language — it works out the rest with you from there.

Here is what you can ask it to do:

#### Research runs *(runs the full research pipeline)*

- **Explore a mechanism**  
  A known model behavior — find which internal component causes it.

- **Reproduce a paper**  
  Both the finding and the method are already known — re-run them faithfully at the stated scale.

  ```text
  /mguide Reproduce this paper: LLMs encode harmfulness and refusal separately
  ```

- **Validate a suspected phenomenon**  
  You have a concrete hypothesis, but no paper (or prior run) has confirmed it yet.

- **Open-ended discovery**  
  Only a research direction — let Mechanist mine a new phenomenon, then investigate it.

#### Literature *(answers only — no pipeline run)*

- **Find literature**  
  Search the 14k-paper interpretability corpus, the 157M-node citation graph, and the web.

  ```text
  /mguide find me papers on sparse autoencoder feature absorption in large language models
  ```

- **See how a field developed**  
  A timeline of the key papers, turning points, debates, and open problems.

  ```text
  /mguide I'd like to know how circuit-level interpretability got to where it is today
  ```

### 4. Follow the run, then read the results

If what Mechanist takes on is a **research run**, it enters the full research pipeline below. Literature requests return an answer directly and stop there.

Mechanist executes the four stages in order: **claim → experiment → verify → iteration**, and writes each stage's relevant documents to disk before the next stage begins. Reading these documents lets you track what has been completed, what is planned next, and what has been discovered:

| Stage | Artifact | What's inside |
|:---|:---|:---|
| **claim** | `idea-stage/IDEA_REPORT.md` | Ranked candidate ideas, or the behavior and claims captured from your task.md. |
| | `refine-logs/FINAL_PROPOSAL.md` | The refined method proposal — how the claims will be tested. |
| | `refine-logs/EXPERIMENT_PLAN.md` | Per-claim milestones: models, data, sample sizes, and success criteria. |
| **experiment** | `refine-logs/MECHANISM_ROUTING.md` | Which interpretability method was chosen, the candidates considered, and why. |
| | `refine-logs/EXPERIMENT_RESULTS.md` | Per-claim results, one-line headlines, and baseline verdicts (supported / not-supported). |
| | `runs/` | Per-run code, logs, and GPU cost records for each experiment job. |
| **verify** | `verify/VERIFY_REPORT.md` | Per-claim robustness verdicts and a cross-claim summary. |
| | `verify/INTEGRITY_AUDIT.md` | What the honesty audits found on the original results and each swap run. |
| **iteration** | `review-stage/AUTO_REVIEW.md` | Round-by-round review log: scores, flagged problems, and the fixes taken. |
| | `review-stage/AUTO_ITERATION_FINAL_REPORT.md` | What changed per claim across the fix loops, with unresolved items at the end. |

When it finishes, read these two files at the project root:

| File | What's inside |
|:---|:---|
| `CLAIMS_LEDGER.md` | Per-claim scoreboard: final verdicts, robustness, and caveats. |
| `AUTO_PIPELINE_REPORT.md` | The run's journey, an index of every artifact, and any Open Items still needing your action. |

---

## 📖 Further Reading

**Want to know more about Mechanist?** Read Mechanist documentation to learn: how to archive the current results and start the next round, explore advanced usage of Mechanist, learn how to write a good `task.md`, or see how the pipeline is designed.

**[Read Mechanist documentation →](http://mechanist.openkg.cn/docs/index.html)**

---

## 🙏 Acknowledgements

We would like to express our heartfelt gratitude for the contribution of ARIS to our project, as we have utilized portions of their source code in our project. 
Many thanks to all the colleagues in the community for submitting issues and providing technical support. 

---

## 📄 Citation

If you use Mechanist, please cite:

```bibtex
@article{wang2026mechanist,
  title={Mechanist: AI as a Scientific Instrument for Discovering the Mechanisms of Intelligence},
  author={Wang, Mengru and Fang, Junfeng and Qiao, Shuofei and Xu, Zhenqian and Xu, Haoming and Wang, Haoxiong and Deng, Shumin and Yang, Linyi and Cui, Zhixiang and Xu, Xin and others},
  journal={arXiv preprint arXiv:2608.12036},
  year={2026}
}
```
