# Mechanist — 用户指南

**此文档涵盖进阶用法——`/mguide` 背后的命令、完整参数参考与日常使用技巧。**

---

## `/mguide` 背后的命令

`/mguide` 是入口——它判断你想做什么、准备好输入，然后分派给下面三个命令之一。你也可以直接调用它们：

| 命令 | 作用 |
|:---|:---|
| `/auto` | 自主研究流水线：claim → experiment → verify → iteration。 |
| `/msearch` | 文献检索：在 14k 篇可解释性论文语料库、157M 节点引用网络及网络资源中搜索。 |
| `/mhistory` | 领域发展史：关键论文、转折点以及思想如何演进。 |

```text
/msearch "sparse autoencoder feature absorption in large language models"
/mhistory "the evolution of circuit-level interpretability"
```

---

## `/auto`——自主流水线

`/auto` 由**两条正交参数轴**驱动，各管一个阶段：

| 参数轴 | 取值 | 用途 |
|:---|:---|:---|
| **`behavior-source`** | `given` / `given-validation` / `discovery` | 控制行为来源及是否运行 M0（现象验证）。 |
| **`mechanism`** | `given` / `discovery` | 控制由谁选择机理方法——用户指定或系统路由。 |

> 不带参数运行 `/auto` 默认等价于 `behavior-source: given, mechanism: discovery`，并读取项目根目录下的 `task.md`。

### 流水线模式

两轴正交，共 3×2=6 种组合均合法。以下为四种最常用模式：

| 模式 | 命令 | 适用场景 |
|:---|:---|:---|
| **论文复现** | `/auto — behavior-source: given, mechanism: given` | 复现一篇论文：你指定行为、机理方法、模型和数据，强制严格资源保真度。 |
| **给定行为 + 探索机理** | `/auto — behavior-source: given, mechanism: discovery` | 行为已被验证；系统探索其背后的机理。 |
| **验证行为 + 探索机理** | `/auto — behavior-source: given-validation, mechanism: discovery` | 你提出行为但希望先通过 M0 验证，再探索机理。 |
| **全自动发现** | `/auto — behavior-source: discovery, mechanism: discovery` | 全自主：流水线发现现象并路由至合适的机理方法。 |

### 各阶段产物

每个阶段都会在进入下一阶段前将本阶段相关文档写入磁盘：

| 阶段 | 关键产物 |
|:---|:---|
| **claim** | `idea-stage/IDEA_REPORT.md` — 候选 idea 排序，或从 `task.md` 捕获的行为与断言<br>`refine-logs/FINAL_PROPOSAL.md` — 精炼后的方法提案<br>`refine-logs/EXPERIMENT_PLAN.md` — 各断言里程碑、模型、数据与成功标准 |
| **experiment** | `refine-logs/MECHANISM_ROUTING.md` — 所选可解释性方法及理由<br>`refine-logs/EXPERIMENT_RESULTS.md` — 各断言结果与基线判决<br>`runs/` — 各次实验的代码、日志与 GPU 开销 |
| **verify** | `verify/VERIFY_REPORT.md` — 鲁棒性判决与跨断言摘要<br>`verify/INTEGRITY_AUDIT.md` — 对原始结果与 swap 跑的诚实性审计 |
| **iteration** | `review-stage/AUTO_REVIEW.md` — 逐轮审稿记录<br>`review-stage/AUTO_ITERATION_FINAL_REPORT.md` — 修复循环中各断言的变化 |

> [!NOTE]
> **查看最终结果：**`/auto` 每轮结束后，优先阅读项目根目录的 `CLAIMS_LEDGER.md`（各断言记分板）与 `AUTO_PIPELINE_REPORT.md`（本轮旅程、产物索引与 Open Items）。

---

## 编写 task.md

`task.md` 是每个项目目录下的**任务说明书**。正文为自由格式自然语言，无固定 schema。`/mguide` 会替你写好它；当你想完全掌控内容、或打算直接调用 `/auto` 时，再手写这个文件。

**你可以让 Mechanist 做的事：**

| 任务类型 | 思路 |
|:---|:---|
| **探索机理** | 已知模型行为——找出哪个内部组件导致了它。 |
| **复现论文** | 发现与方法均已知——按既定规模忠实复现。 |
| **验证可疑现象** | 已有具体假设，但尚无论文或先前实验确认。 |
| **开放式发现** | 只有研究方向——先让 Mechanist 挖出现象，再深入调查。 |

**`task.md` 应包含的内容：**

| 内容 | 何时必需 | 说明 |
|:---|:---|:---|
| **behavior** | `behavior-source: given` / `given-validation` | 提供一个具体、可证伪的现象。 |
| **topic** | `behavior-source: discovery` | 提供一个想研究的大方向，细节由 Mechanist 自己挖掘。 |
| **family** | `mechanism: given` | 提供一个具体机理方法（如 Fisher information / steering vectors）。 |
| **model / data** | 推荐 | 实验用的模型与数据（写清路径）。复现模式下必填。 |
| **claim 列表 / goal** | 可选 | 你希望验证的若干条断言以及本轮目标。 |

### 声明计算资源

在 `task.md` 中用自然语言写明 GPU 预算和卡数：

```text
你有 8 小时的 GPU 预算，在 GPU 用时达到预算前，不要以预算为理由暂停或简化实验。
你同时最多只能占用 8 张 GPU 中的 4 张。
```

- **充足的预算会增大智能体的实验能力**——它在告诉智能体"别为省成本而简化或放弃实验"，而不仅是上限。
- 也可以把资源分配到具体阶段（如"主实验最多用 4 张卡，verify 变体最多 2 张"）。
- GPU 预算属于**硬约束**：Agent 会将每次实验控制在预算内再启动，预算真的不够时会停下并上报。

### 声明硬约束

在 `task.md` 中用自然语言声明不可妥协的要求。编排器会自动分类并将每条约束分发到相关阶段。

```text
所有实验必须严格使用 Llama-3-8B。不要用 Pythia 2.8B。
验证 claim 3 时只用 Pythia 1B 和 410M，暂时不要跑 2.8B。
```

智能体将硬约束视为红线。如果确实无法在约束下完成，会停下并上报，而非擅自突破。

### 进展通知

在 `task.md` 中用自然语言表达通知意图：

```text
当实验取得进展时，向我的邮箱 example@gmail.com 发送通知，每小时同步一次。
```

启用后，流水线会在关键触点（实验完成 / verify 完成 / 全部结束 / halt / 需要人工介入）自动推送简报，并按小时同步进展。不写通知意图时，通知功能完全静默。

> [!NOTE]
> 你需要自行配置通知渠道。Mechanist 只扫描本地已配好的通知渠道并调用发送，不负责安装或推荐任何具体通知工具。

---

## 多轮研究

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

## `/auto` 参数

`/auto` 的所有参数均写在命令尾部：以 ` — `（破折号，`--` 亦可）起头，后接 `key: value`，多个用逗号分隔。

```bash
/auto "direction" — auto-proceed: false                    # 每个 gate 暂停等待用户批准
/auto "direction" — GPU_ID=4                               # 指定 GPU
/auto "direction" — claim-model: opus, verify-model: sonnet # 按阶段单独指定模型
/auto "direction" — dimensions: method,dataset             # verify 鲁棒性维度
/auto "direction" — review-loop: false                     # verify 后停止，跳过迭代
```

---

## 设置文献目录

在项目目录下创建 `literature/` 文件夹，放入必读 PDF——文献综述阶段每轮都会扫描。这是**只读的用户精选通道**，流水线从不修改或删除这些文件。同名论文以 `literature/` 中的版本为准。

```bash
mkdir -p literature
cp ~/Downloads/*.pdf literature/    # 后续所有 /auto 运行都会包含这些文献
```

---

## 批量假设生成

为某 topic 批量生成 behavior + mechanism 假设，结果累积进 `hypothesis_library.json`，含新颖度评分与 LLM 语义去重。

```bash
# 同时发现行为和机理（默认）
/hypothesis-batch "LLM beliefs"

# 固定 behavior，只搜索机理——behavior 可为自由文本或节点 ID
/hypothesis-batch "LLM beliefs" — behavior: "模型在多轮对话中倾向维持首轮立场"
/hypothesis-batch "LLM beliefs" — behavior: B3

# 控制规模
/hypothesis-batch "LLM beliefs" — n-behaviors: 12         # 每轮新增 behavior 数（仅 discover 模式）
/hypothesis-batch "LLM beliefs" — rounds: 5               # 连续多轮；挖尽自动提前停止

# 控制每轮有多少条是"不看策略清单"先生成的
/hypothesis-batch "LLM beliefs" — cold-n: 4               # 每轮中在看到 discovery-strategy 分类法之前就生成的条数
                                                          # （默认 n-behaviors / 5）。池子总塌缩到同一个句式时调高；
                                                          # 设 0 关闭 cold pass（不建议）。

# 速度/精度取舍
/hypothesis-batch "LLM beliefs" — novelty-web: false      # 跳过 web 检索，仅靠模型知识打分（更快，可能漏掉最新论文）
```

每条假设获新颖度评分作为粗筛。要严格验证，对选中候选单独跑 `/novelty-check`。

---

## 实验隔离

当对同一实验重复运行多次时（如 `exp1`、`exp2`、`exp3`），智能体可能会无意中读取历史运行的产物，污染当前运行。

以下提供两种机制控制智能体的文件访问范围，可任选其一或同时使用。

### 方案一：Prompt 软约束

在 `task.md` 中添加禁令：

```text
禁止读取其它实验目录，禁止借鉴既往实验的数据、方案、组别设计等信息。
```

编排器会在派发每个子 Agent 时显式注入该指令。这是提示词层面的约束，依赖模型遵循指令。

### 方案二：配置文件硬约束

在当前实验目录下放置 `.claude/settings.local.json`，在文件系统权限层面拒绝读取所有历史运行目录。

放置位置（假设本轮实验目录是 `exp/`）：

```
<project-dir>/
└── exp/
    └── .claude/
        └── settings.local.json     ← 只对从 exp/ 启动的会话生效
```

示例：

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

使用要点：

- 路径必须是**绝对路径**并以 `/**` 结尾，才能匹配目录下的全部文件。
- 每新增一轮实验，就在新目录里放一份新的 `settings.local.json`，把所有历史实验目录都追加到 `deny` 里。
- 该文件只对在此目录下启动的 Claude Code 会话生效，不会影响其它项目。

> [!WARNING]
> 这只是软偏好，不是硬边界。智能体仍可通过 `Bash(cat ...)`、`Bash(head ...)`、`Grep`、`Glob` 等方式间接读到内容。但一般来说禁掉 Read 够用了。