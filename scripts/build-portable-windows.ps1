Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildRoot = Join-Path $RepoRoot "build\portable"
$DistRoot = Join-Path $RepoRoot "dist"
$PortableRoot = Join-Path $DistRoot "AurynkPortable"
$ToolsRoot = Join-Path $PortableRoot "tools"
$AdbRoot = Join-Path $PortableRoot "platform-tools"
$ScrcpyRoot = Join-Path $ToolsRoot "scrcpy"
$ArtifactName = "AurynkPortable-windows-x64.zip"
$ArtifactPath = Join-Path $DistRoot $ArtifactName
$PythonExe = $env:PYTHON
if (-not $PythonExe) {
    $PythonExe = "python"
}

function Invoke-Step([string]$Message, [scriptblock]$Action) {
    Write-Host "==> $Message" -ForegroundColor Cyan
    & $Action
}

function Invoke-External([scriptblock]$Action) {
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "External command failed with exit code $LASTEXITCODE."
    }
}

function Expand-ZipSingleRoot([string]$ZipPath, [string]$DestinationPath) {
    $ExpandTarget = Join-Path $BuildRoot ([System.IO.Path]::GetFileNameWithoutExtension($ZipPath))
    if (Test-Path $ExpandTarget) {
        Remove-Item -Recurse -Force $ExpandTarget
    }
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExpandTarget -Force

    $Entries = @(Get-ChildItem -LiteralPath $ExpandTarget)
    if ($Entries.Count -eq 1 -and $Entries[0].PSIsContainer) {
        $Source = $Entries[0].FullName
    }
    else {
        $Source = $ExpandTarget
    }

    if (Test-Path $DestinationPath) {
        Remove-Item -Recurse -Force $DestinationPath
    }
    New-Item -ItemType Directory -Force -Path $DestinationPath | Out-Null
    Copy-Item -Path (Join-Path $Source "*") -Destination $DestinationPath -Recurse -Force
}

Invoke-Step "Preparing directories" {
    New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
    if (Test-Path $PortableRoot) {
        Remove-Item -Recurse -Force $PortableRoot
    }
    if (Test-Path $ArtifactPath) {
        Remove-Item -Force $ArtifactPath
    }
}

Invoke-Step "Building web frontend" {
    Push-Location (Join-Path $RepoRoot "web")
    try {
        Invoke-External { npm ci }
        Invoke-External { npm run build }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "Installing Python build dependencies" {
    Invoke-External { & $PythonExe -m ensurepip --upgrade }
    Invoke-External { & $PythonExe -m pip install . pyinstaller }
}

Invoke-Step "Building portable app with PyInstaller" {
    Push-Location $RepoRoot
    try {
        Invoke-External { & $PythonExe -m PyInstaller --noconfirm aurynk-portable.spec }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "Downloading Android platform-tools" {
    $ZipPath = Join-Path $BuildRoot "platform-tools-latest-windows.zip"
    Invoke-WebRequest -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile $ZipPath
    Expand-ZipSingleRoot -ZipPath $ZipPath -DestinationPath $AdbRoot
}

Invoke-Step "Downloading latest scrcpy for Windows" {
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/Genymobile/scrcpy/releases/latest" -Headers @{ "User-Agent" = "AurynkPortableBuild" }
    $Asset = $Release.assets | Where-Object { $_.name -match '^scrcpy-win64-v.+\.zip$' } | Select-Object -First 1
    if (-not $Asset) {
        throw "Could not find a scrcpy win64 release asset."
    }

    $ZipPath = Join-Path $BuildRoot $Asset.name
    Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $ZipPath
    Expand-ZipSingleRoot -ZipPath $ZipPath -DestinationPath $ScrcpyRoot
}

Invoke-Step "Writing portable launcher note" {
    @"
Aurynk Portable for Windows

Contents:
- Aurynk desktop shell
- Bundled web frontend
- Bundled Android platform-tools in .\platform-tools
- Bundled scrcpy in .\tools\scrcpy

If you replace the bundled tools, keep this structure:
- .\platform-tools\adb.exe
- .\tools\scrcpy\scrcpy.exe
"@ | Set-Content -Path (Join-Path $PortableRoot "README-portable.txt") -Encoding UTF8
}

Invoke-Step "Creating zip artifact" {
    Compress-Archive -Path (Join-Path $PortableRoot "*") -DestinationPath $ArtifactPath -Force
}

Write-Host ""
Write-Host "Portable package ready:" -ForegroundColor Green
Write-Host "  $ArtifactPath"
