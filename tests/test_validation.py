"""Tests for input validation functions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import _config_guardrails, _validate_show


class TestValidateShow:
    def test_valid_show_command(self):
        assert _validate_show("show version") is None

    def test_valid_show_ip_route(self):
        assert _validate_show("show ip route") is None

    def test_valid_show_interfaces(self):
        assert _validate_show("show interfaces status") is None

    def test_rejects_non_show_command(self):
        err = _validate_show("configure terminal")
        assert err is not None
        assert "Only 'show' commands" in err

    def test_rejects_ping_command(self):
        err = _validate_show("ping 8.8.8.8")
        assert err is not None
        assert "Only 'show' commands" in err

    def test_blocks_copy(self):
        err = _validate_show("show copy running-config")
        assert err is not None
        assert "copy" in err.lower()

    def test_blocks_delete(self):
        err = _validate_show("show delete flash:")
        assert err is not None
        assert "delete" in err.lower()

    def test_blocks_erase(self):
        err = _validate_show("show erase startup-config")
        assert err is not None
        assert "erase" in err.lower()

    def test_blocks_reload(self):
        err = _validate_show("show reload reason")
        assert err is not None
        assert "reload" in err.lower()

    def test_blocks_write(self):
        err = _validate_show("show write memory")
        assert err is not None
        assert "write" in err.lower()

    def test_blocks_configure(self):
        err = _validate_show("show configure terminal")
        assert err is not None
        assert "configure" in err.lower()

    def test_blocks_pipe(self):
        err = _validate_show("show version | include IOS")
        assert err is not None
        assert "Pipe" in err

    def test_blocks_redirect(self):
        err = _validate_show("show version > /tmp/out")
        assert err is not None
        assert "Pipe" in err

    def test_case_insensitive(self):
        assert _validate_show("SHOW VERSION") is None

    def test_whitespace_handling(self):
        assert _validate_show("  show version  ") is None


class TestConfigGuardrails:
    def test_valid_config(self):
        lines = ["interface GigabitEthernet0/0", "ip address 10.0.0.1 255.255.255.0"]
        assert _config_guardrails(lines) is None

    def test_blocks_write_erase(self):
        err = _config_guardrails(["write erase"])
        assert err is not None
        assert "write erase" in err

    def test_blocks_erase(self):
        err = _config_guardrails(["erase startup-config"])
        assert err is not None
        assert "erase" in err

    def test_blocks_reload(self):
        err = _config_guardrails(["reload"])
        assert err is not None
        assert "reload" in err

    def test_blocks_delete(self):
        err = _config_guardrails(["delete flash:vlan.dat"])
        assert err is not None
        assert "delete" in err

    def test_blocks_format(self):
        err = _config_guardrails(["format flash:"])
        assert err is not None
        assert "format" in err

    def test_allows_normal_commands(self):
        lines = [
            "hostname Router1",
            "interface Loopback0",
            "ip address 1.1.1.1 255.255.255.255",
            "router ospf 1",
            "network 10.0.0.0 0.0.0.255 area 0",
        ]
        assert _config_guardrails(lines) is None

    def test_blocks_dangerous_in_multiline(self):
        lines = [
            "interface GigabitEthernet0/0",
            "no shutdown",
            "reload",
        ]
        err = _config_guardrails(lines)
        assert err is not None
        assert "reload" in err
