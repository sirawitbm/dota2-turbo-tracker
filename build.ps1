$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "tools\project.ps1")

$iconPath = Join-Path $PSScriptRoot "assets\TurboTracker.ico"
$outputPath = Join-Path $PSScriptRoot "dist\$ProjectExeName.exe"
$versionInfoPath = Join-Path ([System.IO.Path]::GetTempPath()) `
    ("TurboTracker-version-" + [guid]::NewGuid() + ".txt")

if (-not (Test-Path $iconPath)) {
    throw "Missing $iconPath. Run: python tools\make_icon.py (needs Pillow)."
}

python -m pip install pyinstaller -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller installation failed with exit code $LASTEXITCODE."
}

Write-Host "Building $ProjectName $ProjectVersion"
New-VersionInfoFile -Path $versionInfoPath

try {
    python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name $ProjectExeName `
        --icon $iconPath `
        --version-file $versionInfoPath `
        --exclude-module PySide6.QtNetwork `
        --exclude-module PySide6.QtQml `
        --exclude-module PySide6.QtQuick `
        --exclude-module PySide6.QtPdf `
        --exclude-module PySide6.QtWebEngineCore `
        --exclude-module tkinter `
        (Join-Path $PSScriptRoot "turbo_tracker.py")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outputPath)) {
        throw "Turbo Tracker build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item $versionInfoPath -Force -ErrorAction SilentlyContinue
}

Write-Host "Done: $outputPath"
