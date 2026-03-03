# Cisco MCP Server

[![MCP Server Badge](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

Direct Cisco device access via Model Context Protocol (MCP). Execute show commands, apply configurations, and troubleshoot Cisco IOS-XE, IOS-XR, and NX-OS devices programmatically through Claude.

## Overview

The Cisco MCP Server provides a secure, validated interface to Cisco network devices using Scrapli for SSH transport. It integrates with Claude Code and other MCP clients to enable intelligent network automation, troubleshooting, and configuration management.

### Supported Platforms

- **Cisco IOS-XE** (routers, switches, ISR/ASR platforms)
- **Cisco IOS-XR** (service provider platforms)
- **Cisco NX-OS** (data center switches)

## Features

### MCP Tools

| Tool | Purpose | Parameters |
|------|---------|-----------|
| `cisco_list_devices` | List all configured Cisco devices | None |
| `cisco_show` | Execute read-only show commands | `device_name`, `command` |
| `cisco_configure` | Apply configuration commands | `device_name`, `config_commands` |
| `cisco_ping` | Execute ping from device to target | `device_name`, `target`, `count` (default: 5) |
| `cisco_get_running_config` | Retrieve running configuration | `device_name`, `section` (optional) |

### Safety & Validation

- **Read-only enforcement**: Show commands validated to prevent configuration changes
- **Dangerous command blocking**: Rejects `reload`, `write erase`, `delete`, `format`, `erase` commands
- **Pipe/redirect blocking**: Prevents output manipulation with `|` or `>`
- **Configuration guardrails**: Validates config commands before execution
- **Connection error handling**: Graceful error reporting for SSH/auth failures
- **Automatic session cleanup**: Connections closed after each operation

## Prerequisites

- **Python**: 3.11 or higher
- **Network access**: SSH connectivity to Cisco devices (port 22 by default)
- **Credentials**: Username and password or key-based authentication
- **Dependencies**: See `pyproject.toml` — automatically managed by `uv`

## Installation

### Using `uv` (Recommended)

```bash
cd cisco-mcp-server
uv sync
```

### Using `pip`

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Configuration

### 1. Device Inventory Setup

Create a `devices.json` file in the project root with your Cisco devices:

```json
{
  "CISCO": [
    {
      "name": "core-router-1",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "$CISCO_PASSWORD",
      "platform": "iosxe",
      "port": 22
    },
    {
      "name": "core-switch-1",
      "host": "192.168.1.2",
      "username": "admin",
      "password": "$CISCO_PASSWORD",
      "platform": "nxos",
      "port": 22
    }
  ]
}
```

**Platform values**: `iosxe`, `ios` (alias for iosxe), `iosxr`, `nxos`

### 2. Credential Management

Store credentials in encrypted vault (recommended) or environment variables.

#### Option A: Encrypted Vault (Ansible Vault)

```bash
# Derive vault password
VAULT_PASS="claude-agent-vault-$(hostname)-$(id -u)"

# Create encrypted file
ansible-vault create ~/.claude/credentials/cisco-devices.vault.yaml \
  --vault-password-file=<(echo "$VAULT_PASS")
```

Contents:
```yaml
cisco_password: "your-secure-password"
cisco_api_key: "your-api-key"
```

#### Option B: Environment Variables

```bash
export CISCO_PASSWORD="your-password"
export CISCO_HOST="192.168.1.1"
export CISCO_USERNAME="admin"
```

### 3. Environment Configuration

Create `.env` file in project root (not committed to git):

```bash
# Device inventory path (relative or absolute)
DEVICE_INVENTORY_PATH="./devices.json"

# Optional: override credentials
CISCO_PASSWORD="your-password"
CISCO_USERNAME="admin"

# Optional: connection timeout (seconds)
SCRAPLI_TIMEOUT=30
```

### 4. Claude Code Integration

Add to `~/.claude/settings.json` or `~/.claude.json`:

```json
{
  "mcp_servers": {
    "cisco": {
      "command": "uv",
      "args": [
        "run",
        "--cwd",
        "/path/to/cisco-mcp-server",
        "python",
        "-m",
        "server"
      ],
      "env": {
        "DEVICE_INVENTORY_PATH": "/path/to/devices.json",
        "CISCO_PASSWORD": "${CISCO_PASSWORD}"
      }
    }
  }
}
```

Or in `~/.claude/CLAUDE.md`:

```bash
# In your CLAUDE.md agent startup configuration
export DEVICE_INVENTORY_PATH="/path/to/cisco-mcp-server/devices.json"
```

## Usage Examples

### Example 1: Device Inventory

```
User: List all Cisco devices in inventory
Claude: I'll retrieve the device list for you.

$ mcp: cisco_list_devices()
```

**Response:**
```json
{
  "status": "ok",
  "devices": {
    "core-router-1": {
      "host": "192.168.1.1",
      "platform": "iosxe",
      "port": 22
    },
    "core-switch-1": {
      "host": "192.168.1.2",
      "platform": "nxos",
      "port": 22
    }
  }
}
```

### Example 2: Show Commands

```
User: Check the version on core-router-1
Claude: I'll query the device version.

$ mcp: cisco_show(device_name="core-router-1", command="show version")
```

**Response:**
```json
{
  "status": "ok",
  "device": "core-router-1",
  "command": "show version",
  "output": "Cisco IOS XE Software, Version 17.06.05\nSystem uptime is 45 days..."
}
```

### Example 3: Configuration Changes

```
User: Configure hostname on core-switch-1 to "production-switch"
Claude: I'll apply the hostname configuration.

$ mcp: cisco_configure(
  device_name="core-switch-1",
  config_commands="hostname production-switch"
)
```

**Response:**
```json
{
  "status": "ok",
  "device": "core-switch-1",
  "commands_applied": ["hostname production-switch"],
  "output": ""
}
```

### Example 4: Troubleshooting with Ping

```
User: Ping 8.8.8.8 from core-router-1 to verify internet connectivity
Claude: I'll execute a ping from the router.

$ mcp: cisco_ping(
  device_name="core-router-1",
  target="8.8.8.8",
  count=5
)
```

**Response:**
```json
{
  "status": "ok",
  "device": "core-router-1",
  "target": "8.8.8.8",
  "output": "Success rate is 100 percent (5/5)"
}
```

### Example 5: Configuration Review

```
User: Show me the interface configuration on core-switch-1
Claude: I'll retrieve the interface section from running config.

$ mcp: cisco_get_running_config(
  device_name="core-switch-1",
  section="interface"
)
```

**Response:**
```json
{
  "status": "ok",
  "device": "core-switch-1",
  "command": "show running-config | section interface",
  "output": "interface Ethernet1/1\n  description Uplink to Core\n  no shutdown\n..."
}
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. tests/

# Run specific test class
uv run pytest tests/test_server_tools.py::TestCiscoShow -v
```

### Code Quality

The project uses `ruff` for linting and formatting:

```bash
# Check code style
uv run ruff check server.py

# Auto-format code
uv run ruff format server.py

# Run full lint suite
uv run ruff check . --fix
```

### Project Structure

```
cisco-mcp-server/
├── server.py              # MCP server implementation
├── main.py                # Entry point (placeholder)
├── pyproject.toml         # Project metadata & dependencies
├── ruff.toml              # Linting configuration
├── tests/
│   ├── conftest.py        # Pytest fixtures
│   ├── test_server_tools.py       # Tool handler tests
│   ├── test_server_integration.py # Integration tests
│   └── test_validation.py         # Input validation tests
└── .env.example           # Example environment file
```

### Key Dependencies

- **scrapli** (2025.1.30+): SSH-based network automation
- **asyncssh**: Async SSH client library
- **mcp** (1.26.0+): Model Context Protocol implementation
- **mcp-network-common**: Shared network MCP utilities
- **python-dotenv**: Environment variable management

### Adding New Tools

1. Add tool function decorated with `@mcp.tool()`
2. Include docstring with description and parameters
3. Wrap with `@handle_ssh_errors` for consistent error handling
4. Add tests in `tests/test_server_tools.py`
5. Run validation: `uv run pytest --cov`

Example:

```python
@mcp.tool()
@handle_ssh_errors
async def cisco_traceroute(device_name: str, target: str) -> str:
    """Execute traceroute from device to target.

    Args:
        device_name: Name of the device from inventory
        target: IP address or hostname to trace
    """
    conn = await _get_conn(device_name)
    try:
        response = await conn.send_command(f"traceroute {target}")
        return ok_response(device=device_name, target=target, output=response.result)
    finally:
        conn.close()
```

## Error Handling

The server returns structured JSON responses with status indicators:

```json
{
  "status": "error",
  "error": "Authentication failed: invalid credentials"
}
```

### Common Errors

| Error | Cause | Resolution |
|-------|-------|-----------|
| `Authentication failed` | Invalid username/password | Verify credentials in inventory/vault |
| `Connection error` | SSH timeout or device unreachable | Check network connectivity, firewall rules, port 22 |
| `Device 'X' not in inventory` | Device name not in devices.json | Add device to inventory file |
| `read-only command validation failed` | Attempted non-show command in cisco_show | Use cisco_configure for config changes |
| `Dangerous command blocked` | Command matches security blocklist | Review command; some operations forbidden for safety |

## Security Considerations

- **No plaintext storage**: Store credentials in encrypted vault or environment variables
- **SSH key support**: Prefer key-based auth over passwords when possible
- **Command validation**: All commands validated before execution
- **Dangerous operation blocking**: System commands (`reload`, `erase`) always rejected
- **Least privilege**: Use service accounts with minimal required permissions
- **Audit logging**: Enable SSH audit logging on network devices

## Troubleshooting

### "Device not reachable"

```bash
# From your local machine, verify SSH access
ssh admin@192.168.1.1 -p 22
```

### "ModuleNotFoundError: No module named 'scrapli'"

```bash
# Reinstall dependencies
uv sync --reinstall
```

### "Vault password incorrect"

```bash
# Verify vault password derivation
echo "claude-agent-vault-$(hostname)-$(id -u)"

# View encrypted file
VAULT_PASS="claude-agent-vault-$(hostname)-$(id -u)"
ansible-vault view ~/.claude/credentials/cisco-devices.vault.yaml \
  --vault-password-file=<(echo "$VAULT_PASS")
```

### Tests fail with "Connection refused"

Tests use mocked connections and don't require actual devices. Run with verbose output:

```bash
uv run pytest tests/ -v --tb=short
```

## Related Projects

- [mcp-network-common](https://github.com/rhuanssauro/mcp-network-common) — Shared utilities for network MCP servers
- [Scrapli Documentation](https://scrapli.readthedocs.io/) — SSH automation framework
- [MCP Specification](https://modelcontextprotocol.io/) — Model Context Protocol

## License

MIT License. See [LICENSE](./LICENSE) for details.

---

**Questions or Issues?**

- Check tests in `tests/` for usage examples
- Review `server.py` for available tools and parameters
- See AGENTS.md for Claude agent integration patterns
