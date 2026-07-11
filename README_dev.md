# Mechanist - 开发模式安装

本项目提供两种安装模式：

- **插件模式安装**：最适合普通用户，开箱即用（参考 [README](./README.md)）。
- **开发模式安装**：最适合测试者 / 开发者，本地改 skill 提示词或辅助代码后便于调试（本文档介绍的安装方法）。

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
这一步是创建一个conda环境，然后安装一些简单且日常使用的库，如果你有自己的环境，可以省略这一步

Create a dedicated conda environment `scientist` for the experiment execution stage and install its dependencies:
```bash
conda create -n scientist python=3.11 -y
conda activate scientist
pip install -r <(curl -sSL https://raw.githubusercontent.com/WangHX2024/homepage/main/requirements.txt)
```

> TODO：上述链接 `WangHX2024/homepage` 在正式上线版本将被替换为 `zjunlp/MECHANIST`。

### 1.4 配置 API key

开发模式（`--plugin-dir`）下，Mechanist 的两个 MCP server 通过**环境变量**读取配置。请提前准备好对应的值。

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

改完执行 `source ~/.bashrc`（或重开一个新终端）使其在当前 shell 生效，用 `echo "$LLM_API_KEY"` 确认非空。

## 2 为 Claude Code 安装 Mechanist 插件（开发模式）

### 2.1 Clone 本仓库

```bash
cd <repo-dir>
git clone https://github.com/mengrusun/MECHANICA.git
```

### 2.2 启动 Claude Code（开发模式）

在**已设置好 §1.4 环境变量**的 shell 里，带 `--plugin-dir` 启动：

```bash
claude --model claude-opus-4-7 --plugin-dir <repo-dir>/MECHANICA
```

启动后用 §2.3 的 `/mcp` 检查 `llm-chat` 与 `mechanic-db` 是否 `connected`。

### 2.3 Verify the installation

Skills and helper servers will be loaded automatically. Confirm the installation with two checks:

- Run `/help` and verify that Mechanist skills are available, for example `/mechanist:auto`, `/mechanist:msearch`, and `/mechanist:mhistory`.
- Run `/mcp` and confirm that both `llm-chat` and `mechanic-db` are marked as **connected**.

### 2.4 开发模式下的修改何时生效

`--plugin-dir` 会让 Claude Code 直接从本地目录读取插件，这样更适合需要修改 Mechanist 源码、skill 提示词、agent prompt 或 MCP helper server 的测试者 / 开发者。

| 修改内容 | 生效方式 |
|---|---|
| `skills/`、`agents/`、slash command、prompt 文本 | 在 Claude Code 中运行 `/reload-plugins`，之后重新调用对应命令。 |
| MCP / helper server 的 Python 代码 | 需要重启 Claude Code。`/reload-plugins` 不会重启已经运行的 server 进程。 |
| 插件 manifest（`plugin.json`）/ MCP 配置 | 需要重启 Claude Code。 |
| 环境变量（`LLM_API_KEY` 等） | 需在启动 `claude` 的 shell 里改好并**重启 Claude Code**；启动后再改不会被已运行的 server 读到。 |

> [!NOTE]
> 修改 `skills/` 的本地内容后，Claude Code 默认会在 3–5 秒内自动刷新 skills 缓存；`/reload-plugins` 只是手动强制刷新、上一道保险。

> [!IMPORTANT]
> 欢迎把对 auto pipeline 的改进提交到 GitHub 仓库共创，但**切记不要上传自己的实验 case 内容**。

## 3 对同一实验重复多次时的隔离配置

当你希望对同一个实验重复运行多次（例如 `verbal_confidence1`、`verbal_confidence2`、`verbal_confidence3` …）、但**不希望之前跑过的实验目录被 Claude Code 读到，从而干扰新一轮的独立性**时，可以在**当前实验目录**下放一份 `.claude/settings.local.json`，用 `permissions.deny` 屏蔽掉所有其它历史实验目录的读取权限。

放置位置示例（假设本轮实验目录是 `exp/`）：

```
<project-dir>/
└── exp/
    └── .claude/
        └── settings.local.json     ← 只在这一轮实验目录里生效
```
示例：
```json
{
  "permissions": {
    "deny": [
      "Read(/absolute/path/to/verbal_confidence/**)",
      "Read(/absolute/path/to/verbal_confidence2/**)",
      "Read(/absolute/path/to/other_old_exp/**)"
    ]
  }
}
```

> [!WARNING]
> 这只是"软偏好"，不是硬边界。Claude 仍然**可以**通过 `Bash(cat ...)`、`Bash(head ...)`、`Grep`、`Glob` 等方式间接读到内容。但一般来说禁掉Read够用了。


### 使用要点

- 路径必须是**绝对路径** + `/**` 通配后缀，才能匹配到目录下的全部文件。
- 每新增一轮实验，就在新目录里放一份新的 `settings.local.json`，把所有历史实验目录都追加到 `deny` 里。
- 该文件只对**在这个目录下启动的 Claude Code 会话**生效，不会影响其它项目。

---

安装完成后，请回到 [README §3 quick start](./README.md#3-quick-start) 继续阅读，了解如何创建项目目录、运行 `/msearch`、`/mhistory` 与 `/auto` 等命令。