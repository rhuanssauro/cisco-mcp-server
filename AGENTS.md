# AGENTS.md — cisco-mcp-server

## Project Scope
Python MCP server that provides guarded Cisco device operations through Scrapli (show, configure, ping, running-config retrieval).

## Repository Signals
- Detected stack/profile: python, mcp, network
- Latest repository commit date: `2026-02-11`

### Key Local Paths
- `server.py`
- `pyproject.toml`
- `uv.lock`

## Recommended Agents (from ~/.claude)
| Agent | Why it applies |
|---|---|
| `python-development` | Async Python server behavior and tool interfaces. |
| `mcp-integration` | MCP tool contracts and runtime integration concerns. |
| `cisco-guru` | IOS-XE/IOS-XR/NX-OS command safety and operational semantics. |
| `security-reviewer` | Credential handling and command guardrails. |
| `code-reviewer` | Final consistency and regression review. |

## Working Rules
Use these related global rules for this repository:
- `~/.claude/rules/git-workflow.md`
- `~/.claude/rules/security.md`
- `~/.claude/rules/coding-style.md`

## Preferred Commands
- Sync dependencies: `uv sync`
- Local run: `uv run python server.py`
- Syntax sanity check: `python -m py_compile server.py`

### Runtime Configuration
- Inventory source priority is implemented in `server.py`:
  1. `CISCO_DEVICES_JSON` (multi-device JSON file)
  2. Fallback single device env vars (`CISCO_HOST`, `CISCO_USER`, `CISCO_PASS`, `CISCO_PLATFORM`, `CISCO_PORT`)
- Keep secrets in environment or secret storage, never in source control.

## Quality Gates
- Preserve command safety controls in `_validate_show()` and `_config_guardrails()`; do not weaken blocked-command coverage.
- Maintain explicit JSON status payload shape (`status`, `data`/`error`) across tool responses.
- Any new MCP tool must follow current error-handling pattern and close Scrapli connections reliably.

## Security and Secrets
- Do not commit real device inventories or credentials.
- Keep `auth_strict_key`/transport security choices deliberate and documented when changed.
- Continue blocking destructive command patterns in config operations unless explicitly re-approved.

## Project-Specific Notes
- Tooling currently expects reachable Cisco devices and valid credentials; there is no offline mock harness in this repo.
- No direct repo mapping found under `~/.claude/projects`; fallback uses relevant global agent/rule guidance only.

## Maintenance
- Last synchronized: `2026-02-13`
- Recency basis: latest repo commit `2026-02-11`
- Update this file when new MCP tools, guardrails, or env contracts are introduced.

## Sources Used
- `server.py`
- `pyproject.toml`
- `uv.lock`
- `~/.claude/agents/python-development.md`
- `~/.claude/agents/mcp-integration.md`
- `~/.claude/agents/cisco-guru.md`
- `~/.claude/agents/security-reviewer.md`
- `~/.claude/agents/code-reviewer.md`
- `~/.claude/rules/git-workflow.md`
- `~/.claude/rules/security.md`
- `~/.claude/rules/coding-style.md`
