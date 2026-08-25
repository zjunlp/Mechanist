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
  - [2. Install the Mechanist Plugin](#2-install-the-mechanist-plugin)
  - [3. Configure the External Review Model](#3-configure-the-external-review-model)
  - [4. Prepare the Python Environment](#4-prepare-the-python-environment-optional)
- [🚀 Quick Start](#-quick-start)
  - [1. Create a Working Directory](#1-create-a-working-directory)
  - [2. Start Claude Code](#2-start-claude-code)
  - [3. Tell `/mguide` What You Want](#3-tell-mguide-what-you-want)
  - [4. Read the Results](#4-read-the-results)
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
/help             # /mechanist:mguide should be listed
/mcp              # llm-chat and mechanic-db should both be "connected"
```

> Commands still missing after that? Restart Claude Code and try again.

### 3. Configure the External Review Model

Mechanist cross-validates its own ideas, experiment designs, and conclusions with an external reviewer at every stage — a second model, independent of Claude, so the same model never grades itself. **Do not use a Claude-series model for this role.** [GPT-5.4](https://platform.openai.com) (`gpt-5.4`) is recommended — with a standard OpenAI key the defaults below are already correct. For Azure, DeepSeek, Qwen, or a third-party proxy, set all three variables to an OpenAI-compatible endpoint.

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

Create an empty folder, start Claude Code inside it, and tell **`/mguide`** what you want in plain language. It works out your research requirements through conversation and writes `task.md` for you — the document describing the experimental task, and the starting point for everything the pipeline does downstream — then runs it once you confirm.

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

### 1. Create a Working Directory

```bash
mkdir my-experiment && cd my-experiment   # one research question per directory
```

Mechanist works inside this folder and writes all outputs here.

### 2. Start Claude Code

> [!NOTE]
> We recommend `claude-opus-4-8` for good performance. Weaker models degrade the whole pipeline.

```bash
claude --model claude-opus-4-8
```

### 3. Tell `/mguide` What You Want

`/mguide` is the single entry point — no parameters to learn, no file format to memorize. Describe your goal in your own words:

**Run a study** — explore a mechanism, reproduce a paper, validate a suspected phenomenon, or hand it a bare direction and let it find the phenomenon itself:

```text
/mguide Reproduce this paper: LLMs encode harmfulness and refusal separately
```

**Find literature** — search the 14k-paper interpretability corpus, the 157M-node citation graph, and the web:

```text
/mguide find me papers on sparse autoencoder feature absorption in large language models
```

**See how a field developed** — a timeline of key papers, turning points, debates, and open problems:

```text
/mguide I'd like to know how circuit-level interpretability got to where it is today
```

For a research run, `/mguide` asks only what it cannot infer — which model and dataset to use, where the weights live, how much GPU time it may spend — then writes `task.md` into the current directory, shows it to you, and starts the run once you confirm.

### 4. Read the Results

The run executes four stages in order — **claim → experiment → verify → iteration** — writing each stage's documents to disk before the next begins (`idea-stage/`, `refine-logs/`, `verify/`, `review-stage/`, `runs/`). When it finishes, read these two files at the project root:

| File | What's inside |
|:---|:---|
| `CLAIMS_LEDGER.md` | Per-claim scoreboard: final verdicts, robustness, and caveats. |
| `AUTO_PIPELINE_REPORT.md` | The run's journey, an index of every artifact, and any Open Items still needing your action. |

> Want to drive the pipeline yourself — pipeline modes, writing `task.md` by hand, GPU budgets, hard constraints, multi-round research? See the [User Guide](docs/user_guide.md).

---

## 📖 Further Reading

- **[User Guide](docs/user_guide.md)** — the commands behind `/mguide`, pipeline modes and the full parameter reference, writing `task.md` by hand, GPU budgets and hard constraints, multi-round research, literature management, hypothesis batch generation, and experiment isolation.
- **[Developer Guide](docs/developer_guide.md)** — for contributors who want to modify skill prompts, agent definitions, or MCP server code locally.

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
