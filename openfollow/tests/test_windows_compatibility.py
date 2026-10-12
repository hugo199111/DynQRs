# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Regression checks for Windows startup, configuration and network pinning."""

from __future__ import annotations

import importlib.util
import json
import socket
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from openfollow import net_egress, net_utils, windows_network
from openfollow.runtime import app_modes, app_orchestration

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1]


def load_launcher():
    spec = importlib.util.spec_from_file_location("windows_launcher", ROOT / "packaging/windows/launcher.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_application_imports_without_unix_account_modules() -> None:
    code = """
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in ('pwd', 'grp'):
        raise ModuleNotFoundError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import openfollow.web.routes
import openfollow.privilege.device_repair
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_config_survives_a_second_launch(tmp_path: Path) -> None:
    launcher = load_launcher()
    resources = ROOT / "packaging/windows"
    target = launcher.seed_config(tmp_path / "user data", resources)
    assert "testpattern" in target.read_text()
    target.write_text("web_port = 9999\n", encoding="utf-8")
    launcher.seed_config(target.parent, resources)
    assert target.read_text() == "web_port = 9999\n"


def test_configuration_uses_localappdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    launcher = load_launcher()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert launcher.data_dir() == tmp_path / "OpenFollow"


def test_failed_bundle_self_check_has_nonzero_exit_and_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    launcher = load_launcher()

    def fail():
        raise RuntimeError("gtksink missing")

    monkeypatch.setattr(launcher, "self_check", fail)
    report = tmp_path / "result.json"
    assert launcher.main(["--self-check", str(report)]) == 1
    assert json.loads(report.read_text()) == {"ok": False, "error": "gtksink missing"}


def test_windows_loop_does_not_require_unix_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    import gi.repository

    calls = []
    glib = SimpleNamespace(timeout_add=lambda *args: calls.append(args))
    gtk = SimpleNamespace(main=lambda: calls.append("main"))
    monkeypatch.setattr(gi.repository, "GLib", glib, raising=False)
    monkeypatch.setattr(gi.repository, "Gtk", gtk, raising=False)
    monkeypatch.setattr(app_orchestration.sys, "platform", "win32")
    app = SimpleNamespace(
        _canvas=SimpleNamespace(start_hud_tick=lambda: calls.append("tick")),
        _runtime_services=SimpleNamespace(shutdown=lambda: calls.append("shutdown")),
        _run_frame=lambda: True,
        _run_housekeeping=lambda: True,
    )
    app_orchestration.run_native_loop(app)
    assert calls[0] == "tick"
    assert calls[-2:] == ["main", "shutdown"]


def test_windows_opens_the_current_web_server_in_default_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    import webbrowser

    from openfollow.runtime import webkit_browser

    opened = []
    monkeypatch.setattr(app_modes.sys, "platform", "win32")
    monkeypatch.setattr(webkit_browser, "build_url", lambda *args, **kwargs: "http://127.0.0.1:8080")
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url) or True)
    app_modes.open_web_ui_external(SimpleNamespace(_config=object()))
    assert opened == ["http://127.0.0.1:8080"]


class RecordingSocket:
    def __init__(self):
        self.calls = []

    def setsockopt(self, level, option, value):
        self.calls.append((level, option, value))

    def bind(self, address):
        self.calls.append(address)


def test_windows_unicast_uses_interface_index_in_network_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(windows_network, "interface_index", lambda name: 27)
    sock = RecordingSocket()
    net_egress.pin_socket_egress(sock, net_egress.Egress("Ethernet", "192.0.2.10"), platform="win32")
    assert sock.calls == [(socket.IPPROTO_IP, 31, struct.pack("!I", 27)), ("192.0.2.10", 0)]


def test_windows_multicast_uses_winsock_address_structures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net_utils.sys, "platform", "win32")
    monkeypatch.setattr(windows_network, "interface_index", lambda name: 27)
    sock = RecordingSocket()
    net_utils.bind_multicast_send_iface(sock, "192.0.2.10", "Ethernet")
    net_utils.join_multicast_group_on_iface(sock, "239.255.0.1", "192.0.2.10", "Ethernet")
    assert sock.calls == [
        (socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("192.0.2.10")),
        (socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton("239.255.0.1") + socket.inet_aton("192.0.2.10")),
    ]


def test_windows_missing_interface_stays_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(name):
        raise net_utils.InterfaceUnavailable("adapter removed")

    monkeypatch.setattr(windows_network, "interface_index", missing)
    sock = RecordingSocket()
    with pytest.raises(net_utils.InterfaceUnavailable, match="adapter removed"):
        net_egress.pin_socket_egress(sock, net_egress.Egress("Ethernet", "192.0.2.10"), platform="win32")
    assert sock.calls == []
