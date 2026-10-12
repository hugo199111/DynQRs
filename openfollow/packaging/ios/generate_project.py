# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Generate the dependency-free native iOS Xcode project."""

import hashlib
import json
from pathlib import Path


def identifier(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


def main() -> None:
    root = Path(__file__).resolve().parent
    project = root / "OpenFollowMobile.xcodeproj"
    project.mkdir(exist_ok=True)
    sources = sorted((root / "OpenFollowMobile").glob("*.swift"))
    records = []

    def record(name: str, contents: str) -> str:
        key = identifier(name)
        records.append(f"{key} = {{ {contents} }};")
        return key

    def quoted(value: str) -> str:
        return json.dumps(value)

    source_ids = []
    file_ids = []
    for source in sources:
        reference = record(
            source.name,
            f"isa = PBXFileReference; lastKnownFileType = sourcecode.swift; "
            f"path = {quoted(source.name)}; sourceTree = \"<group>\";",
        )
        file_ids.append(reference)
        source_ids.append(record(source.name + "-build", f"isa = PBXBuildFile; fileRef = {reference};"))
    assets = record(
        "assets", "isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; "
        "path = Assets.xcassets; sourceTree = \"<group>\";",
    )
    asset_build = record("assets-build", f"isa = PBXBuildFile; fileRef = {assets};")
    app = record(
        "product", "isa = PBXFileReference; explicitFileType = wrapper.application; "
        "includeInIndex = 0; path = OpenFollow.app; sourceTree = BUILT_PRODUCTS_DIR;",
    )
    record("app-group", f"isa = PBXGroup; children = ({','.join(file_ids + [assets])}); path = OpenFollowMobile; sourceTree = \"<group>\";")
    record("products", f"isa = PBXGroup; children = ({app}); name = Products; sourceTree = \"<group>\";")
    record("main-group", f"isa = PBXGroup; children = ({identifier('app-group')},{identifier('products')}); sourceTree = \"<group>\";")
    source_phase = record("sources", f"isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({','.join(source_ids)}); runOnlyForDeploymentPostprocessing = 0;")
    resource_phase = record("resources", f"isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = ({asset_build}); runOnlyForDeploymentPostprocessing = 0;")
    framework_phase = record("frameworks", "isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;")
    for kind in ("project", "target"):
        configurations = []
        for mode in ("Debug", "Release"):
            if kind == "project":
                settings = 'CLANG_ENABLE_MODULES = YES; SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 17.0;'
            else:
                settings = (
                    'ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon; '
                    'CODE_SIGN_STYLE = Automatic; GENERATE_INFOPLIST_FILE = NO; '
                    'INFOPLIST_FILE = OpenFollowMobile/Info.plist; '
                    'IPHONEOS_DEPLOYMENT_TARGET = 17.0; '
                    'PRODUCT_BUNDLE_IDENTIFIER = app.openfollow.mobile; '
                    'PRODUCT_NAME = OpenFollow; SWIFT_VERSION = 5.0; '
                    'SWIFT_EMIT_LOC_STRINGS = YES; TARGETED_DEVICE_FAMILY = "1,2"; '
                    'SUPPORTED_PLATFORMS = "iphoneos iphonesimulator"; '
                    'SUPPORTS_MACCATALYST = NO; MARKETING_VERSION = 1.0; CURRENT_PROJECT_VERSION = 1; '
                    'LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks"; '
                )
                settings += 'SWIFT_OPTIMIZATION_LEVEL = "-O";' if mode == "Release" else 'SWIFT_OPTIMIZATION_LEVEL = "-Onone";'
            configurations.append(record(f"{kind}-{mode}", f"isa = XCBuildConfiguration; buildSettings = {{ {settings} }}; name = {mode};"))
        record(f"{kind}-configs", f"isa = XCConfigurationList; buildConfigurations = ({','.join(configurations)}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;")
    target = record(
        "target", f"isa = PBXNativeTarget; buildConfigurationList = {identifier('target-configs')}; "
        f"buildPhases = ({source_phase},{framework_phase},{resource_phase}); buildRules = (); dependencies = (); "
        f"name = OpenFollow; productName = OpenFollow; productReference = {app}; productType = \"com.apple.product-type.application\";",
    )
    root_object = record(
        "project", f"isa = PBXProject; attributes = {{ LastUpgradeCheck = 1600; }}; "
        f"buildConfigurationList = {identifier('project-configs')}; compatibilityVersion = \"Xcode 14.0\"; "
        f"developmentRegion = es; hasScannedForEncodings = 0; knownRegions = (es,en,Base); "
        f"mainGroup = {identifier('main-group')}; productRefGroup = {identifier('products')}; projectDirPath = \"\"; projectRoot = \"\"; targets = ({target});",
    )
    contents = '// !$*UTF8*$!\n{ archiveVersion = 1; classes = {}; objectVersion = 56; objects = {\n'
    contents += "\n".join(records) + f"\n}}; rootObject = {root_object}; }}\n"
    (project / "project.pbxproj").write_text(contents)
    print(f"Generated {project}")


if __name__ == "__main__":
    main()
