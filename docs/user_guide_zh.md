# Mechanist — 用户指南

**此文档涵盖日常使用的高级技巧。**

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