# Mechanist — 开发者指南

**面向需要修改 skill 提示词、agent 定义或 MCP 服务代码的贡献者。**

> 如果你只是想**使用** Mechanist 运行实验，这份文档不适合你——请阅读[主 README](./README_zh.md)。本指南面向希望修改 Mechanist 内部行为的开发者。

---

## 目录

- [环境搭建](#环境搭建)
  - [1. 前置条件](#1-前置条件)
  - [2. 克隆并启动](#2-克隆并启动)
  - [3. 验证](#3-验证)
- [开发工作流](#开发工作流)
- [实验隔离](#实验隔离)

---

## 环境搭建

### 1. 前置条件

先完成[主 README](./README_zh.md#-安装) 中的基础安装步骤：

- 安装 Claude Code 并登录
- 安装 uv
- 创建 `scientist` conda 环境
- 配置环境变量（`LLM_API_KEY` 等）

完成后再回到这里继续。

### 2. 克隆并启动

克隆仓库并以 `--plugin-dir` 指向本地副本启动 Claude Code：

```bash
git clone https://github.com/zjunlp/Mechanist.git
```

```bash
# 创建工作目录（任意位置——推荐放在仓库旁边）
mkdir exp && cd exp

# 通过 --plugin-dir 让 Claude Code 从本地副本加载插件
claude --model claude-opus-4-7 --plugin-dir ../Mechanist
```

```
<dir>/
├── Mechanist/   # 本地克隆（插件源码）
└── exp/         # 实验工作目录
    └── task.md
```

这是与用户模式的关键区别：`--plugin-dir` 让 Claude Code 直接从本地文件系统加载插件，因此你对源码的编辑可以即时生效。

### 3. 验证

与用户模式相同的检查：

- 运行 `/help`——Mechanist skills 应已出现。
- 运行 `/mcp`——`llm-chat` 与 `mechanic-db` 应显示为 **connected**。

---

## 开发工作流

编辑 Mechanist 源文件后，修改何时生效取决于你改了什么：

| 修改内容 | 生效方式 |
|:---|:---|
| `skills/`、`agents/`、slash command、prompt 文本 | 在 Claude Code 会话中运行 `/reload-plugins`。（Claude Code 也会在 3–5 秒内自动刷新 skills；`/reload-plugins` 是手动强制刷新。） |
| MCP / helper server Python 代码（`mcp-servers/`） | **重启 Claude Code。**`/reload-plugins` 不会重启已在运行的 server 进程。 |
| 插件清单（`plugin.json`）/ MCP 配置 | **重启 Claude Code。** |
| 环境变量（`LLM_API_KEY` 等） | 在启动 shell 中修改后**重启 Claude Code**——已运行的 server 不会在会话中途读取新值。 |

> [!IMPORTANT]
> 将改动提交回仓库时，**切勿上传实验 case 内容**（`exp/` 目录、含私密数据的 `task.md` 等）。

---

## 实验隔离

当对同一实验重复运行多次时（如 `exp1`、`exp2`、`exp3`），智能体可能会无意中读取历史运行的产物，污染当前运行。在开发模式下这尤为重要，因为你大概率在反复迭代同一个实验。

以下提供两种机制控制智能体的文件访问范围，可任选其一或同时使用。

### 方案一：Prompt 软约束

在 `task.md` 中添加禁令：

```text
禁止读取其它实验目录，禁止借鉴既往实验的数据、方案、组别设计等信息。
```

编排器会在派发每个子 Agent 时显式注入该指令。这是**提示词层面的约束**，依赖模型遵循指令。

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