"""Tests for server instantiation and tool registration."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import _PLATFORM_MAP, mcp


class TestServerRegistration:
    def test_mcp_server_created(self):
        assert mcp.name == "Cisco Network Tools"

    def test_tool_count(self):
        tools = mcp._tool_manager._tools
        assert len(tools) == 5

    def test_expected_tools_registered(self):
        tools = mcp._tool_manager._tools
        expected = {
            "cisco_list_devices",
            "cisco_show",
            "cisco_configure",
            "cisco_ping",
            "cisco_get_running_config",
        }
        assert set(tools.keys()) == expected


class TestPlatformMap:
    def test_iosxe_mapping(self):
        assert _PLATFORM_MAP["iosxe"] == "cisco_iosxe"

    def test_iosxr_mapping(self):
        assert _PLATFORM_MAP["iosxr"] == "cisco_iosxr"

    def test_nxos_mapping(self):
        assert _PLATFORM_MAP["nxos"] == "cisco_nxos"

    def test_ios_defaults_to_iosxe(self):
        assert _PLATFORM_MAP["ios"] == "cisco_iosxe"
