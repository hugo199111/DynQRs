# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Bundle updated web resources with an existing native Windows executable."""

import argparse
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def require_same_runtime(repository: Path, base_commit: str) -> None:
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "-z", base_commit, "HEAD", "--", "openfollow"],
        cwd=repository,
    ).decode().split("\0")
    allowed = (
        "openfollow/openfollow/web/static/",
        "openfollow/openfollow/web/templates/",
        "openfollow/packaging/iphone/",
    )
    forbidden = [
        name for name in changed
        if name and name != "openfollow/packaging/windows/README.md"
        and not name.startswith(allowed)
    ]
    if forbidden:
        raise SystemExit(
            "Native sources changed; compile a new Windows executable first: "
            + ", ".join(forbidden)
        )


def repackage(source: Path, destination: Path, application: Path) -> None:
    replacements = {}
    prefix = "OpenFollow/_internal/openfollow/web/"
    for directory in ("static", "templates"):
        root = application / "openfollow" / "web" / directory
        for path in sorted(root.rglob("*")):
            if path.is_file():
                name = prefix + directory + "/" + path.relative_to(root).as_posix()
                replacements[name] = path
    replacements["OpenFollow/README-Windows.md"] = (
        application / "packaging" / "windows" / "README.md"
    )
    replacements["OpenFollow/README-iPhone.md"] = (
        application / "packaging" / "iphone" / "README.md"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as original, ZipFile(
        destination, "w", compression=ZIP_DEFLATED, compresslevel=6
    ) as updated:
        if "OpenFollow/OpenFollow.exe" not in original.namelist():
            raise SystemExit("The input archive does not contain OpenFollow.exe.")
        for entry in original.infolist():
            if entry.filename in replacements:
                continue
            with original.open(entry) as reader, updated.open(entry, "w") as writer:
                shutil.copyfileobj(reader, writer)
        for name, path in replacements.items():
            updated.write(path, name)
    print(f"Windows and iPhone package: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--base-commit", required=True)
    args = parser.parse_args()
    application = Path(__file__).resolve().parents[2]
    require_same_runtime(application.parent, args.base_commit)
    if args.source.resolve() == args.destination.resolve():
        raise SystemExit("Input and output archives must be different files.")
    repackage(args.source, args.destination, application)


if __name__ == "__main__":
    main()
