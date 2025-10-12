# Build a portable Windows app using PyInstaller
# Run in PowerShell: pwsh -File packaging\windows\build_pyinstaller.ps1

$ErrorActionPreference = "Stop"

# Ensure pyinstaller is available
python -m pip install --upgrade pyinstaller | Out-Null

# Change to repo root
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

# Build
pyinstaller `
  --name "PCAPpuller" `
  --windowed `
  --icon assets/PCAPpuller.ico `
  --noconfirm `
  gui_pcappuller.py

Write-Host "Built app at: dist/PCAPpuller.exe"
