# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
[CmdletBinding()]
param(
    [string]$BuildRoot = "$env:LOCALAPPDATA\OpenFollow-build",
    [string]$NativePrefix = "",
    [string]$MsysRoot = "C:\msys64",
    [string]$PythonExecutable = "",
    [switch]$Detection
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw "The executable must be built on Windows."
}
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
$BuildRoot = (Resolve-Path $BuildRoot).Path

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments 2>&1 | Tee-Object -Variable CommandOutput
    $ExitStatus = $LASTEXITCODE
    if ($ExitStatus -ne 0) {
        $Details = ($CommandOutput | Select-Object -Last 35 | Out-String)
        throw "$Program failed with exit code $ExitStatus`n$Details"
    }
}

Push-Location $Repo
try {
    $Venv = Join-Path $BuildRoot "venv"
    if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
        if ($PythonExecutable) {
            Invoke-Checked $PythonExecutable @("-m", "venv", $Venv)
        } else {
            Invoke-Checked "py" @("-3.13", "-m", "venv", $Venv)
        }
    }
    $Python = Join-Path $Venv "Scripts\python.exe"
    Invoke-Checked $Python @("-c", "import sys,struct; assert sys.version_info[:2] == (3,13); assert struct.calcsize('P') == 8")
    Invoke-Checked $Python @("-m", "pip", "install", "poetry==2.4.1", "poetry-plugin-export==1.9.0", "gvsbuild==2026.8.0", "pyinstaller==6.22.3", "pyinstaller-hooks-contrib==2026.8", "pillow==11.3.0")
    if (-not $NativePrefix) {
        if (-not (Test-Path (Join-Path $MsysRoot "usr\bin\patch.exe"))) {
            throw "Install MSYS2 and its patch package, or provide -NativePrefix. See packaging/windows/README.md."
        }
        $NativeRoot = Join-Path $BuildRoot "native-build"
        Invoke-Checked $Python @(
            "$PSScriptRoot\build_native.py", "build", "--platform", "x64", "--configuration", "release",
            "--build-dir", $NativeRoot, "--msys-dir", $MsysRoot, "--enable-gi", "--py-wheel",
            "--extra-opts", "gst-plugins-good:-Dgtk3=enabled;-Djpeg=enabled;-Dpng=enabled",
            "--extra-opts", "gst-plugins-bad:-Dsrt=enabled",
            "gtk3", "pygobject", "librsvg", "adwaita-icon-theme", "libjpeg-turbo", "libpng",
            "gstreamer", "gst-plugins-base", "gst-plugins-good", "openfollow-srt", "gst-plugins-bad", "gst-libav"
        )
        $NativePrefix = Join-Path $NativeRoot "gtk\x64\release"
    }
    $NativePrefix = (Resolve-Path $NativePrefix).Path
    $env:OPENFOLLOW_NATIVE_PREFIX = $NativePrefix
    $env:PATH = "$NativePrefix\bin;" + $env:PATH
    $env:GI_TYPELIB_PATH = "$NativePrefix\lib\girepository-1.0"
    $env:GST_PLUGIN_PATH_1_0 = "$NativePrefix\lib\gstreamer-1.0"
    $env:GST_REGISTRY_FORK = "no"
    $Wheels = @(Get-ChildItem -Path $NativePrefix -Filter "*.whl" -Recurse |
        Where-Object { $_.Name -match "^(pygobject|pycairo)-" })
    if ($Wheels.Count -lt 2) { throw "Native prefix must include the Python 3.13 PyGObject and Pycairo wheels." }
    foreach ($Wheel in $Wheels) {
        Invoke-Checked $Python @("-m", "pip", "install", "--no-deps", $Wheel.FullName)
    }
    $env:VIRTUAL_ENV = $Venv
    $env:POETRY_VIRTUALENVS_CREATE = "false"
    $Export = Join-Path $BuildRoot "requirements-full.txt"
    $Requirements = Join-Path $BuildRoot "requirements-python.txt"
    $Vcs = Join-Path $BuildRoot "requirements-vcs.txt"
    $ExportArgs = @("-m", "poetry", "export", "--only", "main", "--output", $Export)
    if ($Detection) { $ExportArgs += @("-E", "detection") }
    Invoke-Checked $Python $ExportArgs
    Invoke-Checked $Python @("$PSScriptRoot\export_requirements.py", $Export, $Requirements, $Vcs)
    Invoke-Checked $Python @("-m", "pip", "install", "--require-hashes", "-r", $Requirements)
    Invoke-Checked $Python @("-m", "pip", "install", "--no-deps", "-r", $Vcs)
    Invoke-Checked $Python @("-m", "pip", "install", "--no-deps", $Repo)
    Invoke-Checked $Python @("-m", "pip", "check")
    $Output = Join-Path $BuildRoot "dist"
    Invoke-Checked $Python @("-m", "PyInstaller", "--noconfirm", "--distpath", $Output,
        "--workpath", (Join-Path $BuildRoot "freeze"), "$PSScriptRoot\openfollow.spec")
    $Executable = Join-Path $Output "OpenFollow\OpenFollow.exe"
    $Report = Join-Path $BuildRoot "self-check.json"
    $Process = Start-Process -FilePath $Executable -ArgumentList @("--self-check", ('"' + $Report + '"')) -Wait -PassThru
    if ($Process.ExitCode -ne 0) { throw "The bundled self-check failed. Read $Report." }
    if (-not (Get-Content -Raw $Report | ConvertFrom-Json).ok) { throw "Invalid self-check report." }
    Invoke-Checked $Python @("$PSScriptRoot\smoke_gui.py", $Executable, (Join-Path $Output "OpenFollow-running.png"))
    foreach ($Notice in @("LICENSE", "THIRD_PARTY_NOTICES.md", "WRITTEN_OFFER.md")) {
        Copy-Item (Join-Path $Repo $Notice) (Join-Path $Output "OpenFollow\$Notice")
    }
    Copy-Item "$PSScriptRoot\README.md" (Join-Path $Output "OpenFollow\README-Windows.md")
    Compress-Archive -Path (Join-Path $Output "OpenFollow") -DestinationPath (Join-Path $Output "OpenFollow-Windows-x64.zip") -Force
    Write-Host "Built: $Output\OpenFollow-Windows-x64.zip"
    Write-Host "Run OpenFollow.exe from the extracted folder; keep its _internal directory."
} finally {
    Pop-Location
}
