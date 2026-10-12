# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Start the real GUI, request the web interface and verify a rendered JPEG."""

from __future__ import annotations

import ctypes
import os
import select
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def capture_window(process: subprocess.Popen, env: dict[str, str], target: Path) -> None:
    """Capture the running application's window without generating an illustration."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        subprocess.run(
            [
                "gst-launch-1.0",
                "-q",
                "ximagesrc",
                "display-name=" + env["DISPLAY"],
                "use-damage=false",
                "show-pointer=false",
                "num-buffers=1",
                "!",
                "videoconvert",
                "!",
                "pngenc",
                "!",
                "filesink",
                "location=" + str(target),
            ],
            env=env,
            check=True,
            timeout=15,
        )
        return
    from ctypes import wintypes

    from PIL import ImageGrab

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    windows = []
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    @callback_type
    def visit(hwnd, _param):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    if not user32.EnumWindows(visit, 0) or not windows:
        raise RuntimeError("Could not find the running OpenFollow window")
    screenshot = ImageGrab.grab(window=windows[0])
    if screenshot.width < 320 or screenshot.height < 200:
        raise RuntimeError("Application window screenshot is unexpectedly small")
    if all(low == high for low, high in screenshot.convert("RGB").getextrema()):
        raise RuntimeError("Application window screenshot is blank")
    screenshot.save(target)


def smoke(executable: Path, screenshot: Path | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="openfollow-smoke-") as temp:
        root = Path(temp)
        env = dict(os.environ)
        display = None
        app = None
        with (root / "startup.log").open("w+") as log:
            try:
                if os.name != "nt" and not env.get("DISPLAY"):
                    display = subprocess.Popen(
                        ["Xvfb", "-displayfd", "1", "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
                        stdout=subprocess.PIPE,
                        stderr=log,
                        text=True,
                    )
                    assert display.stdout is not None
                    if not select.select([display.stdout], [], [], 10)[0]:
                        raise RuntimeError("Xvfb did not start")
                    number = display.stdout.readline().strip()
                    if not number.isdigit():
                        raise RuntimeError("Xvfb did not provide a display number")
                    env["DISPLAY"] = ":" + number
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", 0))
                    port = probe.getsockname()[1]
                config = root / "config.toml"
                config.write_text(
                    f'web_port = {port}\nweb_bind = "127.0.0.1"\nvideo_source_type = "testpattern"\n'
                    "auto_update_check = false\nauto_time_sync = false\n",
                    encoding="utf-8",
                )
                command = (
                    [str(executable), "--config", str(config)]
                    if executable.suffix.lower() == ".exe"
                    else [
                        str(executable),
                        "-m",
                        "openfollow.main",
                        str(config),
                    ]
                )
                app = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log)
                # Local readiness requests must bypass any outbound HTTPS proxy.
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    if app.poll() is not None:
                        raise RuntimeError(f"Application exited with status {app.returncode}")
                    try:
                        with opener.open(f"http://127.0.0.1:{port}/", timeout=2) as response:
                            html = response.read()
                        with opener.open(f"http://127.0.0.1:{port}/api/video/snapshot", timeout=2) as response:
                            mime = response.headers.get_content_type()
                            jpeg = response.read()
                        if b"OpenFollow" in html and mime == "image/jpeg" and jpeg.startswith(b"\xff\xd8\xff"):
                            if screenshot is not None:
                                capture_window(app, env, screenshot)
                            print(f"GUI smoke OK: web page and JPEG frame ({len(jpeg)} bytes)")
                            return
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(0.25)
                raise RuntimeError("Application did not serve its web interface and a video frame")
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                if app is not None:
                    stop(app)
                if display is not None:
                    stop(display)


if __name__ == "__main__":
    screenshot = Path(sys.argv[2]).absolute() if len(sys.argv) > 2 else None
    smoke(Path(sys.argv[1]).absolute(), screenshot)
