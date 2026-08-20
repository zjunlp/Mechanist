# Claude Code and Codex host compatibility

Mechanist's workflow text uses Claude Code's historical tool names. Apply the
following host mapping before executing any Mechanist skill. The workflow
semantics and artifact contracts do not change.

| Workflow term | Claude Code | Codex |
|---|---|---|
| Skill invocation | `Skill` or `/skill-name` | Load/invoke the named bundled skill (for example `$skill-name` when entered explicitly) |
| Isolated stage worker | `Agent` | Spawn a sub-agent with the same self-contained prompt when sub-agents are available; otherwise execute the stage in the current context |
| Interactive choice | `AskUserQuestion` | Use Codex user-input UI when available, otherwise ask one concise question and wait |
| Scheduled notification | `CronCreate` / `CronList` | Use scheduled tasks when available; otherwise skip hourly scheduling and retain event-driven notifications |
| Invocation arguments | `$ARGUMENTS` | The text or structured options supplied with the current skill invocation |
| Plugin root | `${CLAUDE_PLUGIN_ROOT}` | `${PLUGIN_ROOT}`; bundled launchers resolve their own location and do not require either variable |
| Web retrieval | `WebSearch` / `WebFetch` | Native `web_search` capability; do not call the Claude-only names |

Additional rules:

- Treat `allowed-tools` as a capability declaration, not a requirement that
  the host expose tools under those exact names.
- In shared workflow prose, refer to a bundled workflow as the `name` skill,
  without a `/` or `$` prefix. Those prefixes are user-interface syntax, not a
  portable skill identity. When writing a command that a human should copy,
  show both forms explicitly: `Claude Code: /name ...` and `Codex: $name ...`.
  Generated artifacts such as `task.md` must follow the same rule.
- In shared workflow prose, say **web retrieval** rather than requiring a
  literal tool name. On Claude Code this maps to `WebSearch` and `WebFetch`;
  on Codex it maps to native `web_search` (including URL/open retrieval when
  supported). If unavailable, use the documented API/MCP/local fallback and
  record the limitation.
- Never fabricate an unavailable tool. Follow the fallback in the table.
- A model override may be a host-native model identifier. Claude aliases such
  as `opus`, `sonnet`, and `haiku` remain valid on Claude Code; Codex model IDs
  remain valid on Codex. If omitted, inherit the session model.
- MCP tools are selected by server and tool identity. Their rendered names may
  differ between hosts; use the `llm-chat` and `mechanic-db` server tools that
  the active host exposes.
