# External reviewer runtime

The `llm-chat` MCP server owns reviewer credentials and provider defaults. A
Mechanist skill must not read, print, copy, or export an API key from project or
host configuration.

Before the first reviewer call:

1. Confirm that the active host exposes the `llm-chat` MCP server and its chat
   tool. Tool rendering may differ by host; select it by server and tool
   identity rather than requiring a literal tool name.
2. Call the tool without a model override unless the user explicitly supplied
   a reviewer model for this run. The server resolves `LLM_MODEL`,
   `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_FALLBACK_MODEL` from its own process
   environment.
3. If the server or tool is unavailable, stop with a host-neutral diagnostic:
   `External reviewer unavailable: configure and enable the llm-chat MCP server,
   then start a new host session.`
4. If the tool reports missing credentials, tell the user to export
   `LLM_API_KEY` in the environment that launches Claude Code or Codex and then
   start a new session. Never request that a secret be committed to `.mcp.json`.

Direct HTTP is an emergency fallback only when the skill explicitly documents
one and the user has already made the required environment variables available.
Never inspect `~/.claude/settings.json`, `~/.codex/config.toml`, or arbitrary
project files to recover reviewer credentials.
