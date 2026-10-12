# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Freeze OpenFollow and a GTK 3 / GStreamer prefix built for Windows x64."""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

repo = Path(SPECPATH).resolve().parents[1]
packaging = repo / "packaging" / "windows"
prefix = Path(os.environ["OPENFOLLOW_NATIVE_PREFIX"])
if not (prefix / "bin").is_dir():
    raise SystemExit("OPENFOLLOW_NATIVE_PREFIX must contain a built GTK 3 / GStreamer stack")

datas = collect_data_files("openfollow") + copy_metadata("openfollow")
datas.append((str(packaging / "config.seed.toml"), "."))
for directory in ("lib/girepository-1.0", "share", "etc"):
    path = prefix / directory
    if path.is_dir():
        datas.append((str(path), "native/" + directory))
binaries = [(str(path), "native/bin") for path in (prefix / "bin").glob("*.dll")]
query_loaders = prefix / "bin" / "gdk-pixbuf-query-loaders.exe"
if query_loaders.is_file():
    binaries.append((str(query_loaders), "native/bin"))
for path in (prefix / "lib" / "gdk-pixbuf-2.0").rglob("*.dll"):
    binaries.append((str(path), "native/" + str(path.parent.relative_to(prefix)).replace("\\", "/")))
plugin_dir = prefix / "lib" / "gstreamer-1.0"
binaries.extend((str(path), "native/lib/gstreamer-1.0") for path in plugin_dir.glob("*.dll"))
hiddenimports = collect_submodules("openfollow") + collect_submodules("mido.backends")
hiddenimports += [
    "rtmidi", "cairo", "gi.repository.Gtk", "gi.repository.Gdk", "gi.repository.GdkPixbuf",
    "gi.repository.GLib", "gi.repository.Gio", "gi.repository.Gst", "gi.repository.GstApp",
    "gi.repository.GstVideo", "gi.repository.Rsvg",
]
a = Analysis(
    [str(packaging / "launcher.py")], pathex=[str(repo)], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, runtime_hooks=[str(packaging / "runtime_hook.py")],
    hooksconfig={"gi": {"module-versions": {"Gtk": "3.0", "Gst": "1.0"}}},
    excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="OpenFollow", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="OpenFollow")
