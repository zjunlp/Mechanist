# `/auto` 全自动流程总览

本文档介绍 `/data/wmr/MECHANICA` 的 `/auto` 自动化流程（autopipeline）。它的目标是**挖掘大模型智能与行为背后的机理**——从一个研究方向出发，自动走完"提出可验证 claim → 跑实验（含机理路由）→ 鲁棒性验证 → 审稿迭代"全链路，默认无需人工介入。

全文分两部分：**第一部分**给出整体结构 + 各阶段使用的模型；**第二部分起**逐阶段详解。

---

## 一、整体结构

### 1.1 编排器 + 四个串行阶段

入口是 `skills/auto/SKILL.md`，它是 **orchestrator（编排器）**，本身只做**调度**——把每个阶段丢进一个**独立的 sub-agent**（独立上下文窗口、可单独配模型）。orchestrator 自己不跑科研逻辑，只看每个 agent 的最终摘要 + 落盘文件，据此触发阶段之间的 **Gate（闸门）**、维护全局账本、写最终报告。

四个串行阶段：

```
/auto (orchestrator)
   │
   ├─ ① claim       想法发现：检索 → 生成/抽取 claim → novelty/impact 评估 → 精炼方案 + 实验计划
   │       └─🚦 Claim Gate
   │
   ├─ ② experiment  机理路由 + 写代码 + 跨模型 review + sanity + 部署 + 收结果
   │       └─🚦 Experiment Gate
   │
   ├─ ③ verify      沿 method/dataset/model 三轴做 swap 变体，算 robustness，双重完整性审计
   │       └─🚦 Verify Gate
   │
   └─ ④ iteration   外部 LLM 审稿 → 路由修复 → 重跑 → 再审，至多 6 轮（REVIEW_LOOP=false 时跳过）
```

每个阶段的执行逻辑都写在各自的 skill 里（单一真相源），`agents/<name>.md` 只是把 orchestrator 的参数翻成 flag 的瘦适配器：

| 阶段 | Agent 文件 | 内部主 skill | 关键产物 |
|---|---|---|---|
| **claim** | `agents/claim.md` | `/auto-claim` | `idea-stage/IDEA_REPORT.md`、`refine-logs/FINAL_PROPOSAL.md`、`refine-logs/EXPERIMENT_PLAN.md` |
| **experiment** | `agents/experiment.md` | `/auto-experiment` | `refine-logs/MECHANISM_ROUTING.md`(committed:true)、`EXPERIMENT_RESULTS.md`、`EXPERIMENT_TRACKER.md` |
| **verify** | `agents/verify.md` | `/auto-verify` | `verify/VERIFY_REPORT.md`、`verify/INTEGRITY_AUDIT.md`、每 claim 一份 `ROBUSTNESS.md` |
| **iteration** | `agents/iteration.md` | `/auto-iteration-loop` | `review-stage/AUTO_REVIEW.md`、`REVIEW_STATE.json`、`REVIEWER_MEMORY.md`、`AUTO_ITERATION_FINAL_REPORT.md` |

### 1.2 各阶段使用的模型

这里要分清**三层**模型，别混在一起：

| 层 | 角色 | 模型 | 配置位置 |
|---|---|---|---|
| **Orchestrator** | 主会话，调度 + 触发 Gate + 写报告 | **当前主会话模型**（现为 Opus 4.7 `claude-opus-4-7`） | 跟随 Claude Code 会话主模型，不受 `/auto` 任何 flag 控制 |
| **claim / experiment / iteration** | 阶段执行 sub-agent | **Opus 4.7** `claude-opus-4-7` | `agents/<name>.md` frontmatter `model:` 行 |
| **verify** | 阶段执行 sub-agent | **Sonnet 4.6** `claude-sonnet-4-6` | `agents/verify.md` frontmatter（大量并行变体跑，用更省的 Sonnet） |
| **llm-chat 陪审模型** | 跨模型 code-review / novelty 交叉验证 / 审稿（阶段**内部**辅助） | **gpt-5.4**（故意用非 Claude 模型，避免与 host 同质化） | `.claude-plugin/plugin.json` 的 `llm_model` 默认值 / `LLM_MODEL` 环境变量 |

几个要点：

- **版本 pin 的唯一真相源是 `agents/<name>.md` frontmatter**。要改某阶段固定使用的具体版本号（如 `claude-opus-4-7` → 别的），直接编辑那个 agent 文件，git 全程跟踪。
- **CLI 只能传家族别名**：`opus` / `sonnet` / `haiku`（大小写不敏感），通过 `MODEL`（全局）或 `<STAGE>_MODEL`（按阶段，如 `verify-model: opus`）覆盖。**不接受**带版本号的 pin——Agent 工具的 `model` 参数 schema 只允许别名。
- **模型解析优先级**（每阶段独立判断）：① CLI 的 `<STAGE>_MODEL` → ② CLI 的全局 `MODEL` → ③ 都没有就用 agent frontmatter 的 pin。
- **orchestrator 不继承 `MODEL` / `<STAGE>_MODEL`**——那些只作用于被派发的 4 个阶段 agent；orchestrator 跑在你的主会话模型上，要换它只能在会话层切主模型（`/model` / `/fast`）。
- **gpt-5.4 不是任何阶段的执行模型**，只是阶段内部的"外部评审助手"（写 code review、做 novelty 交叉验证、做审稿打分），不跑实验、不产出 claim/verdict。`CODE_REVIEW=false` 可关掉它在 experiment/verify 里的介入。改它的模型：编辑 `plugin.json` 的 `llm_model` 或设 `LLM_MODEL` 环境变量，**严禁在 SKILL.md 里 hardcode 模型名**（pre-flight 检查会硬失败）。

### 1.3 贯穿全程的横向设计

- **`AUTO_PROCEED` 二元化**（默认 `true`）：`true` 则所有 Gate 都不弹 UI，直接取 recommended 选项全自动跑；`false` 则在每个 Gate 调 `AskUserQuestion` **无限阻塞**等人。**没有"超时回退"的第三态**——二者互斥。少数数据保护型闸门（多轮守卫、Given-Behavior 理解闸门）**无视 `AUTO_PROCEED`**，永远等用户。
- **`RESUME`**（默认 `false`）：`true` 时每阶段先看产物是否齐全且非空，齐全就跳过 agent 调用直接走 Gate，并把 `resume: true` 下传让 skill 内部做 phase 级跳过。crash 后续跑用。`RESUME=false` 永远从头跑、覆盖旧产物。
- **`REVIEW_LOOP`**（默认 `true`）：`false` 时停在 verify，不跑 iteration。
- **Fail-loudly / 干净停**：claim 出不来 idea、routing 没候选、verify 没目标 claim 等会写 `AUTO_PIPELINE_REPORT.md` 标 `halted-at-<stage>`；可修复的停顿（plan 冲突、欠功率、全完整性破损且 `REVIEW_LOOP=false`）写成 **Round-End Decision**（`ended-needs-decision`），附 detail + remedy；现象未成立（M0）写成 `ended-phenomenon-not-established` 当合法负结果。
- **Claim Ledger（全局账本）**：orchestrator 是唯一写手，每个阶段结束后从该阶段落盘文件里抽 per-claim 字段，增量合并进 `claims_ledger.json`，再渲染出人读的 `CLAIMS_LEDGER.md`。一份文件就能看到每条 claim 的"陈述 / 数据 / 模型 / 方法 / 主实验结果 / verify verdict / iteration 是否被收窄或证伪 / 最终状态"。
- **跨轮全局记忆**：`research_memory.json` 记录历轮探索过的 behavior 与 mechanism 结论，下一轮 claim 阶段会避开已定论的工作（除非 `task.md` 显式 pin 并带 `retry-settled`）。
- **硬约束注入（task.md → 每个 subagent）**：与「输出语言」同构的横向规则。派发任何阶段 agent 前，orchestrator 把 `task.md` 里用户写明的**不可协商的运行约束**（GPU 卡数上限、最大并发、算力预算、必用/禁用的 model/dataset、环境规则）**逐字抽成 `## HARD CONSTRAINTS` 块，注入每个 agent 派发 prompt 的头部**（每阶段、每 resume 都重注）；agent 须在发车前把 dispatch 裁到 cap 以内，禁止「先超配再释放」，挡路则停下上报。规则写在 `skills/auto/SKILL.md` 的 Key Rules「Hard constraints」条。
- **进展通知（opt-in，`task.md` 声明才启用）**：`task.md` 里写了要通知（如「用邮件提醒」）时，orchestrator 在**每小时节奏** + **进展 / 结束 / 阻滞 / 需人工审批**事件调 `/notify`。该 skill 起草一份固定格式简报（实验进展 / 实验方案 / 在执行的任务 / 后续规划 / 阻滞·需人工审批），存进根目录 `notification/`（永不覆写、`/next-round` 不归档），并通过用户已配置的通知服务发出（渠道无关，不指定或推荐任何具体工具）。未 opt-in 时全部静默 no-op，绝不阻塞。
- **拒绝-改派纪律 + 角色红线**：编排器 reject 一个 stage 成果后要它重做时，磁盘 `EXPERIMENT_PLAN.md` 是唯一权威约束，改派 = 先更新 `EXPERIMENT_PLAN.md`，终止旧的 Subagent，再创建新的 Subagent 重跑；新 Subagent 不采信被拒那次的遗留文档、直接覆写，编排器永不执行 stage 逻辑、永不接管。**详见 [§1.5](#15-拒绝-改派纪律角色边界与文档所有权)**。

### 1.4 端到端数据流（产物如何在阶段间传递）

```
task.md / $ARGUMENTS
       │
       ▼
  ① claim ──► IDEA_REPORT.md + FINAL_PROPOSAL.md + EXPERIMENT_PLAN.md
       │            （EXPERIMENT_PLAN.md 里每个 milestone 含 data + model + 成功标准）
       │       [Ledger 播种 planned 值] ──🚦 Claim Gate
       ▼
  ② experiment ──► MECHANISM_ROUTING.md(committed) + EXPERIMENT_RESULTS.md + EXPERIMENT_TRACKER.md
       │            （填回 actual used_n / 主实验 verdict）
       │       [Ledger 填 actual + 主实验] ──🚦 Experiment Gate
       ▼
  ③ verify ──► VERIFY_REPORT.md + INTEGRITY_AUDIT.md + 每 claim ROBUSTNESS.md
       │            （沿 method/dataset/model swap，算 robustness，判 PASS/FAIL/INCONCLUSIVE/ZERO_ELIGIBLE）
       │       [Ledger 填 verify verdict] ──🚦 Verify Gate
       ▼
  ④ iteration ──► AUTO_REVIEW.md + REVIEW_STATE.json + AUTO_ITERATION_FINAL_REPORT.md
                    （外部审稿打分 → 路由修复 → 重跑 → 再审，收窄/证伪 claim）
                [Ledger 覆盖 final_status + 末轮触发 paper-figure]
```

### 1.5 拒绝-改派纪律、角色边界与文档所有权

上面的数据流是「顺流」。但编排器**拒绝**一个 stage 成果、要它带着修正后的要求**重做**该 stage，是一条容易出问题的回边。可能会出现的问题：**约束冲突**（重做要求与原任务打架）、**角色越界**（沟通无效时编排器亲自接管实验）、**文档悬空**（改派/接管后没人维护文档，留下脏数据）。这一节的纪律把三者一起堵住。纪律规则主要定义在 `skills/auto/SKILL.md` 的 Key Rules，本节是导读。

**核心原则**：**磁盘 `EXPERIMENT_PLAN.md` 是唯一权威约束；改派 = 先更新权威产物，kill 原有的 Subagent，再启动全新的 Subagent 重跑该 stage；改派失败即 Round-End，编排器绝不接管。**

**改派决策：谁改 `EXPERIMENT_PLAN` 由「冲突发生在哪个阶段」决定**——`claim agent` 随时可改（它是 owner）、`iteration agent` 可就地改 plan 的故障 step（受控的局部改），而 **`experiment` / `verify` 一律不能改 plan、编排器也从不碰**。按冲突所在阶段路由：

| 冲突发生阶段 | 谁改 `EXPERIMENT_PLAN` | 改法 + 重跑 |
|---|---|---|
| **claim**（Claim Gate） | **claim agent** | switch/re-run 整份重写；experiment 还没跑，无下游可 supersede |
| **experiment**（Gate / 中途 / 结果被拒，如欠功率） | **不需改**，或 **claim agent**（experiment 禁改、iteration 未起） | 只是**没跑到位** → 不改 plan，fresh experiment 按同一 plan 补跑；**真需改 plan**（微调或改 intent）→ 退回 **claim 重入**改写，再 fresh experiment |
| **verify**（Verify Gate） | **没人**（verify 只跑 swap、不改 plan） | 主实验/plan 有问题则**下沉 iteration**：`verify-inconclusive` → iteration 就地改 plan-step，或 claim 重入 |
| **iteration** | **iteration agent**（局部改）/ **claim agent**（claim 重入） | iteration 就地改 plan 的故障 step + 重跑（in-loop 或重派 `/auto-experiment`）；claim 重入经 handoff 由 claim agent 整份重规划、走全链 |

> **两个正交轴别混**：「谁**有权**改 plan」由**阶段**定（claim 随时 / iteration 受控局部 / experiment·verify 禁改）；「**要不要**改、改多大」由**变更类型**定（照跑不动 plan / 局部微调 / 改 intent 整份重写）——后者决定改法，却改不了"谁有权动手"。有界重试 ≤ **2** 次，仍无合规结果 → **Round-End Decision**，绝不接管。

**四个阶段被拒时各自怎么走（同一纪律的四种实例）。** 通用动作固定为——**编排器判定拒绝 → 先更新权威 `EXPERIMENT_PLAN.md`（由该阶段允许的编辑者改，编排器从不手改）→ 终止旧 subagent → 起一个全新的 subagent（新上下文 + `RESUME` 读盘）重跑；新 subagent 只认更新后的权威 plan，不采信被拒那次留下的其它遗留产物（`EXPERIMENT_RESULTS.md`、变体脚本等），直接覆写重来**。四阶段的差别只在「谁改 plan、要不要改、起哪个新 subagent」：

- **① claim 被拒（Claim Gate）** —— claim agent 是 plan 的 owner，编排器直接**起新的 claim subagent** 换 idea / 整份重写，产出新 `EXPERIMENT_PLAN.md` 回到 Claim Gate。此时 experiment 还没跑，**没有下游遗留产物要覆写 / supersede**，最干净。

- **② experiment 被拒（Gate / 中途 / 结果被拒，如欠功率）** —— experiment **禁改 plan**，按「要不要改 plan」分两支：
  - **只是没跑到位**（grid/seed 没跑全，plan 本身没错）→ **不改 plan**，起**新的 experiment subagent 按同一 plan 补跑**（就是「在原有基础上继续跑」）。
  - **plan 真需改**（微调或改 intent）→ 编排器**先起 claim subagent 改 `EXPERIMENT_PLAN.md`** → 再起**新的 experiment subagent** 按更新后的 plan fresh 重跑。

- **③ verify 被拒（Verify Gate）** —— verify **只跑 swap、不改 plan**，所以 Verify Gate 处**不直接起 claim 改 plan**，而是把问题**下沉 iteration**，由 verify 四态触发对应回边：
  - **变体自身跑坏**（脚本 bug / `ZERO_ELIGIBLE_VARIANTS`）→ iteration **① 修变体脚本**再重派 `/auto-verify`。
  - **主实验 / plan 有问题**（`INCONCLUSIVE`）→ iteration **② 就地改 plan 故障 step**，或 **③ claim 重入**。
  - （`no-target` / `scorer-invalid` 这类不进 iteration，直接 **Round-End Decision** 回问用户。）

- **④ iteration 被拒 / 需上游** —— iteration agent **可就地改 plan 的故障 step**（这是它被授权的活）：
  - **局部**：iteration 自己改 `EXPERIMENT_PLAN.md` 故障 step + 重跑（in-loop 或重派 `/auto-experiment`）→ 重 verify，**不惊动编排器**。
  - **全路径（claim 重入）**：需整份重规划 → iteration 设 `awaiting_upstream` **交回编排器** → 编排器起 **claim subagent 整份重规划** → 依次 experiment / verify → `resume` 回 iteration，预算不重置。

> **一句话对照**：能不能自己改 plan——**claim = 随时、iteration = 只故障 step、experiment · verify = 一律不能**；改 plan 的永远是子 agent、编排器从不手改；重跑一律**新起** subagent（非老 agent 续聊）。越靠下游，「改派」越倾向**就地 / 下沉**；越靠上游，越倾向**整份重规划**。

每次改派都要求子 agent **supersede**（就地重写并标注取代）被拒结果的叙事，而非在旁边并列追加互相矛盾的新段。

**角色红线（硬）**：编排器合法动作只有四种——dispatch agent、fire gate、read files、write ledger。它**永不**亲自跑实验、**永不**写 stage 产物（`EXPERIMENT_RESULTS.md`/`EXPERIMENT_TRACKER.md`/变体脚本…）、**永不**代子 agent 执行 skill。"do not synthesize a fallback" 覆盖的是"agent 不肯产出"，而不只是"文件缺失"——跑不出来就 Round-End，不是接管。

**文档所有权 + supersede**：每份 stage 文档归**产出它的 skill**（格式由该 skill 定义、只由子 agent 执行）；编排器只**派生账本**、不写任何 stage 文档。一次改派**重跑该 skill**，由 skill 就地 supersede 旧叙事——因此"新旧叙事并存"的脏数据、和"编排器接管后文档无人写"的悬空，两个来源同时消失（后者靠上面的红线禁掉接管而根除）。

**子 agent 侧兜底**：四个 agent 各有一节「Constraint precedence」——若派发 prose 与磁盘 `EXPERIMENT_PLAN.md`（claim agent 则为 `task.md`）冲突，**以磁盘产物为权威并在 return 里报冲突**，不私自二选一、也不停在原地纠结。

**用户手动改派（最高优先入口）**：用户请求是**最高权威**——覆盖 `task.md` pin 与 plan 的"保护"（用户被授权改 scientific intent），即便全自动也**立即被尊重**，且**不弹 Round-End 让用户去做他刚要求的事**。无论是口头发给编排器、在 gate 上、还是自己改文件，编排器的角色都是**判断 + 路由，绝不亲手改 plan、绝不热通知运行中的 subagent**：（1）据**要求强度 × subagent 状态**选"立即打断当前 subagent（停 agent 属调度、不破红线）"还是"推到下一个边界"；（2）**委托该阶段允许的编辑者改写**（按上表阶段轴，非按变更类型）——在 experiment 中途/之前，唯一编辑者是 **claim agent**（claim 重入：改 intent 整份重写、同 intent 微调则 scoped 改一处）；进了 iteration 阶段，同 intent 微调才可由 **iteration agent** 就地改一处 plan-step。**编排器绝不手改 `EXPERIMENT_PLAN.md`**（它的机器标记只有 claim skill 能改得合法）；（3）**fresh 重派**指向更新后的 plan（不给运行中的 agent 热切 plan——那会造成三方冲突），旧叙事标 `superseded: per user request`。用户若自己编辑 `EXPERIMENT_PLAN.md`/`task.md` 再 `resume`，也是既有的合法路径。

> **谁改 plan、是否新起 subagent**（两个入口通用，按上表的阶段轴）：**改 plan 的一定是跑 skill 的 subagent，永不是编排器**——`claim agent` 随时可改（owner）、`iteration agent` 只在 iteration 阶段可就地改 plan 的故障 step，`experiment` / `verify` **禁改**。所以同一个"同 intent 微调"，落在 **experiment 中途**只能走 **claim 重入**、落在 **iteration** 里才由 **iteration agent** 就地改——**编辑者由阶段定，不由变更类型定**。**再调用一律是 fresh subagent（新上下文）+ RESUME 读盘**，不是老 subagent 原地续聊；是否新起 experiment 阶段则看重跑发生在哪：experiment 中途/用户改派 → 新起 experiment；iteration 里就地改 step 的那类 → 常 in-loop 重跑、不新起；claim 重入/改 intent → 起一整条新的 claim→experiment→verify 链。

---

## 二、claim 阶段详解（想法发现）

> 顶层结构三层：**调度前置闸门（orchestrator）→ `/auto-claim` 内部 Phases → 调度后置 Claim Gate**。真正的 phase 逻辑全在 `skills/auto-claim/SKILL.md`。

### 2.1 两条正交参数轴：BEHAVIOR_SOURCE × MECHANISM（贯穿全程的分叉）

`/auto` 由两条**正交**的参数轴驱动，各管一个阶段（旧的 `MODE` 已移除；旧 `mode: reproduction` ≡ `behavior-source: given, mechanism: given`）。两轴在命令行传入：`/auto — behavior-source: <X>, mechanism: <Y>`；裸跑 `/auto`（不带参数）等价于 `given` + `discovery`。

#### 两条轴的取值（合并对比）

`BEHAVIOR_SOURCE` 管 behavior 阶段（行为来源 / 是否 ideation / 是否 M0），`MECHANISM` 管 mechanism 阶段（谁选机理方法）。下表把两轴的全部取值放在一起对比：

| 轴（默认） | 取值 | 该阶段做什么（关键差异） | M0 / 路由 | 适用场景 |
|---|---|---|---|---|
| **BEHAVIOR_SOURCE**（默认 `given`） | **`given`** | 行为从 `task.md` / direction 取定、**视作成立**；无 ideation / novelty | **无 M0**，直接进机理 | 现象已被前人验证，省掉验证开销 |
| | **`given-validation`** | 同样取定行为（不挖掘、无 ideation / novelty） | **以 M0 现象验证闸门开头** | 给了候选行为但不确定成立，想先验证 |
| | **`discovery`** | `/mechanism-behavior-discovery` 挖**新现象** + 完整 ideation（novelty + impact 优先排名） | **以 M0 开头** | 只有 topic，让 pipeline 找值得做的新现象 |
| **MECHANISM**（默认 `discovery`） | **`discovery`** | 系统路由：claim 载 `/mechanism-explore` 塑造方向 | experiment 用 `/mechanism-skills` 选 family（auto-select / mini-prompt） | 不指定方法，让系统挑最合适的 |
| | **`given`** | 用户指定：捕获并盖 `chosen_mechanism:`（命名方法 **或** behavioral-only） | experiment 直接 commit 为 `CHOSEN_FAMILY`（Phase 1.5 Mode B，不路由、不弹 mini-prompt） | 复现某论文方法 / 已定方法 |

> **M0 四态判定**（仅 `given-validation` / `discovery`）：established / conditional / not-established / inconclusive；`given` 无 M0。`discovery` 锐化新现象按 Real / Non-obvious / Specific / Robust / Tractable 五条标准，再跑 idea-creator → novelty → impact → review。给定的 behavior 须"具体可证伪"，否则 Given-Behavior 理解闸门会拦下来问你（见 §2.2）。

#### 六种组合（3×2 全合法）

行 = `behavior-source`（管 M0 / ideation），列 = `mechanism`（管谁选方法），格子即组合含义。✅ = README 四种规范写法。

| behavior-source ↓ ＼ mechanism → | **`given`** 用户指定方法 | **`discovery`** 系统路由 |
|---|---|---|
| **`given`** 无 M0、无 ideation | ✅ 复现论文（唯一 **strict** 禁降配） | ✅ 现象默认成立，系统探机理 |
| **`given-validation`** 先 M0 验证 | 先验证现象，用指定方法 | ✅ 先验证现象，系统探机理 |
| **`discovery`** 挖新现象+M0+ideation | 挖新现象，用指定方法 | ✅ 全自动：挖现象+系统探机理 |

除左上角 `given`+`given` 盖 `resource_fidelity: strict`（禁降配、忽略 `CHOSEN_IDEA`）外，其余 5 格均 cost-aware（受 `UNDERPOWER` 欠功率门保护）。

### 2.2 orchestrator → claim agent（含两个前置闸门）

direction 解析：`$ARGUMENTS` 非空 → 当 direction，`task.md` 作详细补充；`$ARGUMENTS` 空 + `task.md` 在 → 只用 `task.md`，传 `direction: ""`；都没有 → 停掉报错，**不允许 agent 自己编 direction**。

派发 agent **之前**，orchestrator 还有两个闸门：

1. **Settled-pin 冲突闸门**（**尊重 `AUTO_PROCEED`**）：orchestrator 同时持有 `task.md` 和 `research_memory.json`，检查 `task.md` 里 pin 的 behavior/direction/family 是否已在往轮定论。命中时按 `retry-settled` 标记解析成 `honor-pin`（用户授权重做）或 `pick-fresh`（换没试过的），作为 `pin_resolution:` 注入。`AUTO_PROCEED=true` 无 retry 标记时**静默** pick-fresh；`false` 则 `AskUserQuestion` 阻塞。
2. **Given-Behavior 理解闸门**（仅 `given` / `given-validation`，**无视 `AUTO_PROCEED` 必等用户**）：检查取定行为是否真"具体可证伪"。若只是空泛主题 → 强制 `AskUserQuestion`（切到 `discovery` / 让用户补具体 behavior），防止 claim 阶段凭空捏一个未经 M0 验证的现象。

### 2.3 `/auto-claim` 内部 Phases

| Phase | 模式 | 内容 | 主产物 |
|---|---|---|---|
| **0** | all | 加载研究简报 / 定方向源 | — |
| **0.5** | all | `REF_PAPER` 给定时总结参考论文 | `REF_PAPER_SUMMARY.md` |
| **1** | all | **文献检索** `/research-lit` → 合成景观 | `RESEARCH_LIT.md`(raw) + `LANDSCAPE.md`(合成) |
| **1.75** | all | **机理策略加载 + 捕获**（纯 context，无产物）：behavior 轴—`discovery`→`/mechanism-behavior-discovery`，`given`/`given-validation`→ 不挖掘；mechanism 轴—`discovery`→`/mechanism-explore`，`given`→ 捕获用户 `chosen_mechanism` | 无 |
| **2** | all | 产出待验证 claim。`discovery`：`/idea-creator` 头脑风暴 8–12 → 可行性/算力/快速 novelty 过滤 → top idea 深度验证 + 跑 pilot → 按经验信号排名。`given`/`given-validation`：从 `task.md` 忠实捕获 behavior/claim + 资源（reproduction 组合下为 binding） | `IDEA_REPORT.md` |
| **3** | `discovery` only | **深度新颖性验证** `/novelty-check`（多源检索 + 并发工作检查），淘汰已发表 | 更新 `IDEA_REPORT.md` |
| **3.5** | `discovery` only | **深度影响力验证** `/impact-check`，按 **impact 优先、novelty 次之**重排 | 更新排名 |
| **4** | `discovery` only | **外部严苛评审** `/research-review`（资深 reviewer 视角打分挑刺） | 更新 `IDEA_REPORT.md` |
| **4.5** | all | **方案精炼 + 实验规划**（见 2.6）。`discovery` 按 `CHOSEN_IDEA` 选 idea / `given`·`given-validation` 合并全部 claim | **`FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md` + `EXPERIMENT_TRACKER.md`** |
| **5** | all | 汇总最终报告 | 定稿 `IDEA_REPORT.md` |

> ⚠️ 两个易混点：(1) **pilot 实验在 Phase 2 内部（`/idea-creator`）跑**，不是单独一个 phase；Phase 3 是对存活 top idea 再做一次更深的专门 novelty 检查。(2) `/idea-creator` 有自己的**内部** Phase 编号（1-5），与 `/auto-claim` 顶层 phase 不是一回事。

`IDEA_REPORT.md` 是 Phase 1–3.5 的同一份 downstream deliverable——Phase 2 写初版、Phase 3 回填 novelty、Phase 3.5 回填 impact 并重排。

### 2.4 检索 → 新 claim：物料怎么进来

**Phase 1 `/research-lit`** 是检索那一步，7 路数据源（按优先级）：Zotero(MCP) → Obsidian(MCP) → 本地 PDF(`papers/`,`literature/`) → WebSearch(arXiv/Scholar/S2) → arXiv API → Semantic Scholar → DeepXiv → Exa。默认 `sources: all` ≈ Zotero+Obsidian+本地+WebSearch+arXiv；S2/DeepXiv/Exa 须显式列出。Zotero 批注被视作"金子"（代表用户自己觉得重要）。

跨源去重（arXiv ID → DOI → 标题归一化）后写两份文件（均无条件 overwrite，**都不参与 resume gating**）：

- **`RESEARCH_LIT.md`** —— raw 检索 dump，每篇一条记录（含 abstract 全文等），经 rerank 但不改写，**纯审计**，下游不读。
- **`LANDSCAPE.md`** —— 合成结果：结构化 paper 表 + 3-5 段叙事 + structural gaps。**Phase 2 `/idea-creator` 会 `Read` 它**进上下文据此生成 idea——它是 `/research-lit → /idea-creator` 之间的**正式 inter-phase data carrier**（从磁盘读，比依赖会话上下文鲁棒，抗长会话压缩 + crash-resume）。

**这张 landscape 表 + gaps 就是喂给下一步生成 claim 的原料。**

**Phase 2 `/idea-creator`** 把 `LANDSCAPE.md` 粘进一个 `mcp__llm-chat__chat` prompt 交给外部模型（gpt-5.4）发散生成 8–12 个 idea（每个含 hypothesis / minimum experiment / risk / effort），约束："可在 ≤8×3090 上测、正负结果都可发、不是 apply X to Y、与 landscape 有区分度"。注意 `llm-chat` **无状态**——同阶段后续追问必须把上一轮 verbatim 再贴一遍。

> ⚠️ "新 claim"是 **idea 级别**的可证伪假设（hypothesis / min experiment），不是把检索到的论文 cite 进来当 claim。检索给的是 *landscape + gaps*——起 *约束* + *启发* 作用。

### 2.5 Novelty + Impact 评估

Novelty **做两遍**，目的不同：

- **第一遍（quick）**：`/idea-creator` 内部对每个新 idea 做 2-3 次 targeted search，明显已发表直接淘汰，不写结构化报告。
- **第二遍（deep）**：`/auto-claim` Phase 3 `/novelty-check`，四阶段——A 抽 3-5 条核心技术 claim；B 对**每条** claim 多源检索（≥3 种 query、2024–2026 年限、卡顶会列表、WebFetch 抓重叠论文）；C 把方法 + 找到的论文喂外部 LLM(`llm-chat`/gpt-5.4) 强制问"novel 吗？最近的 prior work？delta 是什么？"；D 输出结构化报告回填进 `IDEA_REPORT.md`。

**Phase 3.5 `/impact-check`** 判断研究的**问题/behavior** 是否重要，输出 `Impact: X/10`。

**impact / novelty 分工（重要设计）**：**impact 看 behavior/现象**（值不值得研究），**novelty 看 mechanism/方法**（够不够新）。Phase 3.5 **按 impact 优先、novelty 破平局**重排 `## Ranked Ideas`——这就是 Phase 4.5 `CHOSEN_IDEA` 索引的对象。

几条易忽视规则：**"Apply X to Y" 默认不算 novel**（除非揭示意外见解）；**方法不 novel 但 finding novel 也算**；**必查最近 6 个月 arXiv** 堵 concurrent work；**novelty 是 claim 级**（逐条 H/M/L 再汇总）。

### 2.6 Phase 4.5 嵌套 —— data / model 在哪一步真正定下来

claim 阶段写 `EXPERIMENT_PLAN.md`（后续 verify 用的 data 与 model 来源）的真实调用链是**三层嵌套**：

```
/auto-claim Phase 4.5
   └─ /research-refine-pipeline
        ├─ Phase 1  Method Refinement → /research-refine（外部 LLM 评审迭代，≤5 轮至 score≥9）→ FINAL_PROPOSAL.md
        ├─ Phase 2  Planning Gate
        ├─ Phase 3  Experiment Planning → /experiment-plan          ★
        │      └─ /experiment-plan Phase 3「Specify Each Experiment Block」
        │            逐 block 写 Dataset/split + provenance + source + available_n + 计划 used_n
        │            + Compared systems(models) + backbone → data & model 在此确定
        │            → refine-logs/EXPERIMENT_PLAN.md
        └─ Phase 4  Integration → PIPELINE_SUMMARY.md
```

> **注意两层同名 Phase 3**：`/research-refine-pipeline` 的 Phase 3 是调度层；`/experiment-plan` 的 Phase 3 才真正逐 block 写 data/model。

`EXPERIMENT_PLAN.md` 还盖几个机器标记：`mechanism_strategy:`（`MECHANISM=discovery` 时写，记走了 `/mechanism-explore` 哪几个方向；`MECHANISM=given` 时为 `n/a`）；`chosen_mechanism:`（仅 `MECHANISM=given`，用户指定的机理方法/family，下传为 `CHOSEN_FAMILY`）；`method_sensitive: [...]`（标记值依赖机理 submethod、允许实验阶段 re-bind 不算改 plan 的字段）；`kind: phenomenon-validation`（仅 `given-validation` / `discovery` 的 M0 里程碑，M1…Mn 声明 `depends_on:[M0]`；`given` 无 M0）；`resource_fidelity: strict`（仅 reproduction 组合 `given`+`given`）。

> **data/model 生命周期**：claim Phase 4.5 写 **planned 值** → Claim Gate 后**播种进 Ledger**（`final_status="planned"`）→ experiment 阶段从 `EXPERIMENT_RESULTS.md` 填 **actual 值**（用实际 used_n 覆盖）→ verify 阶段以此为主实验基准沿 `DIMENSIONS` 做 swap。verify 不重新选 data/model，只消费。

### 2.7 🚦 Claim Gate

`AUTO_PROCEED=true`（默认）→ 不弹 UI，直接取 `IDEA_REPORT.md` top-ranked idea，进 experiment。`AUTO_PROCEED=false` → `AskUserQuestion` 四选（approve / switch `<N>` / re-run / stop）并阻塞。

最终交给 experiment 的"claim"有三层：① idea-level（`IDEA_REPORT.md` 的 hypothesis，自然语言）；② method-level（`FINAL_PROPOSAL.md`，已 anchor 过 ≤5 轮 review）；③ 可验证 claim（`EXPERIMENT_PLAN.md` 每个 milestone，含 data/model）。

---

## 三、experiment 阶段详解（机理路由 + 构建 + 部署）

> 逻辑在 `skills/auto-experiment/SKILL.md`。先分清两套"build/deploy"语义：**Mode A/B** 是 orchestrator 调用 agent 的模式（`route_only` / `build`）；**build/deploy/sanity/collect** 是 skill 内部 Phase 的口语化分组。

### 3.1 orchestrator → experiment agent

- **Resume 解析先行**：grep `MECHANISM_ROUTING.md` 的 `committed:` / `routing: not-applicable` / `chosen_family:` 三字段，按 0–4 分支 dispatch（含"现象终止"早退分支：若 `EXPERIMENT_RESULTS.md` 带 `phenomenon_status: not-established` 则整个 pipeline 已在 M0 结束，跳过 verify+iteration）。
- **Call-count 二元化**：`AUTO_PROCEED=true` 一通合并调用（agent Phase 0 自动选 recommended family）；`AUTO_PROCEED=false` 两通调用 + 中间 `AskUserQuestion` 选 family。
- **Family pin 短路**：`task.md` pin 了 `family:` 且解析为 honor-pin → 直接走 build 路径，跳过路由选择。

### 3.2 Phase 1.25（仅 `given-validation` / `discovery`）—— M0 现象验证闸门

`given-validation` / `discovery` 路径的实验计划以 M0 开头，**实验阶段第一步就跑 M0**，四态判定：
- `established` / `conditional` → 继续（`conditional` 把后续机理分析限制在成立条件内）；
- `not-established` → 🛑 **结束 pipeline**，写负结果报告，跳过 verify+iteration（合法负发现，非错误）；
- `inconclusive` → 修测试/计划后重跑 M0。

### 3.3 Phase 1.5 —— Mechanism-family routing

输入 `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md`，路由本身在 `/mechanism-skills` 做，Phase 0 只调度 + 写 manifest。`MECHANISM_ROUTING` 三模式：`auto`（默认，出 2–3 个 family/submethod 候选）/ `skip`（resume 路径假定已存在）/ `not-applicable`（行为级提案，写 stub 跳过路由）。每条候选带：family 路径、submethod、`screen → decode → verify → recover` 组合计划、成本估算、绑定到具体 claim 的 rationale。`RESEARCH_DOMAIN` 在这里作路由约束。

### 3.4 Phase 1 —— Parse plan

读 `EXPERIMENT_PLAN.md` 抽 milestone 顺序（sanity → baseline → main → ablation → polish）、每 block 的 dataset/split/超参/seed/成功标准/优先级、总 GPU-h budget。in-memory，无产物。

### 3.5 Phase 2 —— 写代码（狭义 build）

**Script 粒度规约**：**一个 model × dataset 一个 dispatch script**（不是一个 milestone 一个），便于 Phase 4 `nohup ... & wait` 干净并行。实现：argparse 暴露全部超参、固定 seed、results 落 JSON/CSV、按 CLAUDE.md 启用 wandb、`BASE_REPO` 非空先 `git clone`。Phase 0 committed 的 family/submethod 决定可参考的 `scripts/`+`references/`（**借鉴可以，逐字拷贝禁止**）。输出目录规约：`runs/<run_id>_<short_purpose>/`。

### 3.6 Phase 2.5 —— 跨模型 code review

`CODE_REVIEW=true`（默认）把代码 + plan + proposal 喂 `mcp__llm-chat__chat`（gpt-5.4），强制问 7 条，其中两条 **CRITICAL hard rule**：
- **#5 GT 来源**：评估用的是 dataset 真 GT，**不是另一个模型的输出当 GT**？
- **#6 scorer 匹配**：scorer 匹配 answer 格式吗？（MCQ→option token exact-match；short→normalized exact-match/token-F1；long→LLM-judge/substring+rubric），且跑 **label-floor check**（50–100 样本上分数方差 ≥0.05，坍缩到常数 = hard halt）。

CRITICAL 必修，最多 2 轮；llm-chat 不可用静默跳过（不阻塞）。这两条 hard rule 在 experiment Phase 2.5、verify 主实验 audit、experiment-audit 多处反复出现，是 pipeline 最看重的质量门。

### 3.7 Phase 3 —— Sanity check

`SANITY_FIRST=true`（默认）先单跑最小 sanity 实验，验证 loop 不崩 / metric 算 + 落盘 / GPU OK / 输出格式对。**最多 3 次自动 debug**：解析错误 → 分类(OOM/Import/CUDA/NaN) → 针对性修；第 2 次仍失败调 `/codex:rescue`（装了 codex plugin 的话）让外部 agent 独立看；3 次后仍失败停掉报告，**不允许带病继续**。GPU pinning：`GPU_ID` 非 `auto` 时把 `CUDA_VISIBLE_DEVICES=<GPU_ID>` 作为 **leading positional arg** 传给 `/run-experiment`。

### 3.8 Phase 4 —— Deploy（发车跑全套）

**Phase 4.0 按 milestone 大小路由**：≥10 runs / 有 `depends_on` / grid expansion / ≥3 seeds×≥3 configs → **Phase 4.B `/experiment-queue`**；≤5 ad-hoc 无依赖无 grid → **Phase 4.A `/run-experiment` 直发**；6–9 runs 建议 queue 可 direct（warning）。`BATCH_DISPATCH` 可强制 `queue`/`direct`/`auto`。

- **4.A 直发**：一个 milestone 所有并行 run **用一个 Bash call** 起，模板 `nohup ... & wait`。**禁忌：不能用 `pgrep -f '<script>.py'` 轮询**（会匹配 polling bash 自己 → 死循环，2026-05-18 挂死 5h 后写进黑名单）；fallback 轮询必须 `grep -v $$` 自排除 + 硬超时。
- **4.B 队列**：从 plan 派生 YAML grid manifest → `/experiment-queue` → 轮询 `queue_state.json` 直到 `completed`/`stuck`（**`stuck` 必须 surface**）。queue 额外能力：OOM retry（backoff 重投）/ stale cleanup / GPU 空闲门 / phase deps。
- **Multi-GPU 切分**：`GPU_ID=4,5,6,7` + `MAX_PARALLEL_RUNS=2` → run A 用 `4,5`、run B 用 `6,7`，**不允许共享同卡**（除非内存实测能塞下）；显式列表少于并行度自动 clamp。

**🚦 Experiment Gate**（`AUTO_DEPLOY` × `AUTO_PROCEED` 2×2）：只有 `AUTO_DEPLOY=false AND AUTO_PROCEED=false` 那一格才 `AskUserQuestion`（approve/narrow/abort）无超时阻塞，专为过夜跑兜底；其余三格静默 deploy。

### 3.9 Phase 5 / 5.5 / 5.6 / 6 —— 收结果 + 收尾

- **Phase 5 收结果**：解析 JSON/CSV/log 抽 key metric；wandb 配了调 `/training-check` 看 NaN/发散/plateau/overfit；写 `EXPERIMENT_RESULTS.md`（结尾 `Ready for /auto-verify: YES/NO`）。**`EXPERIMENT_TRACKER.md` 所有权属于 claim Phase 4.5**——experiment 阶段只在表上**原地翻 Status**（`pending→running→done|failed`），**禁止整张覆盖**；launch 前翻 running、单 run 返回立即翻终态（hang 检测依赖"卡在 running 超 2×ETA"信号）。
- **Phase 5.5（`COMPACT=true`）**：每个完成 run 追加结构化条目到 `EXPERIMENT_LOG.md`。
- **Phase 5.6 auto ablation**：主实验正面 → `/ablation-planner` 生成消融计划，append 到 plan + tracker；negative/inconclusive 跳过。
- **Phase 6 handoff**：打印 deploy 总结，指向 `/auto-verify`。

**🚦 Power-Fidelity Gate（cost-aware 组合，`UNDERPOWER != off`）**：cost-aware 跑常以降配规模跑，weak/negative verdict 可能是欠功率假象而非真负。对"verdict 弱 + 实跑规模显著低于 plan"的 claim 标 `suspected_under_power`：`tag`（默认）打 provisional caveat 后继续；`stop` 当 Round-End Decision 停下；`off` 不查。reproduction 组合因 `resource_fidelity: strict` 已禁降配，此门免疫。

experiment 最终给 verify 三份产物：`MECHANISM_ROUTING.md`(committed:true，verify 的 method swap 必须在同一 family 内就靠它锚定)、`EXPERIMENT_RESULTS.md`、`EXPERIMENT_TRACKER.md`。

---

## 四、verify 阶段详解（claim 鲁棒性验证）

> 逻辑在 `skills/auto-verify/SKILL.md`，共 **11 个 Phase / 3 个 Stage**。核心思路：**对每条 claim，把主实验用过的 method/dataset/model 各换一个做"变体"重跑，看结论是否还成立**——成立=鲁棒(PASS)，分歧=脆弱(FAIL)。换之前先审主实验完整性，换之后再审变体完整性。

### 4.1 目录布局

`<claim_dir>` = `<claim_id>_<short_claim>`（如 `C1_gasl_beats_baselines`，≤4 个 snake_case 词）。

```
verify/
├── VERIFY_REPORT.md          # 顶层汇总（固定名）
├── INTEGRITY_AUDIT.md        # Phase 2 主实验 + Phase 9 variant 完整性 verdict 汇总
└── <claim_dir>/
    ├── PLAN.md               # Phase 3 选的变体 + 理由
    ├── ROBUSTNESS.md         # Phase 10 per-claim verdict（始终写，是 resume 真相源）
    ├── main_experiment_audit/       # Phase 2：对 refine-logs/ 审，{EXPERIMENT,MECHANISM}_AUDIT.{md,json}
    ├── variant_audit/        # Phase 9：对 variants/ 审，同结构
    └── variants/
        ├── method-swap-<tag>/   (config.yaml, run.sh, DIFF.md, result.json, verdict.json)
        ├── dataset-swap-<tag>/
        └── model-swap-<tag>/
```

### 4.2 Stage 1（Phase 1–2）：目标选取 + 主实验完整性闸门

**Phase 1 目标选取**：
- `TARGET_CLAIMS`（默认 `all`）：`all` / `passed`（仅主实验 supported）/ `failed`（仅主实验 not-supported）/ 单 claim-id。
- `MAX_VERIFY_CLAIMS`（默认 `1`）：**Stage 1 无条件审计每条目标 claim，cap 只 gate Stage 2 入口**。Phase 3 step 0 从 Stage 1 admitted pool 里按**重要性判断**挑 top-K（读 claim 陈述 + `IDEA_REPORT.md` / `## Rationale` 等上游语境；行号不是优先级信号）。未被挑中的 admitted claim 标 `INTEGRITY_ONLY` with `stage2_skip_reason: max_verify_claims_cap`，后续可 `/auto-verify <id> — resume: true` 补跑 Stage 2（Stage 1 audit 通过 RESUME 复用）。显式单 claim 模式 trivially 挑那一个。

**Phase 2 主实验完整性审计（Stage 1 gate）**：对每条目标 claim 跑两个跨模型审计——
- `/experiment-audit`（A–F）：A. GT 是从 dataset 来还是模型输出来？B. metric 有没有被模型自己的 max/mean 归一？C. claim 引用的数字在结果文件里真存在吗？D. 评估函数定义了却没调（dead code）？E. claim 措辞（"comprehensive"）是否超出实际 scene/seed 数？F. 评估类型（real_gt / synthetic_proxy）。
- `/mechanism-audit`（A 已实现，B–F 预留）：A. steering coefficient 是否扫了 ≥3 个数量级、σ_proj 归一、有 random-direction 基线对照等（无 additive intervention 时返回 n/a）。

verdict 合并：`s = max(severity(exp), severity(mech))`（fail=3/warn=2/pass=1/n/a=0），两者皆 n/a→pass。per-claim 分支：**pass** 正常进 Phase 3–10；**warn** 进但打 `[MAIN-EXPERIMENT INTEGRITY: WARN]`；**fail** → 直接判 **INCONCLUSIVE**，跳过该 claim 的 Phase 3–10（主实验的锚都坏了，算 robustness 无意义）。

### 4.3 Stage 2（Phase 3–7）：生成 + 部署变体

- **Phase 3 step 0（新）Stage-2 挑选**：从 Phase 2 admitted pool 里按重要性判断挑 K = min(`MAX_VERIFY_CLAIMS`, |ADMITTED|) 个 claim，结果持久化到 `verify/STAGE2_PICK.json`；未被挑中的 admitted claim 直接标 `INTEGRITY_ONLY` (`stage2_skip_reason: max_verify_claims_cap`) 并跳到 Phase 11。
- **Phase 3 选变体**：仅对 picked claim 沿 `DIMENSIONS`（默认 `model`）**每轴一个 swap**，故默认 1 变体/picked-claim。**method swap 受"同 family"硬约束**——机理类 claim 的方法替换必须留在主实验的 mechanism family 内（如 `probing/residual-stream` → `probing/sae-feature`，但不能 probing → causal-attribution，那是另一个问题）；family 由 `MECHANISM_ROUTING.md` 锚定。**dataset / model swap 无 family 约束**，由 pick-alternatives 从 `IDEA_REPORT.md` + research-lit 取候选，外部 LLM 按"对 claim 最强独立检验"排序。
- **Phase 4** reviewer 批 verify 计划；**Phase 5** 实现变体（与主实验**最小 diff**）；**Phase 6** 跨模型 code review（`CODE_REVIEW=true`：只改了该 swap 吗？有无静默改超参？仍用真 GT？metric 算法同主实验？必须改超参时 主实验是否也对齐？最多 2 轮，MCP 挂静默跳过）；**Phase 7** sanity（`SANITY_FIRST=true`，复用 experiment Phase 3 的 3 次 debug 协议）后部署。

### 4.4 Stage 3（Phase 8–11）：判定 + 审计 + 聚合

- **Phase 8 `/result-to-claim`**：对每个变体判 `claim_supported: pass|fail`（无 partial，达不到无歧义支持即 fail），再确定性算 `consistent_with_main_experiment`——主实验 supported 时 `=claim_supported`；主实验 not-supported 时 `=flip(claim_supported)`（即"变体与主实验是否得出同方向结论"）。
- **Phase 9 变体完整性审计**（对称 Phase 2，审 `variants/`）：per-variant `integrity_status = max_severity(exp, mech)`。**fail 的变体从 robustness 的分子分母里都剔除**（"不知道它会说什么" ≠ "它反对"，计 0 会把 robustness 偏向 FAIL）。
- **Phase 10 算 robustness**：

  ```
  N_eligible = 完整性 ∈ {pass,warn} 的变体数
  #pass      = 其中 consistent_with_main_experiment==pass 的数
  robustness = #pass / N_eligible
  ```

  判定：`N_eligible < MIN_VARIANTS_FOR_VERDICT`（默认 1）→ **ZERO_ELIGIBLE_VARIANTS**；否则 `robustness ≥ ROBUSTNESS_THRESHOLD`（默认 0.5）→ **PASS**，否则 **FAIL**。
- **Phase 11** 写 `VERIFY_REPORT.md` + handoff。

### 4.5 五个 per-claim 终态

| 终态 | 含义 | 由谁判 | iteration 该怎么修 |
|---|---|---|---|
| **PASS** | 主实验结论在 swap 下鲁棒（`robustness ≥ 阈值`） | Phase 10 | 仅做叙事一致性检查，无需实验 |
| **FAIL** | 主实验完整但变体分歧（`robustness < 阈值`） | Phase 10 | 两阶段：先查/修变体完整性，仍 FAIL 则改/收窄 claim |
| **INCONCLUSIVE** | Phase 2 主实验完整性 FAIL，变体根本没跑 | Phase 2 | **只修主实验评估，不动 claim** |
| **ZERO_ELIGIBLE_VARIANTS** | 主实验 OK 但所有变体 Phase 9 完整性 FAIL | Phase 10 | **只修变体脚本，不动主实验 / claim** |
| **INTEGRITY_ONLY** | Stage 1 pass/warn，Stage 2 刻意跳过（`stage2_skip_reason`：`swap_variants_false` = 全局审计-only 模式；`max_verify_claims_cap` = Stage 1 admitted 但未进 top-K） | Phase 2 step 4 / Phase 3 step 0 | **无回边动作** — 记入 Open Items，按 `stage2_skip_reason` 提示补跑命令：`swap_variants_false → /auto-verify <id> — swap-variants: true, resume: true`；`max_verify_claims_cap → /auto-verify <id> — resume: true` |

> INCONCLUSIVE 与 ZERO_ELIGIBLE 都是"评估坏了"，但坏在不同侧（主实验 vs 变体），路由到 iteration 不同修复面。INTEGRITY_ONLY 则是"审计通过但没做 swap"，无修复动作，iteration 只在 Open Items 里挂个补跑建议。

**🚦 Verify Gate**：同 Experiment Gate 的 `AUTO_PROCEED` 语义——`true` 静默跑（log 出 N_pass/N_fail/... + 两个完整性 verdict）；`AUTO_PROCEED=false AND AUTO_DEPLOY=false` 才 `AskUserQuestion` 阻塞。

---

## 五、iteration 阶段详解（自动审稿循环）

> 逻辑在 `skills/auto-iteration-loop/SKILL.md`，`REVIEW_LOOP=false` 时整个跳过。核心：**外部 LLM 当审稿人 → 给分 + 逐 claim 提修改 → 按类型路由修复并重跑 → 再审**，至多 `MAX_ITERATIONS=6` 轮，达标早停。

### 5.1 一轮的五个 Phase（A → B → B.5 → C → D → E）

- **Phase A 审稿**：调外部 LLM（`mcp__llm-chat__chat`/gpt-5.4，curl 兜底）。第 2 轮起把 `REVIEWER_MEMORY.md`（审稿人持久"怀疑日志"）+ 上轮摘要 prepend 进 prompt（有 `thread_id` 则靠 MCP 线程续接、省略摘要）。审稿人产出 free-form：**1–10 分** + verdict（ready/almost/not ready）+ 逐 claim 行动建议（带路由类型）+ 可选 `## Memory update`。
- **Phase B 解析 + STOP 判定**：分数/verdict 规范化；校验每条路由是否合法（如 INCONCLUSIVE 上请求 ③ 会被拒）。**三维 STOP 规则**：`score ≥ TARGET_SCORE(6)` **AND** `verdict ∈ {ready, almost}` **AND** `verify_failed / verify_inconclusive / verify_zero_eligible` 三桶全空（每条非 deferred claim 都 PASS）。三条全满足才终止；审稿人给高分但还有未决 claim 则 log 后继续。
- **Phase B.5 更新 reviewer memory**：append 一节到 `REVIEWER_MEMORY.md`（新怀疑 / 旧怀疑是否解决 / 仍未决 / 模式）。**append-only**，绝不改旧节（对抗性审计连续性）。
- **Phase C 实施修复**：按路由类型 dispatch（见 5.2），消耗预算并递增计数器。
- **Phase D 等结果**：`/monitor-experiment` 盯远程实验（③ 全路径走 orchestrator handoff，跳过此 phase）。
- **Phase E 记录**：append 到 `AUTO_REVIEW.md`（九个固定子节，空也写 `none`），写 `REVIEW_STATE.json`。

### 5.2 修复路由四类型

| 类型 | 用于 | 做什么 / dispatch | 预算消耗 |
|---|---|---|---|
| **① variant-only** | FAIL（变体完整性脏）或 ZERO_ELIGIBLE | 改/删变体脚本 → `/auto-verify <id> — resume:true` | 1 iteration |
| **② main-experiment-script** | **仅 INCONCLUSIVE** | 改 `EXPERIMENT_PLAN.md` 故障步 + 主实验脚本（保留 `resource_fidelity:strict` 行 verbatim）→ 重跑 | 1 iteration（单 claim 最多 2 次 ②） |
| **③ claim 重入** | **仅 Phase-2-passed 的 FAIL** | 重写 claim（轻量 in-loop 改写，或全路径重入 `/auto-claim`→`/auto-experiment`→`/auto-verify`） | 1 iteration **+ 1 claim-reentry** |
| **⓪ narrative-only** | 只需 paper 侧 caveat/改写 | 写进 `AUTO_REVIEW.md` 的 Actions Taken | **0**（不计预算） |

路由有**强约束**：INCONCLUSIVE 禁止改写 claim（主实验才是坏的，须先修到主实验过 Phase 2、claim 变 FAIL 才能改）；ZERO_ELIGIBLE 只修变体不动主实验/claim；deferred claim **本轮不许任何动作**（只记 Open Items，须先单独 `/auto-verify <id>`）。

### 5.3 五个 verify 结果桶的处理

orchestrator 从 `VERIFY_REPORT.md` 抽五桶转发给 iteration agent（它只做提取转发，路由由 iteration skill 拥有）：

| 桶 | 状态 | 处理 |
|---|---|---|
| `verify-passed` | PASS | 仅叙事一致性检查，不消耗 iteration |
| `verify-failed` | FAIL | 两阶段：Phase1 查/修变体完整性(①)，仍 FAIL 则 Phase2 改写 claim(③) |
| `verify-inconclusive` | INCONCLUSIVE | 只修主实验(②)，禁动 claim |
| `verify-zero-eligible` | ZERO_ELIGIBLE | 只修变体(①)，禁动主实验/claim |
| `deferred-claims` | （无状态） | 本轮无动作，记 Open Items |

### 5.4 预算 + 终止 + 状态持久化

- **`MAX_ITERATIONS=6`**：对 ①/②/③ 总次数的硬上限（⓪、PASS 检查、deferred 记录都不计）。耗尽 → `iterations_exhausted`。
- **`MAX_CLAIM_REENTRIES=2`**：③ 的子预算（防"光改 claim 不修实验背后"的失败模式）。耗尽 → Phase C 拒绝再 ③，回退 ① 或终止 `claim_reentry_exhausted`。③ 产出的新 claim **共享同一预算**，不另分配。
- **STOP 三维规则**（见 5.1）满足 → `positive_verdict`。**stall 守卫**：连续 2 轮 ⓪-only 且分数/verdict 不变 → `stalled` 终止。
- **`REVIEW_STATE.json`**（每 Phase E 写）：`iterations_consumed` / `claim_reentries_consumed` / `status`(in_progress/awaiting_upstream/completed) / `last_score` / `last_verdict` / `consecutive_noop_count` / `iteration_breakdown[]` / `pending_upstream_calls` / `thread_id` / `termination_reason` 等。
- **`awaiting_upstream` 回边 handoff**：③ 走全路径时，agent 置 `status=awaiting_upstream` + 填 `pending_upstream_calls`（`auto-claim`→`auto-experiment`→`auto-verify`）后返回；orchestrator 顺序执行这些调用，全部落盘后以 `resume:true` 重新唤起 iteration agent（计数器从 state 继承，不重置）。轻量 ③ 在同一轮内 inline 跑完，不走 handoff。
- **Resume 陈旧检查**：state 超 24h 归档重来（`awaiting_upstream` 例外，那是有意的长时 handoff）。
- **Resource-Fidelity 不变量**：每条触及 `EXPERIMENT_PLAN.md` 或重入 claim 的回边（②、③）必须保留 `resource_fidelity: strict`（③ 全路径靠从 `IDEA_REPORT.md` 的 `**Mode**:` 头检测 mode 自动重盖），丢了会静默关掉降配防护。

### 5.5 产物 + 终态

- `AUTO_REVIEW.md`（逐轮 append-only 审计日志，九固定子节）
- `REVIEW_STATE.json`（机器状态，crash 恢复用）
- `REVIEWER_MEMORY.md`（第 2 轮起，审稿人跨轮怀疑日志，append-only）
- `AUTO_ITERATION_FINAL_REPORT.md`（终止时一次性合成，按 verify 原始分类组织每条 claim 的迭代旅程）

终态：`positive_verdict` / `iterations_exhausted` / `claim_reentry_exhausted` / `stalled`（均 `status=completed`），或 `awaiting_upstream`（handoff，非终态）。

**末轮 Ledger Figures hook**：iteration 正常终止（或 `REVIEW_LOOP=false` 时的 verify 末写）后，若 `LEDGER_FIGURES != false`，调一次 `/paper-figure` 给每条非 deferred claim 生成 0–3 张出版级图/表，inline 嵌进 `CLAIMS_LEDGER.md`（每次 pipeline run 仅触发一次）。

---

## 六、常见改动点

**模型相关：**
- 改某阶段固定版本号 → 编辑 `agents/<name>.md` frontmatter `model:` 行（**别在 CLI 传版本号**）。
- 临时换阶段模型 → CLI 传家族别名，如 `/auto "..." — verify-model: opus`。
- 换 orchestrator 模型 → 会话层切主模型（`/model`、`/fast`）。
- 换陪审/审稿模型 → `plugin.json` 的 `llm_model` 或 `LLM_MODEL` 环境变量（pre-flight 三级优先级：项目 `.mcp.json` > 用户 settings > shell env，**严禁 hardcode**）。

**Claim 相关：**
- 加检索源 → `research-lit/SKILL.md` Source Table。
- 改 novelty 深度 → `novelty-check/SKILL.md` Phase B 的 query 数/年限/Phase C prompt。
- 改 impact 判定 / 排序权重 → `impact-check/SKILL.md` + `auto-claim/SKILL.md`（Phase 3.5 impact-first 重排）。
- 改 verify 用的 data/model → 源头是 `experiment-plan/SKILL.md` Phase 3「Specify Each Experiment Block」（别去 verify 改，它只消费 + swap）。
- 改是否上 M0 → `BEHAVIOR_SOURCE`（`given` 无 M0 / `given-validation`·`discovery` 带 M0）；改谁选机理方法 → `MECHANISM`（`given` 用户指定 / `discovery` 系统路由）。

**Experiment 相关：**
- 改 dispatch 路由阈值 → `auto-experiment/SKILL.md` Phase 4.0 表格。
- 改 sanity 自动 debug 次数 → Phase 3 硬编码 `max 3 attempts`。
- 改 code review 检查项 → Phase 2.5 的 7 条（尤其 #5 GT、#6 scorer 两条 hard rule）。
- 注意 `EXPERIMENT_TRACKER.md` 所有权属 claim，experiment 只原地翻 Status，越界 wholesale 重写会毁 audit trail。

**Verify / Iteration 相关：**
- 改变体轴数 / 鲁棒性阈值 → `DIMENSIONS` / `ROBUSTNESS_THRESHOLD` / `MIN_VARIANTS_FOR_VERDICT`。
- 改迭代预算 / 早停线 → `MAX_ITERATIONS` / `MAX_CLAIM_REENTRIES` / `TARGET_SCORE`。
- method swap 的同 family 约束、四终态语义在 `auto-verify/SKILL.md`；路由四类型 + 预算在 `auto-iteration-loop/SKILL.md`（单一真相源，别在 orchestrator 里重复定义）。
</content>
</invoke>
