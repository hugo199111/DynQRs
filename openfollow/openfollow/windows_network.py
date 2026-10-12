# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Resolve Windows adapter aliases to indices for Winsock interface pinning."""

from __future__ import annotations

import ctypes

from openfollow.net_utils import InterfaceUnavailable


def interface_index(alias: str) -> int:
    """Resolve a psutil adapter name through the Windows IP Helper API."""
    api = ctypes.WinDLL("iphlpapi.dll")  # type: ignore[attr-defined]
    luid = ctypes.c_uint64()
    index = ctypes.c_uint32()
    to_luid = api.ConvertInterfaceAliasToLuid
    to_luid.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint64)]
    to_luid.restype = ctypes.c_uint32
    to_index = api.ConvertInterfaceLuidToIndex
    to_index.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint32)]
    to_index.restype = ctypes.c_uint32
    status = to_luid(alias, ctypes.byref(luid))
    if not status:
        status = to_index(ctypes.byref(luid), ctypes.byref(index))
    if status or not index.value:
        raise InterfaceUnavailable(f"Windows interface {alias!r} is unavailable (status {status})")
    return int(index.value)
