# Codex installation and operation

Mechanist is a dual-host plugin. Claude Code loads `.claude-plugin/plugin.json`;
Codex loads `.codex-plugin/plugin.json`, the bundled Skills, and `.mcp.json`.
The Codex path is tested with `codex-cli 0.148.0`.

## Prerequisites

- Codex CLI or Codex in the ChatGPT desktop app
- Python 3.11 or newer
- `uv` available on `PATH`
- A writable experiment directory
- Optional GPU and SSH credentials required by the experiments you request

The Codex IDE extension does not currently load plugins. Use the CLI or desktop
app for Mechanist workflows.

## Install from this checkout

Register the repository as a local marketplace and install the plugin:

```bash
codex plugin marketplace add /absolute/path/to/Mechanist
codex plugin add mechanist@mechanist
codex plugin list
codex mcp list
```

`codex plugin list` must show `mechanist@mechanist` as installed and enabled.
`codex mcp list` must show `llm-chat` and `mechanic-db` as enabled. Start a new
Codex thread after installation or reinstallation; existing threads retain the
Skill and tool catalog with which they started.

Codex installs a cached snapshot. Editing the source checkout does not update
the active copy. During development, update the plugin cachebuster, reinstall,
and open a new thread.

## Configure the external services

Export credentials in the shell that launches Codex:

```bash
export LLM_API_KEY="..."
export LLM_MODEL="gpt-5.6-luna"
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_FALLBACK_MODEL="gpt-5.6-luna"
export MECHANIC_DB_API_KEY="..."
codex
```

`LLM_API_KEY` is required for the external reviewer. `LLM_MODEL`,
`LLM_BASE_URL`, and `LLM_FALLBACK_MODEL` have launcher defaults.
`MECHANIC_DB_API_KEY` is optional because the paper service provides a limited
anonymous tier. Never commit credentials to `.mcp.json`, `.codex/config.toml`,
`task.md`, or generated reports.

The MCP process owns these values. Mechanist Skills do not inspect Codex or
Claude configuration files for secrets.

## Create an experiment project

Use one directory per research question:

```bash
mkdir my-mechanist-experiment
cd my-mechanist-experiment
printf '# Research task\n\nDescribe the behavior and constraints here.\n' > task.md
codex
```

For a conservative local permission baseline, adapt
[`examples/codex-config.toml`](examples/codex-config.toml) into
`.codex/config.toml`. Keep `sandbox_mode = "workspace-write"` unless the
experiment genuinely requires broader filesystem access. Network, remote SSH,
and commands outside the workspace can still require approval.

Historical run isolation is strongest when each run has its own directory and
the workspace root is that directory. Do not start Codex from a parent folder
containing other experiment runs if cross-run contamination matters.

## Invoke Mechanist

Codex invokes Skills by intent or explicit `$skill-name` mention:

```text
$auto
$auto behavior-source: discovery, mechanism: discovery
$msearch sparse autoencoder feature splitting
$monitor-experiment
```

The full pipeline is sequential:

```text
claim -> experiment -> verify -> iteration -> claim ledger
```

Installed-plugin runs use isolated Codex workers with a self-contained stage
prompt. `.codex/agents/*.toml` is used when Mechanist itself is the active
project checkout; it is not required in the user's experiment directory.

When subagents are unavailable or disabled, the pipeline executes the same
stage contract in the parent context and records a `[host-fallback]` note.

## Verify an installation

From the Mechanist source checkout, run the offline compatibility suite:

```bash
python3 -m unittest discover -s tests -v
```

It checks manifests, custom agents, Skill metadata and catalog budget, secret
ownership, archival safety, and both MCP protocol handshakes without making an
external API call. A complete release qualification additionally runs a small
real task through `$auto`, interruption/resume, and `$next-round` with test API
credentials and a bounded compute budget.

## Troubleshooting

### Skills are missing

Confirm the plugin is installed and enabled with `codex plugin list`, reinstall
after source changes, then open a new thread. Codex does not refresh the active
thread's initial Skill catalog.

### MCP server is enabled but unavailable

Run `uv --version` and `codex mcp list`. The launcher prints a targeted error
when `uv` is missing. First startup may need network access to populate the `uv`
dependency cache. In restricted Codex sandboxes the launcher uses
`$TMPDIR/mechanist-uv-cache` instead of assuming that `~/.cache` is writable;
set `UV_CACHE_DIR` before starting Codex to choose a persistent alternative.
If the host Python already provides `httpx`, the launcher reuses that runtime
and does not access the package index.

### Reviewer reports missing credentials

Export `LLM_API_KEY` before starting Codex, close the current session, and start
a new one. Exporting it from a command inside an already-running agent does not
change the environment of the existing MCP server.

### A stage cannot spawn a subagent

Check that agents are enabled in project or global Codex config. Mechanist will
fall back to the parent context, but this reduces context isolation. For long
research runs, enable agents and allow at least one child thread.

### A command needs broader permissions

Review the exact command and target, then approve only the needed operation.
Do not switch the whole project to unrestricted access solely to avoid normal
approval prompts.

## Compatibility contract

| Capability | Claude Code | Codex CLI/Desktop |
|---|---|---|
| Workflow Skills | Slash command / Skill tool | Intent or `$skill-name` |
| Isolated stages | Plugin agents | Codex subagents; parent fallback |
| User choices | `AskUserQuestion` | Native user-input UI or concise question |
| Web retrieval | `WebSearch` / `WebFetch` | Native web-search capability |
| External reviewer | `llm-chat` MCP | `llm-chat` MCP |
| Paper retrieval | `mechanic-db` MCP | `mechanic-db` MCP |
| Hourly notifications | Host scheduler when available | Scheduled task when available; otherwise event-driven only |

The authoritative mapping is
[`skills/shared-references/host-compatibility.md`](../skills/shared-references/host-compatibility.md).
