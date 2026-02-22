"""Tests for MCP tool handlers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapli.exceptions import (
    ScrapliAuthenticationFailed,
    ScrapliConnectionError,
    ScrapliTimeout,
)

from server import (
    cisco_configure,
    cisco_get_running_config,
    cisco_list_devices,
    cisco_ping,
    cisco_show,
)


@pytest.mark.asyncio
class TestCiscoListDevices:
    async def test_list_devices_empty(self, monkeypatch):
        import server

        monkeypatch.setattr(server, "DEVICES", {})
        result = json.loads(await cisco_list_devices())
        assert result["status"] == "ok"
        assert result["devices"] == {}

    async def test_list_devices_populated(self, mock_devices):
        result = json.loads(await cisco_list_devices())
        assert result["status"] == "ok"
        assert "router1" in result["devices"]
        assert result["devices"]["router1"]["host"] == "192.168.1.1"
        assert result["devices"]["router1"]["platform"] == "iosxe"


@pytest.mark.asyncio
class TestCiscoShow:
    @patch("server._get_conn")
    async def test_show_success(self, mock_get_conn, mock_devices, mock_scrapli_conn):
        mock_get_conn.return_value = mock_scrapli_conn
        mock_scrapli_conn.send_command.return_value.result = (
            "Cisco IOS XE Software, Version 17.06.05"
        )

        result = json.loads(await cisco_show("router1", "show version"))
        assert result["status"] == "ok"
        assert result["device"] == "router1"
        assert "17.06.05" in result["output"]
        mock_scrapli_conn.close.assert_called_once()

    async def test_show_rejects_non_show(self, mock_devices):
        result = json.loads(await cisco_show("router1", "configure terminal"))
        assert result["status"] == "error"
        assert "Only 'show' commands" in result["error"]

    async def test_show_rejects_pipe(self, mock_devices):
        result = json.loads(await cisco_show("router1", "show version | include IOS"))
        assert result["status"] == "error"
        assert "Pipe" in result["error"]

    @patch("server._get_conn")
    async def test_show_auth_failed(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliAuthenticationFailed("bad creds")
        result = json.loads(await cisco_show("router1", "show version"))
        assert result["status"] == "error"
        assert "Authentication failed" in result["error"]

    @patch("server._get_conn")
    async def test_show_connection_error(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliConnectionError("unreachable")
        result = json.loads(await cisco_show("router1", "show version"))
        assert result["status"] == "error"
        assert "Connection error" in result["error"]

    @patch("server._get_conn")
    async def test_show_timeout(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliTimeout("timed out")
        result = json.loads(await cisco_show("router1", "show version"))
        assert result["status"] == "error"
        assert "Connection error" in result["error"]

    @patch("server._get_conn")
    async def test_show_unknown_device(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ValueError("Device 'bogus' not in inventory")
        result = json.loads(await cisco_show("bogus", "show version"))
        assert result["status"] == "error"
        assert "not in inventory" in result["error"]


@pytest.mark.asyncio
class TestCiscoConfigure:
    @patch("server._get_conn")
    async def test_configure_success(
        self, mock_get_conn, mock_devices, mock_scrapli_conn
    ):
        mock_get_conn.return_value = mock_scrapli_conn
        result = json.loads(
            await cisco_configure(
                "router1", "interface Loopback0\nip address 1.1.1.1 255.255.255.255"
            )
        )
        assert result["status"] == "ok"
        assert len(result["commands_applied"]) == 2
        mock_scrapli_conn.send_configs.assert_called_once()
        mock_scrapli_conn.close.assert_called_once()

    async def test_configure_empty_commands(self, mock_devices):
        result = json.loads(await cisco_configure("router1", ""))
        assert result["status"] == "error"
        assert "No config commands" in result["error"]

    async def test_configure_strips_conf_t(self, mock_devices):
        with patch("server._get_conn") as mock_get_conn:
            conn = MagicMock()
            conn.open = AsyncMock()
            conn.close = MagicMock()
            response = MagicMock()
            response.result = ""
            conn.send_configs = AsyncMock(return_value=response)
            mock_get_conn.return_value = conn

            result = json.loads(
                await cisco_configure(
                    "router1",
                    "configure terminal\nhostname R1\nend",
                )
            )
            assert result["status"] == "ok"
            assert result["commands_applied"] == ["hostname R1"]

    async def test_configure_blocks_reload(self, mock_devices):
        result = json.loads(await cisco_configure("router1", "interface Gi0/0\nreload"))
        assert result["status"] == "error"
        assert "reload" in result["error"]

    @patch("server._get_conn")
    async def test_configure_auth_failed(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliAuthenticationFailed("bad creds")
        result = json.loads(await cisco_configure("router1", "hostname TestRouter"))
        assert result["status"] == "error"
        assert "Authentication failed" in result["error"]


@pytest.mark.asyncio
class TestCiscoPing:
    @patch("server._get_conn")
    async def test_ping_success(self, mock_get_conn, mock_devices, mock_scrapli_conn):
        mock_get_conn.return_value = mock_scrapli_conn
        mock_scrapli_conn.send_command.return_value.result = (
            "Success rate is 100 percent (5/5)"
        )
        result = json.loads(await cisco_ping("router1", "8.8.8.8"))
        assert result["status"] == "ok"
        assert "100 percent" in result["output"]
        mock_scrapli_conn.close.assert_called_once()

    @patch("server._get_conn")
    async def test_ping_with_count(
        self, mock_get_conn, mock_devices, mock_scrapli_conn
    ):
        mock_get_conn.return_value = mock_scrapli_conn
        await cisco_ping("router1", "10.0.0.1", count=10)
        call_args = mock_scrapli_conn.send_command.call_args
        assert "repeat 10" in call_args[0][0]

    @patch("server._get_conn")
    async def test_ping_connection_error(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliConnectionError("unreachable")
        result = json.loads(await cisco_ping("router1", "8.8.8.8"))
        assert result["status"] == "error"
        assert "Connection error" in result["error"]


@pytest.mark.asyncio
class TestCiscoGetRunningConfig:
    @patch("server._get_conn")
    async def test_get_running_config_full(
        self, mock_get_conn, mock_devices, mock_scrapli_conn
    ):
        mock_get_conn.return_value = mock_scrapli_conn
        mock_scrapli_conn.send_command.return_value.result = (
            "hostname Router1\n!\ninterface GigabitEthernet0/0"
        )
        result = json.loads(await cisco_get_running_config("router1"))
        assert result["status"] == "ok"
        assert result["command"] == "show running-config"
        assert "hostname" in result["output"]

    @patch("server._get_conn")
    async def test_get_running_config_section(
        self, mock_get_conn, mock_devices, mock_scrapli_conn
    ):
        mock_get_conn.return_value = mock_scrapli_conn
        result = json.loads(
            await cisco_get_running_config("router1", section="interface")
        )
        assert result["status"] == "ok"
        assert "section interface" in result["command"]

    @patch("server._get_conn")
    async def test_get_running_config_auth_failed(self, mock_get_conn, mock_devices):
        mock_get_conn.side_effect = ScrapliAuthenticationFailed("denied")
        result = json.loads(await cisco_get_running_config("router1"))
        assert result["status"] == "error"
        assert "Authentication failed" in result["error"]
