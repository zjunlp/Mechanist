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
  - [2. 编写 `task.md`](#2-将研究任务写成-taskmd)
  - [3. 运行 `/auto`](#3-启动-claude-code-并运行-auto)
  - [4. 跟踪运行并阅读结果](#4-跟踪运行然后阅读结果)
- [📚 使用指南](#-使用指南)
  - [`/auto`——自主流水线](#auto自主流水线)
  - [`/msearch`——文献检索](#msearch文献检索)
  - [`/mhistory`——主题发展历程](#mhistory主题发展历程)
- [📖 进一步阅读](#-进一步阅读)
- [📄 引用](#-引用)
- [🙏 致谢](#-致谢)

---

## 📖 概述

**Mechanist** 将关于大语言模型内部机理的研究问题转化为**有证据支持的科学发现**。它全流程自动协调：文献检索 → 假设提出 → 实验实现与执行 → 鲁棒性验证 → 迭代精炼。

**Mechanist 以 Claude Code 插件形式分发**——无需克隆本仓库。几分钟内完成安装，交给它一个研究问题，它会在你自己的机器和 GPU 上跑实验，并交回一份可核验的研究报告。（Codex 支持即将推出。）

最新的安装步骤与上手教程见网站 [Quick Start](http://mechanist.openkg.cn/#/quick-start) 页面。

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

`/auto` 流水线由一个**编排器（orchestrator）**和四个串行阶段组成，每个阶段运行在独立的子智能体中：

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
/help             # 应出现 /mechanist:auto、/mechanist:msearch、/mechanist:mhistory
/mcp              # llm-chat 与 mechanic-db 均应为 "connected"
```

> 若命令仍未出现，重启 Claude Code 后再试。

### 3. 配置外部评审模型

Mechanist 在每一阶段都会用**外部评审模型**交叉验证自己的 idea、实验设计与结论——该模型须独立于 Claude，避免同模型自评。**不要使用 Claude 系列模型担任此角色。** 推荐通过 [platform.openai.com](https://platform.openai.com) 使用 GPT-5.6 Luna（`gpt-5.6-luna`）；填入标准 OpenAI key 后，下方默认值即可。若使用 Azure、DeepSeek、通义千问或第三方中转，请将三个变量都指向 OpenAI 兼容端点。

| 环境变量 | 是否必填 | 默认 / 示例 | 用途 |
|:---|:---|:---|:---|
| `LLM_API_KEY` | **必填** | `sk-…` | 外部评审模型 API key（交叉验证）。 |
| `LLM_MODEL` | 可选 | `gpt-5.6-luna` | 外部评审模型名称。 |
| `LLM_BASE_URL` | 可选 | `https://api.openai.com/v1` | LLM 服务端点；使用中转时填中转 URL。 |

将以下内容写入 `~/.bashrc`（或 `~/.zshrc`）：

```bash
# --- Mechanist（写入 ~/.bashrc 或 ~/.zshrc）---
export LLM_API_KEY="sk-..."                       # 必填：外部评审模型 key
export LLM_MODEL="<your_model_name>"              # 可选，默认：gpt-5.6-luna
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

创建工作目录，用自由格式的 Markdown 文件 `task.md` 描述研究问题，然后打开 Claude Code 运行 `/auto`，即可启动自主研究流水线。

```
 task.md  ──▶  /auto  ──▶  CLAIMS_LEDGER.md + AUTO_PIPELINE_REPORT.md
 (你的输入)     (执行引擎)     (研究发现)
```

### 1. 创建工作目录

为本次研究任务新建一个空文件夹。Mechanist 会在此目录内工作，并将所有产出写入其中。

```bash
mkdir my-experiment && cd my-experiment   # 每个研究问题对应一个目录
```

### 2. 将研究任务写成 `task.md`

在项目根目录放置名为 `task.md` 的自由格式 Markdown 文件，用自然语言写清研究问题。常见问法包括：

| 你可以让 Mechanist 做的事 | 思路 |
|:---|:---|
| **探索机理** | 已知模型行为——找出哪个内部组件导致了它。 |
| **复现论文** | 发现与方法均已知——按既定规模忠实复现。 |
| **验证可疑现象** | 已有具体假设，但尚无论文或先前实验确认。 |
| **开放式发现** | 只有研究方向——先让 Mechanist 挖出现象，再深入调查。 |

> 完整参考见[编写 task.md](#编写-taskmd)——你可以指定模型路径、GPU 预算、硬约束等更多细节。

### 3. 启动 Claude Code 并运行 `/auto`

> [!NOTE]
> 推荐使用 `claude-opus-4-8` 以获得良好表现。较弱模型会拖累整条流水线。

在项目根目录启动 Claude Code：

```bash
claude --model claude-opus-4-8
```

在会话中直接运行 `/auto`。它会读取 `task.md` 并自动跑完整条研究流水线：

```text
/auto
```

### 4. 跟踪运行，然后阅读结果

Mechanist 按顺序执行四个阶段——**claim → experiment → verify → iteration**——并在进入下一阶段前将本阶段相关文档写入磁盘：

| 阶段 | 关键产物 |
|:---|:---|
| **claim** | `idea-stage/IDEA_REPORT.md` — 候选 idea 排序，或从 `task.md` 捕获的行为与断言<br>`refine-logs/FINAL_PROPOSAL.md` — 精炼后的方法提案<br>`refine-logs/EXPERIMENT_PLAN.md` — 各断言里程碑、模型、数据与成功标准 |
| **experiment** | `refine-logs/MECHANISM_ROUTING.md` — 所选可解释性方法及理由<br>`refine-logs/EXPERIMENT_RESULTS.md` — 各断言结果与基线判决<br>`runs/` — 各次实验的代码、日志与 GPU 开销 |
| **verify** | `verify/VERIFY_REPORT.md` — 鲁棒性判决与跨断言摘要<br>`verify/INTEGRITY_AUDIT.md` — 对原始结果与 swap 跑的诚实性审计 |
| **iteration** | `review-stage/AUTO_REVIEW.md` — 逐轮审稿记录<br>`review-stage/AUTO_ITERATION_FINAL_REPORT.md` — 修复循环中各断言的变化 |

结束后，优先阅读项目根目录下的这两个文件：

| 文件 | 内容 |
|:---|:---|
| `CLAIMS_LEDGER.md` | 各断言记分板：最终判决、鲁棒性与注意事项。 |
| `AUTO_PIPELINE_REPORT.md` | 本轮旅程、全部产物索引，以及仍需你处理的 Open Items。 |

通过[流水线模式](#流水线模式)控制行为和机理发现的处理方式。归档 / 下一轮流程与进阶用法见[用户指南](user_guide_zh.md)。

---

## 📚 使用指南

### `/auto`——自主流水线

`/auto` 由**两条正交参数轴**驱动，各管一个阶段：

| 参数轴 | 取值 | 用途 |
|:---|:---|:---|
| **`behavior-source`** | `given` / `given-validation` / `discovery` | 控制行为来源及是否运行 M0（现象验证）。 |
| **`mechanism`** | `given` / `discovery` | 控制由谁选择机理方法——用户指定或系统路由。 |

> 不带参数运行 `/auto` 默认等价于 `behavior-source: given, mechanism: discovery`。

#### 流水线模式

两轴正交，共 3×2=6 种组合均合法。以下为四种最常用模式：

| 模式 | 命令 | 适用场景 |
|:---|:---|:---|
| **论文复现** | `/auto — behavior-source: given, mechanism: given` | 复现一篇论文：你指定行为、机理方法、模型和数据，强制严格资源保真度。 |
| **给定行为 + 探索机理** | `/auto — behavior-source: given, mechanism: discovery` | 行为已被验证；系统探索其背后的机理。 |
| **验证行为 + 探索机理** | `/auto — behavior-source: given-validation, mechanism: discovery` | 你提出行为但希望先通过 M0 验证，再探索机理。 |
| **全自动发现** | `/auto — behavior-source: discovery, mechanism: discovery` | 全自主：流水线发现现象并路由至合适的机理方法。 |

> [!NOTE]
> **查看最终结果：**`/auto` 每轮结束后，优先阅读项目根目录的 `CLAIMS_LEDGER.md`（各断言记分板）与 `AUTO_PIPELINE_REPORT.md`（本轮旅程、产物索引与 Open Items）。各阶段产物会写在 `idea-stage/`、`refine-logs/`、`verify/`、`review-stage/`、`runs/` 下——详见[跟踪运行](#4-跟踪运行然后阅读结果)。

#### 编写 task.md

`task.md` 是每个项目目录下的**任务说明书**。正文为自由格式自然语言，无固定 schema。

**`task.md` 应包含的内容：**

| 内容 | 何时必需 | 说明 |
|:---|:---|:---|
| **behavior** | `behavior-source: given` / `given-validation` | 提供一个具体、可证伪的现象。 |
| **topic** | `behavior-source: discovery` | 提供一个想研究的大方向，细节由 Mechanist 自己挖掘。 |
| **family** | `mechanism: given` | 提供一个具体机理方法（如 Fisher information / steering vectors）。 |
| **model / data** | 推荐 | 实验用的模型与数据（写清路径）。复现模式下必填。 |
| **claim 列表 / goal** | 可选 | 你希望验证的若干条断言以及本轮目标。 |

#### 声明计算资源

在 `task.md` 中用自然语言写明 GPU 预算和卡数：

```text
你有 8 小时的 GPU 预算，在 GPU 用时达到预算前，不要以预算为理由暂停或简化实验。
你同时最多只能占用 8 张 GPU 中的 4 张。
```

- **充足的预算会增大智能体的实验能力**——它在告诉智能体"别为省成本而简化或放弃实验"，而不仅是上限。
- 也可以把资源分配到具体阶段（如"主实验最多用 4 张卡，verify 变体最多 2 张"）。
- GPU 预算属于**硬约束**：Agent 会将每次实验控制在预算内再启动，预算真的不够时会停下并上报。

#### 声明硬约束

在 `task.md` 中用自然语言声明不可妥协的要求。编排器会自动分类并将每条约束分发到相关阶段。

```text
所有实验必须严格使用 Llama-3-8B。不要用 Pythia 2.8B。
验证 claim 3 时只用 Pythia 1B 和 410M，暂时不要跑 2.8B。
```

智能体将硬约束视为红线。如果确实无法在约束下完成，会停下并上报，而非擅自突破。关于约束分类、作用域以及硬约束与告知性注意事项的区别，详见[用户指南](docs/user_guide_zh.md#可靠性与最佳实践)。

#### 进展通知

在 `task.md` 中用自然语言表达通知意图：

```text
当实验取得进展时，向我的邮箱 example@gmail.com 发送通知，每小时同步一次。
```

启用后，流水线会在关键触点（实验完成 / verify 完成 / 全部结束 / halt / 需要人工介入）自动推送简报，并按小时同步进展。不写通知意图时，通知功能完全静默。

> [!NOTE]
> 你需要自行配置通知渠道。Mechanist 只扫描本地已配好的通知渠道并调用发送，不负责安装或推荐任何具体通知工具。

#### 多轮研究

`/auto` 跑完一轮后，用 `/next-round` 将产物归档至 `rounds/round_<N>/` 并起草下一轮 `task.md`。它读取 `research_memory.json`，自动避开已定论的现象和机理方向。

```bash
# 探索全新现象
/next-round new-behavior
#   推荐下一轮：/auto — behavior-source: discovery, mechanism: discovery

# 保留同一现象，换机理方向深入
/next-round new-mechanism B1
#   推荐下一轮：/auto — behavior-source: given, mechanism: discovery

# 让系统按上一轮结论推荐
/next-round
```

归档前 `/next-round` 会打印哪些将被搬走、哪些将保留。产物进入 `rounds/round_<N>/`，而 `task.md`、`research_memory.*`、`.claude/`、`.mcp.json` 和 `.git` 留在根目录。`new-mechanism` 变体还会额外保留 `data/` 和 `cache/` 以复用同一现象的激活数据。

**多轮守卫：**每轮 `/auto` 启动时检测根目录是否有上一轮未归档的产物。若存在则 halt，提示三选一：运行 `/next-round`（归档后继续，推荐）、`resume: true`（继续未完成的一轮）或手动删除列出的产物。即使是全自动模式也会触发此守卫——绝不会静默覆盖上一轮的工作。

**重访已定论方向：**默认情况下 `/auto` 会避开 `research_memory.json` 中已标记为定论的行为或机理方向。如果你在 `task.md` 中指定了一个已定论方向但未授权重做，流水线会将其视为可能的疏忽，在全自动模式下静默换为未尝试的方向，在交互模式下弹窗确认。若要强制重做，在 `task.md` 中添加：

```markdown
retry-settled: true
```

---

### `/msearch`——文献检索

`/msearch` 检索领域相关文献：在 14k 篇可解释性论文语料库、157M 节点引用网络及网络资源中搜索，返回经过整理和排序的相关论文列表。适合了解某个主题的研究现状，或检查某个假设是否已被探索过。

```text
/msearch "sparse autoencoder feature absorption in large language models"
```

---

### `/mhistory`——主题发展历程

`/mhistory` 生成领域发展史：追溯某个研究主题的学术演进脉络——关键论文、转折点以及思想如何发展。输出为结构化的叙事，帮助你将自己的工作置于文献背景中，或发现尚未被充分探索的方向。

```text
/mhistory "the evolution of circuit-level interpretability"
```

生成的时间线涵盖奠基性论文、方法学突破、主要争论和开放问题——一份给定主题的领域发展轨迹紧凑图谱。

---

## 📖 进一步阅读

- **[用户指南](user_guide_zh.md)**——流水线架构详解、完整参数参考、基于参考论文工作、文献管理、批量假设生成、实验隔离与可靠性最佳实践。
- **[开发者指南](developer_guide_zh.md)**——面向需要本地修改 skill 提示词、agent 定义或 MCP 服务代码的贡献者。

---

## 🙏 致谢

我们谨对ARIS为本项目所做的贡献表示衷心感谢，因为我们在项目中使用了其部分源代码。
同时，衷心感谢社区所有同仁提交问题并提供技术支持。