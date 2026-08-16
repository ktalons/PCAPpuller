# Build the Windows exe locally, mirroring the Windows branch of .github/workflows/release.yml.
# Produces release\PCAPpullerGUI-windows.exe with the version resource embedded.
# Requires an active Python environment (e.g. .venv\Scripts\Activate.ps1); the script installs
# PyInstaller and the package extras into it, the same as CI. Version comes from pcappuller.__version__.
# Run in PowerShell: pwsh -File packaging\windows\build_pyinstaller.ps1

$ErrorActionPreference = "Stop"

# Change to repo root
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

python -m pip install --upgrade pyinstaller | Out-Null
python -m pip install -e ".[datetime,gui]" | Out-Null

$Version = (python -c "import pcappuller; print(pcappuller.__version__)").Trim()
$Major, $Minor, $Patch = $Version.Split('.')
New-Item -ItemType Directory -Force -Path build, release | Out-Null

# Version resource: render packaging/windows/version-info.txt with the release version,
# then let PyInstaller embed it. A leftover placeholder fails the build.
$rendered = (Get-Content packaging\windows\version-info.txt -Raw) `
  -replace '@VERSION@', $Version `
  -replace '@VERSION_TUPLE@', "$Major, $Minor, $Patch, 0"
if ($rendered -match '@') { throw "unrendered placeholder in version-info.txt" }
Set-Content -Path build\version-info.txt -Value $rendered -Encoding UTF8

pyinstaller --noconfirm --onefile --windowed --name PCAPpullerGUI `
  --icon assets/PCAPpuller.ico `
  --version-file build/version-info.txt `
  --add-data "pcappuller/assets/pcappuller.png;pcappuller/assets" `
  gui_pcappuller.py
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed with exit code $LASTEXITCODE" }
Move-Item -Force dist\PCAPpullerGUI.exe release\PCAPpullerGUI-windows.exe

# Read the resource back so a missing or wrong version fails the build instead of shipping.
$actual = (Get-Item release\PCAPpullerGUI-windows.exe).VersionInfo.ProductVersion
if ($actual -ne $Version) { throw "version resource mismatch: exe reports '$actual', expected '$Version'" }

Write-Host "Built release\PCAPpullerGUI-windows.exe (version $Version)"
