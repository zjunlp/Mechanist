# Mechanist — Autonomous Research Agent for LLM Mechanistic Interpretability

**Mechanist converts a research question into evidence-backed findings.** Given a question about the internal mechanisms of a large language model, Mechanist coordinates the research workflow: literature retrieval, hypothesis formulation, experiment implementation and execution, robustness validation, and iterative refinement.

Mechanist is distributed as a **Claude Code plugin**; using it does **not** require cloning this repository.

**Automated workflow coverage:**

- **Literature review** — queries a 14k-paper interpretability corpus, a 157M-node cross-disciplinary citation graph, and web sources.
- **Hypothesis formulation** — proposes a novelty-checked claim, or extracts claims from user-provided material.
- **Experiment execution** — generates experiment code, runs evaluations, and records results against a mechanism-aware plan.
- **Verification** — evaluates claims under alternate models, datasets, and methods.
- **Iteration** — reviews failed or weak results, updates the plan, and reruns the relevant stages.

```
 research question ──▶ claim ──▶ experiment ──▶ verify ──▶ iterate ──▶ findings
                    (hypothesis)  (execution) (validation) (refinement)
```

本项目提供两种安装模式：

- **插件模式安装**：最适合普通用户，开箱即用（本文档介绍的安装方法）。
- **开发模式安装**：最适合测试者 / 开发者，本地改 skill 提示词或辅助代码后便于调试（参考 [README_dev](./README_dev.md)）。

## 1 安装 Claude Code 与基础依赖

### 1.1 安装 Claude Code

先安装并登录 Claude Code。

```bash
# 下载并安装 Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# 安装后重启终端，验证安装
claude --version
```

> [!IMPORTANT]
> **本项目要求 Claude Code 使用 Opus 4.7 模型。** 每次启动时通过 `--model` 指定，或在会话内用 `/model` 选择 Opus 4.7。
> ```bash
> claude --model claude-opus-4-7
> ```

### 1.2 安装 uv

Mechanist MCP 服务使用 uv 启动临时 Python 环境。

```bash
# 下载并安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装后重启终端，验证安装
uv --version
```

### 1.3 Create a conda environment

Create a dedicated conda environment `scientist` for the experiment execution stage and install its dependencies:
```bash
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/WangHX2024/homepage/main/requirements.txt)
```

> TODO：上述链接 `WangHX2024/homepage` 在正式上线版本将被替换为 `zjunlp/MECHANIST`。

### 1.4 配置环境变量

Mechanist 的两个 MCP server 通过**环境变量**读取配置。请提前准备好下表的值，并按本节末尾「设置环境变量」设置好。

| 环境变量 | 是否必填 | 示例 / 默认值 | 用途 |
|---|---|---|---|
| `LLM_API_KEY` | 必填 | `sk-…` | 外部评审模型 API key，用于交叉验证。未设置时 `llm-chat` 会连上但调用报错。 |
| `LLM_MODEL` | 可选 | 默认 `gpt-5.4` | 外部评审模型名称。 |
| `LLM_BASE_URL` | 中转站看情况填 | 默认 `https://api.openai.com/v1` | 如果经过中转站使用 `LLM_MODEL`（比如 gpt-5.4），则需填中转站的 url。 |
| `LLM_FALLBACK_MODEL` | 可选 | 默认 `gpt-5.4` | server 在主模型 504 超时时的回退模型。 |
| `MECHANIC_DB_API_KEY` | 可选 | `sk_…` | Mechanic-DB 论文检索服务 key。未设置时 Mechanist 会跳过 Mechanic-DB，仅使用本地 PDF、Web 搜索、arXiv、Semantic Scholar；后续可随时补填。 |

#### 配置外部评审模型

外部评审模型在工作各阶段独立审阅 Claude 给出的 idea、实验设计与结论，提供交叉验证，避免同模型自评带来的 correlated failure。因此**不能使用 Claude 系列模型**作为外部评审模型。

- 推荐使用 GPT-5.4 作为外部评审模型，可前往 `https://platform.openai.com` 注册账号并获取官方 key 填入 `LLM_API_KEY`。此时 `LLM_MODEL` 与 `LLM_BASE_URL` 使用默认值即可（可不设置）。
- 若改用其它模型提供商（如 Azure / DeepSeek / 通义千问 / 第三方中转站等，需兼容 OpenAI 格式），需设置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。

#### 申请 `mechanic_db_api_key`

Mechanic-DB 是 Mechanist 自建的论文检索服务，背后是一个 14k 篇可解释性论文语料库 + 157M 节点的跨学科引用网络，在工作各阶段提供领域内论文的精准召回，相比通用 Web 搜索更聚焦、更详细。未配置 key 时 Mechanist 会跳过 Mechanic-DB，仅使用本地 PDF、Web 搜索、arXiv、Semantic Scholar 作为兜底。

第 1 步：向 Mechanic-DB 服务发起注册请求（把 `you@example.com` 换成你的真实邮箱）：

如果你用的是124.128.251.61这台服务器请使用localhost:9001，但如果使用的不是需要把所有 localhost:9001 换成 mechanist.openkg.cn，包括三个文件：
README_dev.md
README.md
mcp-servers/mechanic-db/server.py


```bash
curl -X POST http://localhost:9001/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com"}'
```
如果你用的是124.128.251.61这台服务器请使用localhost:9001，但如果使用的不是需要把所有 localhost:9001 换成 mechanist.openkg.cn，包括三个文件：
README_dev.md
README.md
mcp-servers/mechanic-db/server.py

> TODO：上述链接 `localhost:9001` 在正式上线版本将被替换为 `mechanist.openkg.cn`。现版本部署在 A800_2 服务器上，仅为测试使用。

第 2 步：打开邮箱中的验证邮件，点开验证链接（如果用的是localhost，记得在服务器上而非你的本机打开链接）。页面会显示一个 `sk_…` 开头的 API key。

- **该 key 只显示一次**，请立即复制并妥善保存，并在下方「设置环境变量」设置到 `MECHANIC_DB_API_KEY`。
- 若未能收取验证邮件，请检查验证邮件是否被误识别为垃圾邮件。

#### 设置环境变量

把上面准备好的值写进 `~/.bashrc`（或 `~/.zshrc`）：

```bash
# --- Mechanist ---
export LLM_API_KEY="sk-..."                       # 必填：外部评审模型 key
export LLM_MODEL="gpt-5.4"                         # 可选，默认 gpt-5.4
export LLM_BASE_URL="https://api.openai.com/v1"    # 可选，默认官方；中转站填中转站 url
export MECHANIC_DB_API_KEY="sk_..."               # 可选：不填则跳过 Mechanic-DB
```

改完执行 `source ~/.bashrc`（或重开一个新终端），用 `echo "$LLM_API_KEY"` 确认非空。


## 2 为 Claude Code 安装 Mechanist 插件

### 2.1 Add the marketplace and install

In Claude Code, run:

```text
/plugin marketplace add mengrusun/MECHANICA
/plugin install mechanist@mechanist
```

装好后，确保 §1.4「设置环境变量」已配置好，**重启 Claude Code**，再用 §2.2 验证。

### 2.2 Verify the installation

Restart Claude Code. Skills and helper servers are loaded automatically. Confirm the installation with two checks:

- Run `/help` and verify that Mechanist skills are available, for example `/mechanist:auto`, `/mechanist:msearch`, and `/mechanist:mhistory`.
- Run `/mcp` and confirm that both `llm-chat` and `mechanic-db` are marked as **connected**.

After both checks pass, open a new Claude Code session in your working directory and continue with §3 (quick start).

## 3 quick start

使用之前建议先阅读一下 [auto pipeline 总览](./overview_autopipeline.md)。

### Set up a project directory

Mechanist runs in a **per-project working directory** — one folder per research question. All inputs and generated artifacts live there. Create one and start a Claude Code session inside it:

#### 普通用户（插件模式）

如果你按 §2 以插件方式安装，直接在实验目录里启动 Claude Code 即可：

```bash
mkdir exp && cd exp
# 启动 Claude Code（每个研究问题一个独立目录）：
claude --model claude-opus-4-7
```

#### 开发者模式（`--plugin-dir`）

如果你按 [README_dev](./README_dev.md) 以开发模式安装，**每次**启动时都需要用 `--plugin-dir` 指向本地仓库，让 Claude Code 直接从本地读取插件，便于改动 skill 提示词或辅助代码后调试。

`exp` 与 `MECHANICA` 的存放位置没有硬性要求，但推荐放在同一个父目录下——这样既方便查看 `exp` 的实验结果，也方便修改 `MECHANICA` 并把改动提交到 GitHub 仓库：

```text
<dir>/
├── MECHANICA/   # clone 下来的本仓库（插件源码）
└── exp/         # 实验工作目录（每个研究问题一个）
    └── task.md  # 任务内容，内容详见 [auto explore](#auto-explore)
```

```bash
cd <dir>
mkdir exp && cd exp
# 启动 Claude Code 时追加 --plugin-dir 指向本地仓库：
claude --model claude-opus-4-7 --plugin-dir <dir>/MECHANICA
```

> [!NOTE]
> 开发模式下，改完 `skills/`、prompt 等文本后在会话内运行 `/reload-plugins` 即可生效；改动 MCP / helper server 的 Python 代码则需重启 Claude Code。详见 [README_dev §2.4](./README_dev.md)。

> [!NOTE]
> 要记得指定claude --model claude-opus-4-7，因为这个对应着我们scientist的 Orchestrator 用的是什么模型（llm-chat的配置以及autopipeline code中制定的是subagent的模型型号）

### search
/msearch "sparse autoencoder feature absorption in large language models"

### generate history development for a topic
/mhistory "the evolution of circuit-level interpretability"


### auto explore

`/auto` 由**两条正交的参数轴**驱动，各管一个阶段：

- **`behavior-source`（behavior 阶段）**：`given`（现象已给定且默认成立，不验证、不做 novelty）/ `given-validation`（现象由你给定，但先用 M0 验证是否成立）/ `discovery`（连 behavior 一起挖掘，跑完整 ideation + novelty + impact）。
- **`mechanism`（mechanism 阶段）**：`given`（你在 task.md 指定机理方法/family，系统直接用）/ `discovery`（系统自动路由选择机理方法）。

> 两轴正交，共 3×2=6 种组合都合法（例如 `behavior-source: given-validation, mechanism: given`）；上面是四种最常用的规范写法。裸跑 `/auto`（不带参数）等价于 `behavior-source: given, mechanism: discovery`。


下面是四种常用组合：

> [!NOTE]
> **下面四种组合的 `task.md` 具体写法各有一份示例可参考：**
> - `behavior-source: given, mechanism: given` → `./research_bgiven_mgiven/task.md`
> - `behavior-source: given, mechanism: discovery` → `./research_bgiven_mdiscovery/task.md`
> - `behavior-source: given-validation, mechanism: discovery` → `./research_bgivenvalidation_mdiscovery/task.md`
> - `behavior-source: discovery, mechanism: discovery` → `./research_bdiscovery_mdiscovery/task.md`

> [!NOTE]
> **task.md 怎么写，有一整节说明**，见 [§4 如何编写 task.md](#4-如何编写-taskmd)。


**1 behavior given + mechanism given**（即原来的 reproduction）— 复现一篇论文：行为和机理方法都由你给定，忠实抽取、跳过 ideation/novelty，使用用户提供的 model 和 data（盖 `resource_fidelity: strict`，禁止降档）。

- 进入工作区：`cd exp/`
- 创建 task.md，写明：behavior 是什么、用哪个机理方法、实验用的 data 和 model（此组合下 `task.md` 必填）

```bash
/auto — behavior-source: given, mechanism: given
```

**2 behavior given + mechanism discovery** — 现象已给定**且默认成立**（已被先前工作验证），直接探究该目标 behavior 背后的机理，不做存在性验证（无 M0），机理方法由系统路由选择。

- 进入工作区：`cd exp/`
- 创建 task.md，写明 behavior 是什么

```bash
/auto — behavior-source: given, mechanism: discovery
```

**3 behavior given-validation + mechanism discovery** — 现象由你给定，但**先验证它是否真的成立，成立才做机理**。和 `given` 一样从 task.md 取定行为（无需挖掘、无 novelty），区别在于实验计划会以一道 **M0 现象验证门** 开场，由实验阶段最先跑：四态判决 `established`/`conditional` → 继续做机制；`not-established` → 停止并出**负面结论报告**（跳过 verify + iteration）；`inconclusive` → 修正后重跑 M0。适用于"我指定了一个行为，但不确定它是否成立，想先验证再做机制"。

- 进入工作区：`cd exp/`
- 创建 task.md，写明要验证的具体 behavior 是什么（须具体可证伪，标准同 `given`）

```bash
/auto — behavior-source: given-validation, mechanism: discovery
```

**4 behavior discovery + mechanism discovery** — 全自动：现象也由 pipeline 发现，机理方法也由系统选择。

- 进入工作区：`cd exp/`
- 创建 task.md，写明想研究的 topic 是什么
```bash
/auto — behavior-source: discovery, mechanism: discovery
```

> [!NOTE]
> **查看最终结果**：`/auto` 每轮运行结束后，本轮的科学结论与整轮 pipeline 的终态都会汇总至工作目录根部的 `CLAIMS_LEDGER.md`。这是一份 claim-centric 的报告，逐条给出每条 claim 的陈述、所用数据 / 模型 / 实验方法、主实验结果、verify 判决，以及 iteration 阶段是否将其收窄或推翻，并合并为最终结论。查阅本轮产出、pipeline 走向与遗留问题，只需阅读该文件即可。


## 4 如何编写 task.md

`task.md` 是每个项目工作目录下的**任务说明书**。正文是**自由格式的自然语言**，没有固定 schema——示例里的 `##` 小节、排版都可任意改 / 删。

### 4.1 task.md 应该包含什么

正文自由发挥，但**能让系统读到**以下内容是有意义的。真正「必传」的随组合而变，其余都有默认兜底：

| 内容 | 何时必需 | 说明 |
|---|---|---|
| **behavior（一个具体、可证伪的现象）** | `behavior-source: given` / `given-validation` 必填 | 需是具体可观测的输出模式（最好带触发条件），而非一个泛泛的 topic。例：「模型把第一人称 `I believe X` 判为比对应第三人称断言更不可能为真」。 |
| **机理方法 / family**（或 behavioral-only 声明） | `mechanism: given` 必填 | 命名一个具体机理方法（如 Fisher information / steering vectors），否则 claim 阶段会停下报错。 |
| **topic（想研究的方向）** | `behavior-source: discovery` 必填 | 现象由 pipeline 自己挖，只需给一个大方向。 |
| **model / data** | 推荐 | 实验用的模型与数据（写清路径）。`behavior given + mechanism given`（复现）组合下必填，且会盖 `resource_fidelity: strict` 禁止降档；其余组合可选，不写则系统自行按成本感知选择。 |
| **claim 列表 / goal** | 可选 | 你想验证的若干条断言、以及本轮目标。 |

> [!NOTE]
> 一句话概括：命令行上的 `behavior-source` / `mechanism` 决定「必传什么」——given 系需要一个具体可证伪的 behavior，`mechanism: given` 需要一个命名的机理方法。其余（model / data / 各小节）都是自由发挥 + 有默认兜底。

### 4.2 声明计算资源（GPU 预算）

用自然语言在 `task.md` 里写明**实验阶段的 GPU 小时数预算和卡数预算**即可，系统会把它注入实验流程进行监控。例如：

```text
你有 8 小时的 GPU 预算，在 GPU 用时达到预算前，不要以 GPU 预算为理由暂停或简化实验。
你同时最多只能占用 8 张 GPU 中的 4 张。
```

- **充足的预算会增大 Agent 的实验能力**——它是在告诉 Agent「别为省成本而简化或放弃实验」，而不仅是一个上限。
- 除总量外，也可以把资源**分配到具体阶段**（例如「主实验最多用 4 张卡，verify 变体最多 2 张」），系统会按阶段分发（见 §4.3 的针对性分发）。
- GPU 预算属于**硬约束**（见下），非协商：Agent 会把每次实验规模压在预算内再启动，预算真的不够时会停下并上报，而不是偷偷超支。

### 4.3 声明硬约束与注意事项

`task.md` 里你写的内容，编排器会分成**两类**注入给各个 subagent，并**只分发给与之相关的那个阶段**（针对性分发），而不是一股脑塞给所有 subagent。

**① 硬约束** —— 三种：

| 类型 | 触发词 | 例子 |
|---|---|---|
| **负向禁令** | 不准 / 不要 / 禁止 / 绝不 | 「不要用 Pythia 2.8B」「禁止对数据做子采样」 |
| **强正向要求** | 必须 / 只能用 / 严格使用 / 就用 | 「必须严格使用 Llama-3-8B」「验证时只能用这两个模型」 |
| **算力 / 资源分配** | 见 §4.2 | GPU 小时 / 卡数预算、给某阶段分配的资源 |

Agent 会把硬约束当作不可逾越的红线——绝不超预算、绝不做被禁止的事、始终满足强正向指定；真的在约束下无法完成时会停下上报，而不是擅自突破。

**② 注意事项 / 告知（信息性，非权威）** —— 你指明了、但**没有强制语气**的内容，例如非强制的 model / dataset 选择、环境说明、偏好。系统会注入让相关 subagent「知晓」，但以实验计划 `EXPERIMENT_PLAN.md` 为权威；必要时 Agent 可以调整，但不会**擅自丢弃**——有冲突会上报而非自作主张。

> [!NOTE]
> **针对性分发（关键）**：约束可以**限定到某个阶段或某条 claim**，编排器会只把它分发给对应的 subagent，不会污染其它阶段。用自然语言点明范围即可，例如：
> ```text
> 验证 claim 3 时只用 Pythia 1B 和 410M，暂时不要跑 2.8B。
> ```
> 这条只会进入 **verify 阶段**（以及负责写计划的 claim 阶段），**不会**误传给主实验——如果主实验的其它 claim 本就需要 2.8B，就不会被这条 verify-only 的限制误伤。同理，可以给 Experiment Stage 和 Verify Stage 分别约束不同的 model / dataset。

### 4.4 声明进展通知

用自然语言在 `task.md` 里表达通知意图即可，例如：

```text
当实验取得进展时，向我的邮箱 example@gmail.com 发送通知，每小时同步一次。
```

启用后，pipeline 会在关键触点（实验完成 / verify 完成 / 全部结束 / halt / 需要人工介入）自动推送简报，并按小时同步进展。

> [!NOTE]
> **通知渠道需要你自行配置**：本项目只扫描你**已配置好的**通知渠道，调用并发送；不写通知意图时，通知功能完全静默、对 pipeline 零影响。

---

## 5 高阶使用技巧细节

`/auto` 的所有参数都写在命令尾部：以 ` — `（前后带空格的破折号，`--` 亦可）起头，后接 `key: value`，多个用逗号分隔。key 推荐连字符式（`auto-proceed`、`ref-paper`、`base-repo`），下划线 / 大写 env 式（`AUTO_PROCEED`）也兼容。下面按"输入从哪来"挑几类最常用的，全部给 CLI 写法。


### 常用参数设置和使用

note: 注意如果和任务相关的内容都写在了task.md，可以省略"direction"，比如直接 /auto — auto-proceed: false 

```bash
/auto "direction" — auto-proceed: false                       # 每个 gate 停下来问你，关闭全自动
/auto "direction" — GPU_ID=4                                  # 设置本次实验使用的gpu_id
/auto "direction" — claim-model: opus, verify-model: sonnet   # 按阶段单独指定模型
/auto "direction" — dimensions: method,dataset                # verify 在哪些轴上做鲁棒性互换（每轴一个变体）
# /auto "direction" — resume: true                              # 崩溃后接着跑，已完成的阶段自动跳过
/auto "direction" — review-loop: false                        # 跑到 verify 为止，不进迭代环
```

### 高阶使用说明

#### resume

这个功能暂时不要用，还没来得及check逻辑

#### 基于已有代码库 — `base-repo:`

给一个 GitHub 仓库 URL，experiment 阶段会在动手实现前先 clone 它，在它的基础上改 / 扩。常与 `ref-paper:` 同用，做"拿这份代码改进这篇论文"。

```bash
/auto "reproduce and extend their probing setup" — base-repo: https://github.com/org/their-repo

# 论文 + 代码一起给
/auto "improve this paper with this codebase" — ref-paper: papers/x.pdf, base-repo: https://github.com/org/their-repo
```


#### next-round

`/auto` 跑完一轮、想"更进一步"开新一轮时，用 `/next-round` 做过渡：它替你**归档上一轮产物**、**起草下一轮 `task.md`**，但"探什么"始终由你定。它依赖 `/auto` 每轮自动维护的全局记忆 `research_memory.json`，因此下一轮会自动避开已定论的现象 / 机理方向。

```bash
# 换一个全新现象去探
/next-round new-behavior
#   推荐下一轮：/auto — behavior-source: discovery, mechanism: discovery

# 留着老现象 B1，换一个没试过的机理方向深挖
/next-round new-mechanism B1
#   推荐下一轮：/auto — behavior-source: given, mechanism: discovery （把 B1 现象写进新 task.md）

# 不确定就直接调用：它读 memory、按上一轮结论推荐一种，再用问答让你确认
/next-round
```

调用后它会先打印"要搬的 / 要留的"再归档：产物进 `rounds/round_<N>/`，而 `task.md` / `research_memory.*` / `.claude` / `.mcp.json` / `.git` 留在根目录（`new-mechanism` 还会额外保留 `data/`、`cache/` 复用同一现象的激活）。然后起草一份带"已探索（勿重复）"摘要的新 `task.md`——你审阅 / 微调后，再手动 `/auto` 开下一轮。

> 防呆：若你忘了 `/next-round` 就直接又开 `/auto`，开头的 multi-round 护栏会检测到根目录有未归档产物并 **halt**，提示三选一：`/next-round`（归档再开，推荐）/ `resume: true`（继续这未完成的一轮）/ 手动删除列出的产物。即使全自动模式也会停下，绝不默默覆盖上一轮。

#### 想重做一个"已定论"的方向 — `retry-settled`

`research_memory.json` 把已定论（behavior `established`/`conditional`/`not-established`，机理方向/family `confirmed`/`refuted`）的东西记着，下一轮 `/auto` **默认避开**它们。所以你即使在新 `task.md` 里 pin 了一个**已经做过**的方向，系统也会当成"你可能忘了它做过"，自动**换一个没试过的**——而不是重跑。

要**强制重做**某个已定论方向（比如想用更大样本 / 修好的对照再验一次），在 `task.md` 里加一行：

```
retry-settled: true
```

- **默认 `false`**（不写这行 = 不重做）：pin 命中已定论项时，全自动会静默换成未试方向；人机交互模式下会弹窗问你（honor / 换新，默认推荐换新）。
- **`retry-settled: true`**：授权重做——pin 命中的已定论项被**如实重跑**，全自动也不再拦。

```bash
# task.md 里同时写明 pin + 重做意图：
#   mechanism direction: Location
#   retry-settled: true
/auto — behavior-source: given, mechanism: discovery
```

> 它是个 `task.md` 级开关，对该轮里所有"撞上已定论记忆"的 pin 统一生效；只影响这一类冲突，不改变其它任何 gate。


---

#### 从具体论文出发 — `ref-paper:`

给一篇参考论文（本地 PDF / arXiv abs 链接 / 任意论文 URL），claim 阶段会先把它读成 `idea-stage/REF_PAPER_SUMMARY.md`，后续 idea 生成都建立在它之上。

```bash
# 本地 PDF
/auto "improve feature disentanglement in sparse autoencoders" — ref-paper: papers/sae.pdf

# arXiv 链接（会顺手把 PDF 下到 papers/）
/auto "extend this analysis to multimodal models" — ref-paper: https://arxiv.org/abs/2401.01234
```


#### 喂自己的文献 — `literature/` 目录

不用参数。在实验目录下建 `literature/` 文件夹，把你的必引文献 / 阅读清单 PDF 丢进去——文献综述阶段每轮都会扫它。它是**只读的用户精选通道**，pipeline 从不改写 / 删除；与 pipeline 自动下载落到 `papers/` 的机器通道并行，同名论文以 `literature/` 里的为准。

```bash
mkdir -p literature
cp ~/Downloads/*.pdf literature/    # 此后任意一轮 /auto 都会带上这些文献
```

想跑前单独看一眼综述、或扩大检索面，可直接用 `/research-lit`：

```bash
/research-lit "your topic" — extra: semantic-scholar, deepxiv   # 叠加额外检索源
/research-lit "your topic" — arxiv download: true               # 把最相关的几篇 arXiv 下到 papers/
```





#### hypothesis-batch

批量生成某 topic 的 behavior + mechanism 假设到 `hypothesis_library.json`,每条带 novelty 打分、LLM 语义去重。

1） discover:没给 behavior,连 behavior 一起挖(behavior 轴走发现策略,每个 behavior 再按 /mechanism-explore 的组合策略挂 mechanism)(默认)
/hypothesis-batch "LLM beliefs"

2）given:固定 behavior,只补 mechanism;behavior 可为节点 id 或自由文本
/hypothesis-batch "LLM beliefs" — behavior: "模型在多轮对话中倾向维持首轮立场"
/hypothesis-batch "LLM beliefs" — behavior: B3

3）控制规模:n-behaviors 每轮新增 behavior 数(默认 10, 仅在behavior为discover的模式下生效)
/hypothesis-batch "LLM beliefs" — n-behaviors: 12

4）连续多轮:rounds 在一次调用里连续跑几轮(默认 1)。每轮跑完一整套 生成→去重→打分→写库,先把这一轮结果累积进 `hypothesis_library.json` 再进下一轮;下一轮会用更新后的库重建 banlist,所以前面轮已生成的 behavior 不会被重复生成。某轮去重后新增为 0 表示话题已挖尽,会提前停并在报告里说明。例:rounds 5 + n-behaviors 10 ≈ 一次调用累积出 ~50 个不重复 behavior
/hypothesis-batch "LLM beliefs" — rounds: 5, n-behaviors: 10

5）novelty:每条假设打一个新颖度分(粗筛用,判断是否已有人做过)。默认会先做一次 web/arXiv 检索、再让模型据此打分(更准);novelty-web: false 跳过检索、纯靠模型自身知识打分(更快但可能漏掉最新论文)。要严格核验就对选中的候选单独跑 /novelty-check
/hypothesis-batch "LLM beliefs" — novelty-web: false
