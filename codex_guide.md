# Codex 版 Mechanist 安装与使用

此文件仅供内测使用，非面向用户的正式文档。

## 从当前源码目录安装 Mechanist 插件

将仓库注册为本地 marketplace，然后安装插件：

```bash
codex plugin marketplace add /absolute/path/to/Mechanist
codex plugin add mechanist@mechanist
codex plugin list       # 必须显示 `mechanist@mechanist` 已安装并启用
codex mcp list          # 必须显示 `llm-chat` 和 `mechanic-db` 已启用
```

## 更新 Mechanist 插件

修改本地仓库后，不会自动更新已安装到 Codex 中的插件副本。
因此，修改插件文件后，需要重新安装插件：

```bash
codex plugin remove mechanist@mechanist
codex plugin add mechanist@mechanist
codex plugin list
```

如果使用 Codex Desktop，还需要重启桌面应用。

## 在会话中调用 Mechanist

在 Codex 中，使用 `$skill-name` 调用 skill（即：将 Claude Code 调用 skill 时的 `/` 符号换为 `$` 符号）。

示例：在 Codex 会话中输入
```text
$auto behavior-source: discovery, mechanism: discovery
```