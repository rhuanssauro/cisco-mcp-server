#!/usr/bin/env python3
"""Cisco MCP Server - Direct device access via Scrapli.

Provides MCP tools for interacting with Cisco IOS-XE, IOS-XR, and NX-OS
devices using Scrapli for SSH transport. Supports show commands, configuration,
ping, and multi-vendor operation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from scrapli import AsyncScrapli
from scrapli.exceptions import (
    ScrapliAuthenticationFailed,
    ScrapliConnectionError,
    ScrapliTimeout,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("CiscoMCPServer")

mcp = FastMCP("Cisco Network Tools")

# Device inventory from environment
DEVICES: dict[str, dict[str, Any]] = {}

_PLATFORM_MAP = {
    "iosxe": "cisco_iosxe",
    "iosxr": "cisco_iosxr",
    "nxos": "cisco_nxos",
    "ios": "cisco_iosxe",
}


def _load_inventory() -> None:
    """Load device inventory from CISCO_DEVICES_JSON env var or individual vars."""
    global DEVICES

    json_path = os.getenv("CISCO_DEVICES_JSON")
    if json_path and os.path.exists(json_path):
        with open(json_path) as f:
            DEVICES.update(json.load(f))
        logger.info(f"Loaded {len(DEVICES)} devices from {json_path}")
        return

    # Fallback: single device from env vars
    host = os.getenv("CISCO_HOST")
    if host:
        DEVICES["default"] = {
            "host": host,
            "username": os.getenv("CISCO_USER", "admin"),
            "password": os.getenv("CISCO_PASS", ""),
            "platform": os.getenv("CISCO_PLATFORM", "iosxe"),
            "port": int(os.getenv("CISCO_PORT", "22")),
        }
        logger.info(f"Loaded single device: {host}")


_load_inventory()

SHOW_BLOCK_WORDS = {"copy", "delete", "erase", "reload", "write", "configure", "conf"}


def _validate_show(command: str) -> str | None:
    cmd = command.strip().lower()
    if not cmd.startswith("show"):
        return f"Only 'show' commands allowed. Got: '{command}'"
    tokens = re.findall(r"[a-zA-Z0-9_-]+", cmd)
    for t in tokens:
        if t in SHOW_BLOCK_WORDS:
            return f"Blocked term '{t}' in show command."
    if any(c in cmd for c in ["|", ">", "<"]):
        return "Pipe/redirect characters not allowed."
    return None


def _config_guardrails(lines: list[str]) -> str | None:
    joined = "\n".join(lines).lower()
    for pattern, label in [
        (r"\bwrite\s+erase\b", "write erase"),
        (r"^\s*erase\b", "erase"),
        (r"\breload\b", "reload"),
        (r"\bdelete\b", "delete"),
        (r"\bformat\b", "format"),
    ]:
        if re.search(pattern, joined, flags=re.MULTILINE):
            return f"Dangerous command blocked: '{label}'"
    return None


async def _get_conn(device_name: str) -> AsyncScrapli:
    """Create an AsyncScrapli connection to the named device."""
    if device_name not in DEVICES:
        raise ValueError(
            f"Device '{device_name}' not in inventory. "
            f"Available: {list(DEVICES.keys())}"
        )

    dev = DEVICES[device_name]
    platform = _PLATFORM_MAP.get(dev.get("platform", "iosxe"), "cisco_iosxe")

    conn = AsyncScrapli(
        host=dev["host"],
        auth_username=dev.get("username", "admin"),
        auth_password=dev.get("password", ""),
        platform=platform,
        port=dev.get("port", 22),
        auth_strict_key=False,
        transport="asyncssh",
        timeout_socket=30,
        timeout_transport=30,
        timeout_ops=60,
    )
    await conn.open()
    return conn


@mcp.tool()
async def cisco_list_devices() -> str:
    """List all Cisco devices in the inventory."""
    result = {}
    for name, dev in DEVICES.items():
        result[name] = {
            "host": dev["host"],
            "platform": dev.get("platform", "iosxe"),
            "port": dev.get("port", 22),
        }
    return json.dumps({"status": "ok", "devices": result}, indent=2)


@mcp.tool()
async def cisco_show(device_name: str, command: str) -> str:
    """Execute a show command on a Cisco device.

    Args:
        device_name: Name of the device from inventory
        command: Show command to execute (must start with 'show')
    """
    err = _validate_show(command)
    if err:
        return json.dumps({"status": "error", "error": err})

    try:
        conn = await _get_conn(device_name)
        try:
            response = await conn.send_command(command)
            return json.dumps(
                {
                    "status": "ok",
                    "device": device_name,
                    "command": command,
                    "output": response.result,
                },
                indent=2,
            )
        finally:
            conn.close()
    except ScrapliAuthenticationFailed as e:
        logger.error(f"Auth failed on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Authentication failed: {e}"})
    except (ScrapliConnectionError, ScrapliTimeout) as e:
        logger.error(f"Connection error on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Connection error: {e}"})
    except Exception as e:
        logger.error(f"Error on {device_name}: {e}", exc_info=True)
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
async def cisco_configure(device_name: str, config_commands: str) -> str:
    """Apply configuration commands to a Cisco device.

    Args:
        device_name: Name of the device from inventory
        config_commands: Configuration lines (newline-separated string).
            Do NOT include 'configure terminal' or 'end' - handled automatically.
    """
    lines = [
        line.rstrip()
        for line in config_commands.strip().splitlines()
        if line.strip()
        and line.strip().lower() not in {"configure terminal", "conf t", "end"}
    ]

    if not lines:
        return json.dumps({"status": "error", "error": "No config commands provided."})

    err = _config_guardrails(lines)
    if err:
        return json.dumps({"status": "error", "error": err})

    try:
        conn = await _get_conn(device_name)
        try:
            response = await conn.send_configs(lines)
            return json.dumps(
                {
                    "status": "ok",
                    "device": device_name,
                    "commands_applied": lines,
                    "output": response.result,
                },
                indent=2,
            )
        finally:
            conn.close()
    except ScrapliAuthenticationFailed as e:
        logger.error(f"Auth failed on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Authentication failed: {e}"})
    except (ScrapliConnectionError, ScrapliTimeout) as e:
        logger.error(f"Connection error on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Connection error: {e}"})
    except Exception as e:
        logger.error(f"Config error on {device_name}: {e}", exc_info=True)
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
async def cisco_ping(device_name: str, target: str, count: int = 5) -> str:
    """Execute a ping from a Cisco device to a target.

    Args:
        device_name: Name of the device from inventory
        target: IP address or hostname to ping
        count: Number of ping packets (default 5)
    """
    command = f"ping {target} repeat {count}"
    try:
        conn = await _get_conn(device_name)
        try:
            response = await conn.send_command(command, timeout_ops=120)
            return json.dumps(
                {
                    "status": "ok",
                    "device": device_name,
                    "target": target,
                    "output": response.result,
                },
                indent=2,
            )
        finally:
            conn.close()
    except ScrapliAuthenticationFailed as e:
        logger.error(f"Auth failed on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Authentication failed: {e}"})
    except (ScrapliConnectionError, ScrapliTimeout) as e:
        logger.error(f"Connection error on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Connection error: {e}"})
    except Exception as e:
        logger.error(f"Ping error on {device_name}: {e}", exc_info=True)
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
async def cisco_get_running_config(device_name: str, section: str = "") -> str:
    """Get running configuration from a Cisco device.

    Args:
        device_name: Name of the device from inventory
        section: Optional section filter (e.g., 'interface', 'router ospf')
    """
    command = "show running-config"
    if section:
        command = f"show running-config | section {section}"

    try:
        conn = await _get_conn(device_name)
        try:
            response = await conn.send_command(command)
            return json.dumps(
                {
                    "status": "ok",
                    "device": device_name,
                    "command": command,
                    "output": response.result,
                },
                indent=2,
            )
        finally:
            conn.close()
    except ScrapliAuthenticationFailed as e:
        logger.error(f"Auth failed on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Authentication failed: {e}"})
    except (ScrapliConnectionError, ScrapliTimeout) as e:
        logger.error(f"Connection error on {device_name}: {e}")
        return json.dumps({"status": "error", "error": f"Connection error: {e}"})
    except Exception as e:
        logger.error(f"Config fetch error on {device_name}: {e}", exc_info=True)
        return json.dumps({"status": "error", "error": str(e)})


if __name__ == "__main__":
    logger.info("Starting Cisco MCP Server...")
    mcp.run()
