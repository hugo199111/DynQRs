# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Resolve native libraries and plugin data inside the Windows bundle."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DLL_HANDLES = []


def configure(root: Path, cache: Path) -> None:
    native = root / "native"
    binary_dir = native / "bin"
    os.environ["PATH"] = str(binary_dir) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        _DLL_HANDLES.append(os.add_dll_directory(str(binary_dir)))
    os.environ["GI_TYPELIB_PATH"] = str(native / "lib" / "girepository-1.0")
    plugins = str(native / "lib" / "gstreamer-1.0")
    for name in ("GST_PLUGIN_PATH", "GST_PLUGIN_PATH_1_0", "GST_PLUGIN_SYSTEM_PATH", "GST_PLUGIN_SYSTEM_PATH_1_0"):
        os.environ[name] = plugins
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["GST_REGISTRY_1_0"] = str(cache / "gstreamer.registry.bin")
    os.environ["GST_REGISTRY_FORK"] = "no"
    os.environ["GSETTINGS_SCHEMA_DIR"] = str(native / "share" / "glib-2.0" / "schemas")
    os.environ["XDG_DATA_DIRS"] = str(native / "share")
    os.environ["GTK_EXE_PREFIX"] = str(native)
    os.environ["FONTCONFIG_PATH"] = str(native / "etc" / "fonts")
    os.environ["OPENFOLLOW_NETWORK_BACKEND"] = "psutil"
    loader_dirs = list((native / "lib" / "gdk-pixbuf-2.0").glob("*/loaders"))
    query = binary_dir / "gdk-pixbuf-query-loaders.exe"
    if loader_dirs and query.is_file():
        loader_dir = loader_dirs[0]
        os.environ["GDK_PIXBUF_MODULEDIR"] = str(loader_dir)
        result = subprocess.run(
            [str(query), *(str(path) for path in loader_dir.glob("*.dll"))], check=True, capture_output=True
        )
        loader_cache = cache / "pixbuf-loaders.cache"
        loader_cache.write_bytes(result.stdout)
        os.environ["GDK_PIXBUF_MODULE_FILE"] = str(loader_cache)


if getattr(sys, "frozen", False):
    configure(Path(sys._MEIPASS), Path(os.environ["LOCALAPPDATA"]) / "OpenFollow" / "cache")
