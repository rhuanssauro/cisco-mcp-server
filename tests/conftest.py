"""Shared test fixtures for cisco-mcp-server tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def mock_devices(monkeypatch):
    """Populate DEVICES inventory with test entries."""
    import server

    test_devices = {
        "router1": {
            "host": "192.168.1.1",
            "username": "admin",
            "password": "secret",
            "platform": "iosxe",
            "port": 22,
        },
        "switch1": {
            "host": "192.168.1.2",
            "username": "admin",
            "password": "secret",
            "platform": "nxos",
            "port": 22,
        },
    }
    monkeypatch.setattr(server, "DEVICES", test_devices)
    return test_devices


@pytest.fixture()
def mock_scrapli_conn():
    """Create a mock AsyncScrapli connection with send_command/send_configs."""
    conn = MagicMock()
    conn.open = AsyncMock()
    conn.close = MagicMock()

    response = MagicMock()
    response.result = "mock output"
    conn.send_command = AsyncMock(return_value=response)
    conn.send_configs = AsyncMock(return_value=response)
    return conn
