<p align="center">
  <img src="mechanist-logo.png" alt="Mechanist Logo" width="413" height="100">
</p>

<p align="center">
  <strong>LLM 机理可解释性自主研究智能体</strong>
</p>

<p align="center">
  <a href="http://mechanist.openkg.cn">项目网站</a> ·
  <a href="../README.md">English</a>
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

## 📖 目录

- [📖 概述](#-概述)
- [🔄 工作流程](#-工作流程)
- [🔧 安装](#-安装)
  - [1. 安装 Claude Code 与 uv](#1-安装-claude-code-与-uv)
  - [2. 安装 Mechanist 插件](#2-安装-mechanist-插件)
  - [3. 配置外部评审模型](#3-配置外部评审模型)
  - [4. 准备 Python 实验环境](#4-准备-python-实验环境可选)
- [🚀 快速开始](#-快速开始)
  - [1. 创建工作目录](#1-创建工作目录)
  - [2. 启动 Claude Code](#2-启动-claude-code)
  - [3. 告诉 `/mguide` 你想做什么](#3-告诉-mguide-你想做什么)
  - [4. 阅读结果](#4-阅读结果)
- [📖 进一步阅读](#-进一步阅读)
- [🙏 致谢](#-致谢)
- [📄 引用](#-引用)

---

## 📖 概述

**Mechanist** 将关于大语言模型内部机理的研究问题转化为**有证据支持的科学发现**。它全流程自动协调：文献检索 → 假设提出 → 实验实现与执行 → 鲁棒性验证 → 迭代精炼。

**Mechanist 以 Claude Code 插件形式分发**——无需克隆本仓库。几分钟内完成安装，交给它一个研究问题，它会在你自己的机器和 GPU 上跑实验，并交回一份可核验的研究报告。（Codex 支持即将推出。）

### 核心能力

| 阶段 | 描述 |
|:---|:---|
| **文献综述** | 检索 14k 篇可解释性论文语料库、157M 节点跨学科引用网络及网络资源。 |
| **假设提出** | 生成经过新颖性检验的断言，或从用户提供的材料中抽取断言。 |
| **实验执行** | 生成实验代码，运行评估，按机理感知计划记录结果。 |
| **验证** | 在替代模型、数据集和方法下评估断言的鲁棒性。 |
| **迭代** | 审视失败或薄弱的结果，更新计划并重跑相关阶段。 |

---

## 🔄 工作流程

```
 研究问题 ──▶ 提出断言 ──▶ 实验执行 ──▶ 鲁棒验证 ──▶ 审稿迭代 ──▶ 科学发现
            (假设)      (执行)      (验证)      (精炼)
```

研究流水线由一个**编排器（orchestrator）**和四个串行阶段组成，每个阶段运行在独立的子智能体中：

1. **Claim（断言提出）**——检索文献，生成或捕获假设，评估新颖性与影响力，产出详细实验计划。
2. **Experiment（实验执行）**——路由选择合适的机理方法，生成实验代码，运行健全性检查，部署实验并收集结果。
3. **Verify（鲁棒验证）**——沿方法、数据集、模型三个维度做 swap 变体，运行完整性审计。
4. **Iteration（迭代精炼）**——外部 LLM 审稿 + 结构化修复路由（最多 6 轮），将断言收敛至可发表水平。

所有结果记录在 **Claim Ledger**（`CLAIMS_LEDGER.md`）中，逐条跟踪每个断言的完整旅程。

---

## 🔧 安装

### 1. 安装 Claude Code 与 uv

Mechanist 运行在 Claude Code 之内——请先安装 Claude Code CLI：

```bash
# 安装 Claude Code，重启终端后验证
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Mechanist 的 MCP 服务使用 `uv` 管理 Python 环境——接着安装 uv：

```bash
# Mechanist 的 MCP 服务用 uv 启动临时 Python 环境
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

### 2. 安装 Mechanist 插件

在 Claude Code 会话中执行：

```text
/plugin marketplace add zjunlp/Mechanist
/plugin install mechanist@mechanist
```

然后激活并验证：

```text
/reload-plugins   # 仅当安装摘要提示时需要
/help             # 应出现 /mechanist:mguide
/mcp              # llm-chat 与 mechanic-db 均应为 "connected"
```

> 若命令仍未出现，重启 Claude Code 后再试。

### 3. 配置外部评审模型

Mechanist 在每一阶段都会用**外部评审模型**交叉验证自己的 idea、实验设计与结论——该模型须独立于 Claude，避免同模型自评。**不要使用 Claude 系列模型担任此角色。** 推荐通过 [platform.openai.com](https://platform.openai.com) 使用 GPT-5.4（`gpt-5.4`）；填入标准 OpenAI key 后，下方默认值即可。若使用 Azure、DeepSeek、通义千问或第三方中转，请将三个变量都指向 OpenAI 兼容端点。

| 环境变量 | 是否必填 | 默认 / 示例 | 用途 |
|:---|:---|:---|:---|
| `LLM_API_KEY` | **必填** | `sk-…` | 外部评审模型 API key（交叉验证）。 |
| `LLM_MODEL` | 可选 | `gpt-5.4` | 外部评审模型名称。 |
| `LLM_BASE_URL` | 可选 | `https://api.openai.com/v1` | LLM 服务端点；使用中转时填中转 URL。 |

将以下内容写入 `~/.bashrc`（或 `~/.zshrc`）：

```bash
# --- Mechanist（写入 ~/.bashrc 或 ~/.zshrc）---
export LLM_API_KEY="sk-..."                       # 必填：外部评审模型 key
export LLM_MODEL="<your_model_name>"              # 可选，默认：gpt-5.4
export LLM_BASE_URL="<your_base_url>"             # 可选，默认：官方端点
```

加载新变量并确认 key 已生效：

```bash
source ~/.bashrc            # 或新开一个终端
echo "$LLM_API_KEY"         # 应打印你的 key，而不是空行
```

> [!NOTE]
> **环境变量只在 Claude Code 启动时读取。** 在已运行的会话里 `export` 不会生效。请编辑 `~/.bashrc` → `source`（或新开终端）→ 再重启 Claude Code。

### 4. 准备 Python 实验环境（可选）

Mechanist 在启动 Claude 会话时所在的 Python 环境中跑实验。若尚未安装实验常用包（PyTorch、NumPy、scikit-learn 等），可用下面命令创建 conda 环境。我们提供的 `scientist` 环境覆盖了 Mechanist 跑实验时常用的工具：

```bash
# 示例：名为 scientist 的专用 conda 环境
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/zjunlp/Mechanist/main/requirements.txt)
```

完成以上步骤后，继续阅读[快速开始](#-快速开始)。

---

## 🚀 快速开始

新建一个空文件夹，在其中启动 Claude Code，然后用自然语言告诉 **`/mguide`** 你想做什么。它会通过对话帮你理清研究需求，替你写好 `task.md`——描述本次实验任务的说明文档，也是后续整条流水线的起点——你确认后直接跑起来。

```
 /mguide "你想做的事"
     │   它帮你理清你的研究需求
     ▼
 task.md
     │   它替你写好的任务说明书，你确认后开跑
     ▼
 claim ──▶ experiment ──▶ verify ──▶ iteration
     │   自主流水线：提出断言 → 跑实验 → 鲁棒验证 → 审稿迭代
     ▼
 CLAIMS_LEDGER.md + AUTO_PIPELINE_REPORT.md
     (研究发现)
```

### 1. 创建工作目录

```bash
mkdir my-experiment && cd my-experiment   # 每个研究问题对应一个目录
```

Mechanist 会在此目录内工作，并将所有产出写入其中。

### 2. 启动 Claude Code

> [!NOTE]
> 推荐使用 `claude-opus-4-8` 以获得良好表现。较弱模型会拖累整条流水线。

```bash
claude --model claude-opus-4-8
```

### 3. 告诉 `/mguide` 你想做什么

`/mguide` 是唯一入口——不需要学参数，也不需要记文件格式，用你自己的话描述目标即可：

**跑一次研究**——探索机理、复现论文、验证可疑现象，或者只给一个大方向、让它自己挖出现象：

```text
/mguide Reproduce this paper: LLMs encode harmfulness and refusal separately
```

**检索文献**——在 14k 篇可解释性论文语料库、157M 节点引用网络及网络资源中搜索：

```text
/mguide 帮我找找 sparse autoencoder feature absorption in large language models 相关的论文
```

**了解一个领域的发展**——关键论文、转折点、主要争论与开放问题的时间线：

```text
/mguide 我想知道 circuit-level interpretability 是怎么一步步走到今天的
```

对于研究任务，`/mguide` 只会问它无法推断的信息——用哪个模型和数据集、权重放在哪里、可以花多少 GPU 时间——然后把 `task.md` 写入当前目录、拿给你过目，待你确认后启动运行。

### 4. 阅读结果

运行会按顺序执行四个阶段——**claim → experiment → verify → iteration**——并在进入下一阶段前将本阶段文档写入磁盘（`idea-stage/`、`refine-logs/`、`verify/`、`review-stage/`、`runs/`）。结束后，优先阅读项目根目录下的这两个文件：

| 文件 | 内容 |
|:---|:---|
| `CLAIMS_LEDGER.md` | 各断言记分板：最终判决、鲁棒性与注意事项。 |
| `AUTO_PIPELINE_REPORT.md` | 本轮旅程、全部产物索引，以及仍需你处理的 Open Items。 |

> 想自己驾驶流水线——流水线模式、手写 `task.md`、GPU 预算、硬约束、多轮研究？见[用户指南](user_guide_zh.md)。

---

## 📖 进一步阅读

- **[用户指南](user_guide_zh.md)**——`/mguide` 背后的命令、流水线模式与完整参数参考、手写 `task.md`、GPU 预算与硬约束、多轮研究、文献管理、批量假设生成与实验隔离。
- **[开发者指南](developer_guide_zh.md)**——面向需要本地修改 skill 提示词、agent 定义或 MCP 服务代码的贡献者。

---

## 🙏 致谢

我们谨对ARIS为本项目所做的贡献表示衷心感谢，因为我们在项目中使用了其部分源代码。
同时，衷心感谢社区所有同仁提交问题并提供技术支持。

---

## 📄 引用

如果您使用了 Mechanist，请引用：

```bibtex
@article{wang2026mechanist,
  title={Mechanist: AI as a Scientific Instrument for Discovering the Mechanisms of Intelligence},
  author={Wang, Mengru and Fang, Junfeng and Qiao, Shuofei and Xu, Zhenqian and Xu, Haoming and Wang, Haoxiong and Deng, Shumin and Yang, Linyi and Cui, Zhixiang and Xu, Xin and others},
  journal={arXiv preprint arXiv:2608.12036},
  year={2026}
}
```