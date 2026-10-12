# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Run gvsbuild with mandatory TLS verification and its source hash checks."""

from __future__ import annotations

import ssl
import sys


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("This native build requires Windows.")
    from gvsbuild.main import run
    from gvsbuild.utils.base_builders import CmakeProject
    from gvsbuild.utils.base_expanders import Tarball
    from gvsbuild.utils.base_project import Project, project_add
    from gvsbuild.utils.builder import Builder

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
