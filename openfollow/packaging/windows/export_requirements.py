# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Separate locked Python wheels, VCS requirements and native GTK bindings."""

from __future__ import annotations

import sys
from pathlib import Path


def split_requirements(source: Path, target: Path, vcs: Path) -> None:
    ordinary: list[str] = []
    git: list[str] = []
    keep = True
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        if not line.startswith(" "):
            keep = not line.lower().startswith(("pygobject==", "pycairo=="))
            if " @ git+" in line:
                git.append(line)
                keep = False
        if keep:
            ordinary.append(line)
    target.write_text("".join(ordinary), encoding="utf-8")
    vcs.write_text("".join(git), encoding="utf-8")


if __name__ == "__main__":
    split_requirements(*(Path(arg) for arg in sys.argv[1:]))
