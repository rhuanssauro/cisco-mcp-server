#!/usr/bin/env python3
"""Cisco MCP Server - Direct device access via Scrapli.

Provides MCP tools for interacting with Cisco IOS-XE, IOS-XR, and NX-OS
devices using Scrapli for SSH transport. Supports show commands, configuration,
ping, and multi-vendor operation.
"""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp_network_common import (
    CommandValidator,
    create_scrapli_conn,
    error_response,
    get_device,
    handle_ssh_errors,
    load_inventory,
    ok_response,
    setup_logger,
)

load_dotenv()

logger = setup_logger("CiscoMCPServer")
mcp = FastMCP("Cisco Network Tools")

DEVICES: dict[str, dict[str, Any]] = {}

_PLATFORM_MAP = {
    "iosxe": "cisco_iosxe",
    "iosxr": "cisco_iosxr",
    "nxos": "cisco_nxos",
    "ios": "cisco_iosxe",
}

load_inventory("CISCO", DEVICES, default_fields={"platform": "iosxe"})

validator = CommandValidator()


async def _get_conn(device_name: str):
    """Create an AsyncScrapli connection to the named device."""
    dev = get_device(device_name, DEVICES)
    platform = _PLATFORM_MAP.get(dev.get("platform", "iosxe"), "cisco_iosxe")
    return await create_scrapli_conn(dev, platform=platform)


@mcp.tool()
async def cisco_list_devices() -> str:
    """List all Cisco devices in the inventory."""
    result = {
        name: {
            "host": dev["host"],
            "platform": dev.get("platform", "iosxe"),
            "port": dev.get("port", 22),
        }
        for name, dev in DEVICES.items()
    }
    return ok_response(devices=result)


@mcp.tool()
@handle_ssh_errors
async def cisco_show(device_name: str, command: str) -> str:
    """Execute a show command on a Cisco device.

    Args:
        device_name: Name of the device from inventory
        command: Show command to execute (must start with 'show')
    """
    err = validator.validate_readonly(command)
    if err:
        return error_response(err)

    conn = await _get_conn(device_name)
    try:
        response = await conn.send_command(command)
        return ok_response(device=device_name, command=command, output=response.result)
    finally:
        conn.close()


@mcp.tool()
@handle_ssh_errors
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
        return error_response("No config commands provided.")

    err = validator.validate_config(lines)
    if err:
        return error_response(err)

    conn = await _get_conn(device_name)
    try:
        response = await conn.send_configs(lines)
        return ok_response(
            device=device_name, commands_applied=lines, output=response.result
        )
    finally:
        conn.close()


@mcp.tool()
@handle_ssh_errors
async def cisco_ping(device_name: str, target: str, count: int = 5) -> str:
    """Execute a ping from a Cisco device to a target.

    Args:
        device_name: Name of the device from inventory
        target: IP address or hostname to ping
        count: Number of ping packets (default 5)
    """
    command = f"ping {target} repeat {count}"
    conn = await _get_conn(device_name)
    try:
        response = await conn.send_command(command, timeout_ops=120)
        return ok_response(device=device_name, target=target, output=response.result)
    finally:
        conn.close()


@mcp.tool()
@handle_ssh_errors
async def cisco_get_running_config(device_name: str, section: str = "") -> str:
    """Get running configuration from a Cisco device.

    Args:
        device_name: Name of the device from inventory
        section: Optional section filter (e.g., 'interface', 'router ospf')
    """
    command = "show running-config"
    if section:
        command = f"show running-config | section {section}"

    conn = await _get_conn(device_name)
    try:
        response = await conn.send_command(command)
        return ok_response(device=device_name, command=command, output=response.result)
    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("Starting Cisco MCP Server...")
    mcp.run()
