# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Build relocatable GdkPixbuf loader metadata for the Windows bundle."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def main() -> None:
    prefix = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2])
    query = prefix / "bin" / "gdk-pixbuf-query-loaders.exe"
    directories = sorted((prefix / "lib" / "gdk-pixbuf-2.0").glob("*/loaders"))
    loaders = sorted(directories[0].glob("*.dll")) if directories else []
    result = subprocess.run(
        [str(query), *(str(path) for path in loaders)], check=True, capture_output=True
    )
    template = "\n".join(
        line for line in result.stdout.decode("utf-8").splitlines() if not line.startswith("#")
    ) + "\n"
    modules = {}
    for index, path in enumerate(loaders):
        marker = f"@OPENFOLLOW_PIXBUF_MODULE_{index}@"
        pattern = re.compile(r'^"[^"\r\n]*[\\/]' + re.escape(path.name) + r'"\r?$', re.MULTILINE)
        template, replaced = pattern.subn(lambda _match: marker, template)
        if replaced != 1:
            raise RuntimeError(f"Missing loader metadata for {path.name}")
        modules[marker] = path.relative_to(prefix).as_posix()
    files = {}
    for path in [query, *sorted(query.parent.glob("*pixbuf*.dll")), *loaders]:
        with path.open("rb") as source:
            files[path.relative_to(prefix).as_posix()] = hashlib.file_digest(source, "sha256").hexdigest()
    output.write_text(json.dumps({"version": 1, "template": template, "modules": modules, "files": files}), encoding="utf-8")
    print("Generated relocatable Windows image loader metadata.")


if __name__ == "__main__":
    main()
