# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Run gvsbuild with mandatory TLS verification and its source hash checks."""

from __future__ import annotations

import os
import shutil
import ssl
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("This native build requires Windows.")
    from gvsbuild.main import run
    from gvsbuild.projects.libvpx import Libvpx
    from gvsbuild.utils.base_builders import CmakeProject
    from gvsbuild.utils.base_expanders import Tarball
    from gvsbuild.utils.base_project import Project, project_add
    from gvsbuild.utils.builder import Builder

    def msys_tools_first(method):
        def wrapped(self):
            # Git's bundled MSYS utilities can precede MSYS2 in the VS PATH.
            # Mixing their runtimes corrupts heredoc append redirections in
            # configure (the banner/TOOLCHAIN gets overwritten by later cat).
            # Keep bash, cat, make and sed on the same MSYS2 runtime.
            previous = self.builder.vs_env["PATH"]
            msys = Project.get_tool_path("msys2")
            self.builder.vs_env["PATH"] = str(msys) + ";" + previous
            try:
                return method(self)
            finally:
                self.builder.vs_env["PATH"] = previous

        return wrapped

    original_vpx_build = Libvpx.build

    @msys_tools_first
    def build_vpx(self):
        # make's generated solution builds Debug before Release. NASM's
        # CodeView debug assembly crashes in that unrelated configuration.
        # Generate/install headers here; post_install builds only the actual
        # requested configuration with MSBuild (Release for this package).
        previous = self.builder.vs_env.get("NO_LAUNCH_DEVENV")
        self.builder.vs_env["NO_LAUNCH_DEVENV"] = "1"
        try:
            original_vpx_build(self)
        finally:
            if previous is None:
                self.builder.vs_env.pop("NO_LAUNCH_DEVENV", None)
            else:
                self.builder.vs_env["NO_LAUNCH_DEVENV"] = previous

    @msys_tools_first
    def install_vpx(self):
        # libvpx's generated Makefile silently skips MSBuild when `which`
        # cannot find it. Compile the generated project explicitly instead
        # of accepting configure/make success as a compiled library.
        architecture = "Win32" if self.builder.x86 else "x64"
        debug = self.builder.opts.configuration == "debug"
        configuration = "Debug" if debug else "Release"
        filename = "vpxmdd.lib" if debug else "vpxmd.lib"
        working = Path(self._get_working_dir())
        try:
            projects = list(working.rglob("vpx.vcxproj"))
            if not projects:
                self.exec_vs(
                    ["make", "target=libs", "NO_LAUNCH_DEVENV=1", "vpx.vcxproj"],
                    add_path=Project.get_tool_path("msys2"),
                )
                projects = list(working.rglob("vpx.vcxproj"))
            if len(projects) != 1:
                available = sorted(str(path.relative_to(working)) for path in working.rglob("*.vcxproj"))
                raise RuntimeError(f"Expected one generated vpx project in {working}, found: {available}")
            project = projects[0]
            library = project.parent / architecture / configuration / filename
            if not library.is_file():
                msbuild_dir = Path(os.environ["OPENFOLLOW_MSBUILD"]).parent
                self.exec_msbuild([str(project), "/m"], configuration=configuration, add_path=str(msbuild_dir))
        except subprocess.CalledProcessError as exc:
            output = exc.stdout or "libvpx build command failed without captured output."
            errors = [line for line in output.splitlines() if "error" in line.lower()]
            detail = "\n".join(errors[-12:] or output.splitlines()[-20:])
            annotation = detail.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=libvpx compiler error::{annotation}", flush=True)
            raise RuntimeError(f"libvpx compiler failed:\n{detail}") from None
        if not library.is_file():
            raise RuntimeError(f"MSBuild did not produce the required libvpx library: {library}")
        shutil.copy2(library, Path(self.builder.gtk_dir) / "lib" / "vpx.lib")

    Libvpx.build = build_vpx
    Libvpx.post_install = install_vpx

    @project_add
    class Srt(Tarball, CmakeProject):
        def __init__(self):
            Project.__init__(
                self,
                "openfollow-srt",
                version="1.5.4",
                archive_url="https://github.com/Haivision/srt/archive/refs/tags/v{version}.tar.gz",
                archive_filename="srt-{version}.tar.gz",
                hash="d0a8b600fe1b4eaaf6277530e3cfc8f15b8ce4035f16af4a5eb5d4b123640cdd",
                dependencies=["cmake", "ninja", "openssl"],
            )

        def build(self):
            CmakeProject.build(
                self,
                use_ninja=True,
                cmake_params=[
                    "-DENABLE_APPS=OFF",
                    "-DENABLE_SHARED=ON",
                    "-DENABLE_STATIC=OFF",
                    "-DENABLE_ENCRYPTION=ON",
                    f"-DOPENSSL_ROOT_DIR={self.builder.gtk_dir}",
                ],
            )
            self.install(r".\LICENSE share\doc\srt")

    retrieve = Builder.urlretrieve

    def verified_retrieve(self, url, filename, reporthook, ssl_ignore_cert=False):
        if ssl_ignore_cert:
            raise ssl.SSLCertVerificationError("TLS verification failed; repair the certificate trust configuration.")
        return retrieve(self, url, filename, reporthook, ssl_ignore_cert=False)

    Builder.urlretrieve = verified_retrieve
    run()


if __name__ == "__main__":
    main()
