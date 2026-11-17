<p align="center"><img src="docs/mechanist-light-logo.png" alt="Mechanist" width="778" height="150"></p>

<p align="center">
  <strong>为自主机理研究提供方法库、人类经验与工具支持</strong>
</p>

Mechanist Light 是 Mechanist 的轻量版本，以 Claude Code 插件的形式提供。你用自然语言交给它一个关于神经网络内部机理的研究问题，基模会自主规划并推进研究，最后汇报有证据支撑的发现、不确定性与局限。

## 设计理念

完整版 Mechanist 把研究组织成固定的流水线（claim → experiment → verify → iteration），配有台账、审计关卡和多轮外部评审。这套流程保证了可追溯性，但也把很多本该灵活的判断固定了下来。

Light 版的出发点是：**当前基模已经足够强，与其规定流程，不如给它自由度和好用的资源。** 因此：

- **不规定流程**：没有必经阶段、步骤类型、全局记忆格式或实验记录文件。研究路线、任务拆分、方法组合，以及是否和如何记录信息，都由基模自主决定。
- **只提供资源**：把完整版中真正有价值的内容——方法知识、实践经验、检索渠道、外部视角，整理成按需取用的能力，在基模需要时补上它的短板。
- **建议而非规范**：各项能力中的经验与规则都是供参考的建议，基模结合具体问题和证据自行取舍。

## 安装

### 1. 克隆仓库

```bash
git clone -b Mechanist-Light https://github.com/zjunlp/Mechanist.git Mechanist-Light
cd Mechanist-Light
pip install -r requirements.txt
```

### 2. 启动 Claude Code

启动 Claude Code 时用 `--plugin-dir` 指向克隆下来的 `Mechanist-Light` 目录（需要使用绝对路径）：

```bash
claude --plugin-dir /绝对路径/Mechanist-Light
```

进入会话后输入 `/mechanist`，能看到 `/mechanist:mechanist` 等技能，就说明本插件加载成功。

### 3. 配置外部服务

外部模型交互功能支持使用 OpenAI 兼容的 Chat Completions 接口。若要启用外部模型交互功能，需将下述变量写进 `~/.bashrc`（或 `~/.zshrc`）：

```bash
# --- Mechanist Light (Example) ---
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-6.1-sol"
```

> [!NOTE]
> 与外部模型讨论的价值在于为 Agent 引入不同的视角，建议选用与基模不同系列的模型。

## 快速开始

1. 为每个研究问题新建一个工作目录，在其中启动 Claude Code：

   ```bash
   mkdir my-research && cd my-research
   conda activate scientist
   claude --plugin-dir /绝对路径/Mechanist-Light
   ```

2. 在会话中输入技能名称，后面接上你的研究指令：

   ```text
   /mechanist:mechanist 研究 Qwen3-1.7B 为什么会陷入重复推理。请选择能区分"特定内部信号"和"普遍生成抑制"的方法，在单卡 A100 的预算内自主推进，并说明证据支持什么结论。
   ```

3. 基模会自主决定研究路线、方法组合、何时查阅经验或文献等，最后汇报发现、不确定性与局限。

写指令时，交代清楚研究目标、目标模型、数据或资源约束（如期望使用的数据集、可用 GPU、时间预算）以及你关心的结论类型即可。如果有特别的要求，比如指定方法、指定数据集，或者希望它在某个环节与外部模型讨论，也可以直接写进指令。

## 架构

```
              /mechanist:mechanist  <你的研究指令>
                           │
                 ┌─────────▼─────────┐
                 │   Mechanist 入口   │   科学家角色提示
                 └─────────┬─────────┘
       ┌───────────────┬───┴───────────┬────────────────┐
       ▼               ▼               ▼                ▼
  机理方法库        人类经验库      信息检索工具   外部模型交互工具
```

入口是一段科学家提示词，介绍四项可供 Agent 调用的能力：

| 能力 | 目录 | 提供什么 |
| --- | --- | --- |
| 机理方法库 | `skills/mechanism-methods/` | 11 个方法家族、32 个具体方法的选择指引、论文、API 文档与代码模板 |
| 人类经验库 | `skills/human-expertise/` | 一份按情境组织的索引和 11 篇经验笔记，涵盖现象发现、研究策略、特征选择、steering 层位与强度、微调学习率、数据与证据、答案测量、图像预处理、训练诊断和研究判断 |
| 信息检索工具 | `skills/information-retrieval/` | 查找和获取论文、博客、GitHub 项目、文档等外部信息；可结合宿主自带的检索工具，以及内置的 Mechanic DB、arXiv、Semantic Scholar、DeepXiv、Exa 脚本 |
| 外部模型交互工具 | `skills/model-consultation/` | Agent 可使用此工具，与其他 AI 模型讨论研究中的问题，例如拿不定主意时一起商量下一步，或讨论主张的新颖性、实验设计、代码和结论；使用时机由 Agent 自己决定 |

## 目录结构

```text
Mechanist-Light/
├── skills/
│   ├── mechanist/               # 入口：科学家提示词
│   ├── mechanism-methods/       # 机理方法库
│   ├── human-expertise/         # 人类经验库
│   ├── information-retrieval/   # 信息检索工具
│   └── model-consultation/      # 外部模型交互工具
├── docs/
└── requirements.txt
```