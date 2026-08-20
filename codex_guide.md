# Mechanist 双端兼容版 —— 安装与使用

此文件仅供内测使用，非面向用户的正式文档。

## 1. 修改背景

Codex 与 Claude Code 在 SKILL 编写、MCP 等约定上有差别。此前 Mechanist 主线版本只适配 Claude Code；为了在保证 Claude Code 兼容性的同时对 Codex 进行兼容，需要对用词表述、工具名称、文件组织形式等进行调整。

如果为 Codex 与 Claude Code 各自维护一套插件定义，改动会重复、容易分叉。因此只维护一份插件定义——也就是现在这份，同时给 Codex 与 Claude Code 用。

未来优化、检验后，计划使用本分支的版本取代现有版本，成为主线。

## 2. 安装插件

### 2.1 Claude Code

使用如下命令启动 Claude Code 会话，启动前确保 Mechanist 仓库已切换至 `codex-compat` 分支：

```bash
claude --plugin-dir <path/to/Mechanist>
```

### 2.2 Codex

使用如下命令将 Mechanist 安装到 Codex，安装前确保 Mechanist 仓库已切换至 `codex-compat` 分支：

```bash
codex plugin marketplace add /absolute/path/to/Mechanist
codex plugin add mechanist@mechanist
codex plugin list       # 必须显示 mechanist@mechanist 已安装并启用
codex mcp list          # 必须显示 llm-chat 和 mechanic-db 已启用
```

## 3. 更新插件

若对本地 Mechanist 仓库进行了修改，若想应用修改：

### 3.1 Claude Code

关闭 Claude Code 窗口并重启即可。

### 3.2 Codex

改源码不会自动应用修改，必须卸载插件后重新安装：

```bash
codex plugin remove mechanist@mechanist
codex plugin add mechanist@mechanist
codex plugin list
```

## 4. 在会话中调用 Mechanist

skill 名字相同，只是不同平台的前缀不同：Claude Code 用 `/`，Codex 用 `$`。

| 平台 | 调用示例 |
|---|---|
| Claude Code | `/auto behavior-source: discovery, mechanism: discovery` |
| Codex | `$auto behavior-source: discovery, mechanism: discovery` |