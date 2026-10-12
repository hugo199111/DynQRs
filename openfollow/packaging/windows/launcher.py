# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Windows entry point with writable per-user state and a bundle self-check."""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is not available")
    return Path(base) / "OpenFollow"


def seed_config(directory: Path, resources: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "config.toml"
    if not target.exists():
        seed = (resources / "config.seed.toml").read_text(encoding="utf-8")
        with target.open("x", encoding="utf-8") as handle:
            handle.write(seed)
    return target


def self_check() -> dict[str, object]:
    """Verify imports, video plugins and the actual web templates."""
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    required = (
        "gtksink",
        "videotestsrc",
        "videoconvert",
        "appsink",
        "jpegenc",
        "jpegdec",
        "pngdec",
        "rtspsrc",
        "rtph264depay",
        "srtsrc",
        "avdec_h264",
    )
    if sys.platform == "win32":
        required += ("mfvideosrc",)
    missing = [name for name in required if Gst.ElementFactory.find(name) is None]
    if missing:
        raise RuntimeError(f"Missing GStreamer elements: {', '.join(missing)}")
    for name in ("openfollow.web.routes", "pypsn", "pygame", "multicast_expert", "rtmidi", "mido", "psutil"):
        importlib.import_module(name)
    from openfollow.video.inputs import get_registry

    registry = get_registry()
    for name in ("testpattern", "rtsp", "rtp", "srt", "ndi", "windows_camera"):
        if name not in registry:
            raise RuntimeError(f"Missing video input: {name}")
    template = resource_root() / "openfollow" / "web" / "templates" / "index.tpl"
    if not template.is_file():
        raise RuntimeError("Web templates are missing from the bundle")
    return {"ok": True, "platform": sys.platform, "elements": list(required), "inputs": sorted(registry)}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--self-check":
        try:
            report = self_check()
        except Exception as exc:
            report = {"ok": False, "error": str(exc)}
        if len(args) > 1:
            Path(args[1]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        if sys.stdout is not None:
            print(json.dumps(report))
        return 0 if report["ok"] else 1
    if args and args[0] == "--config":
        if len(args) != 2 or not Path(args[1]).is_file():
            raise ValueError("--config requires an existing configuration file")
        config = Path(args[1]).resolve()
        directory = config.parent
    else:
        directory = data_dir()
        config = seed_config(directory, resource_root())
    os.chdir(directory)
    sys.argv = [sys.argv[0], str(config)]
    from openfollow.main import main as run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
