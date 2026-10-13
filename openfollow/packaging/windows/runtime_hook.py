# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Resolve native libraries and plugin data inside the Windows bundle."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_DLL_HANDLES = []


def _write_cache(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _loader_cache(query: Path, loader_dir: Path, cache: Path) -> Path:
    loaders = sorted(loader_dir.glob("*.dll"))
    libraries = sorted(query.parent.glob("*pixbuf*.dll"))
    fingerprint = hashlib.sha256(str(query.resolve()).encode())
    for path in [query, *libraries, *loaders]:
        stat = path.stat()
        fingerprint.update(f"\n{path}:{stat.st_size}:{stat.st_mtime_ns}".encode())
    destination = cache / f"pixbuf-loaders-{fingerprint.hexdigest()[:24]}.cache"
    if not destination.is_file() or destination.stat().st_size == 0:
        data = _bundled_loader_data(query, loaders)
        if data is None:
            result = subprocess.run(
                [str(query), *(str(path) for path in loaders)], check=True, capture_output=True
            )
            data = result.stdout
        _write_cache(destination, data)
    return destination


def _bundled_loader_data(query: Path, loaders: list[Path]) -> bytes | None:
    native = query.parent.parent
    try:
        metadata = json.loads((native.parent / "pixbuf-loaders.json").read_text(encoding="utf-8"))
        if metadata["version"] != 1:
            return None
        expected = {str(native / relative) for relative in metadata["modules"].values()}
        if expected != {str(path) for path in loaders}:
            return None
        for relative, expected_hash in metadata["files"].items():
            with (native / relative).open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected_hash:
                    return None
        data = metadata["template"]
        for marker, relative in metadata["modules"].items():
            data = data.replace(marker, json.dumps(str(native / relative), ensure_ascii=False))
        return data.encode("utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        return None


def configure(root: Path, cache: Path) -> None:
    native = root / "native"
    binary_dir = native / "bin"
    # Native helper executables also need PyInstaller's collected runtime
    # DLLs at the bundle root, especially on a machine without VC++ tools.
    os.environ["PATH"] = os.pathsep.join((str(binary_dir), str(root), os.environ.get("PATH", "")))
    if hasattr(os, "add_dll_directory"):
        _DLL_HANDLES.append(os.add_dll_directory(str(binary_dir)))
    os.environ["GI_TYPELIB_PATH"] = str(native / "lib" / "girepository-1.0")
    plugins = str(native / "lib" / "gstreamer-1.0")
    for name in ("GST_PLUGIN_PATH", "GST_PLUGIN_PATH_1_0", "GST_PLUGIN_SYSTEM_PATH", "GST_PLUGIN_SYSTEM_PATH_1_0"):
        os.environ[name] = plugins
    cache.mkdir(parents=True, exist_ok=True)
    # Separate installs must not invalidate each other's absolute plugin paths.
    installation = hashlib.sha256(os.path.normcase(str(native.resolve())).encode()).hexdigest()[:24]
    registry = cache / f"gstreamer-{installation}.registry.bin"
    previous_registry = cache / "gstreamer.registry.bin"
    if not registry.exists() and previous_registry.is_file():
        try:
            _write_cache(registry, previous_registry.read_bytes())
        except OSError:
            pass  # GStreamer rebuilds a missing or incompatible registry.
    os.environ["GST_REGISTRY_1_0"] = str(registry)
    os.environ["GST_REGISTRY_FORK"] = "no"
    os.environ["GSETTINGS_SCHEMA_DIR"] = str(native / "share" / "glib-2.0" / "schemas")
    os.environ["XDG_DATA_DIRS"] = str(native / "share")
    os.environ["GTK_EXE_PREFIX"] = str(native)
    # Native Windows decorations bypass the canvas pointer handlers.
    os.environ["GTK_CSD"] = "0"
    os.environ["FONTCONFIG_PATH"] = str(native / "etc" / "fonts")
    os.environ["OPENFOLLOW_NETWORK_BACKEND"] = "psutil"
    loader_dirs = list((native / "lib" / "gdk-pixbuf-2.0").glob("*/loaders"))
    query = binary_dir / "gdk-pixbuf-query-loaders.exe"
    if loader_dirs and query.is_file():
        loader_dir = loader_dirs[0]
        os.environ["GDK_PIXBUF_MODULEDIR"] = str(loader_dir)
        os.environ["GDK_PIXBUF_MODULE_FILE"] = str(_loader_cache(query, loader_dir, cache))


if getattr(sys, "frozen", False):
    configure(Path(sys._MEIPASS), Path(os.environ["LOCALAPPDATA"]) / "OpenFollow" / "cache")
