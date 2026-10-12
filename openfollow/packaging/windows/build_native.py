# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Run gvsbuild with mandatory TLS verification and its source hash checks."""

from __future__ import annotations

import os
import shutil
import ssl
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

    def install_vpx(self):
        # libvpx's generated Makefile silently skips MSBuild when `which`
        # cannot find it. Compile the generated project explicitly instead
        # of accepting configure/make success as a compiled library.
        architecture = "Win32" if self.builder.x86 else "x64"
        debug = self.builder.opts.configuration == "debug"
        configuration = "Debug" if debug else "Release"
        filename = "vpxmdd.lib" if debug else "vpxmd.lib"
        library = Path(self.build_dir) / architecture / configuration / filename
        if not library.is_file():
            msbuild_dir = Path(os.environ["OPENFOLLOW_MSBUILD"]).parent
            self.exec_msbuild(["vpx.vcxproj", "/m"], configuration=configuration, add_path=str(msbuild_dir))
        if not library.is_file():
            raise RuntimeError(f"MSBuild did not produce the required libvpx library: {library}")
        shutil.copy2(library, Path(self.builder.gtk_dir) / "lib" / "vpx.lib")

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
