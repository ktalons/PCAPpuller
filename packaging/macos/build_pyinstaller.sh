#!/usr/bin/env bash
# Build the macOS app locally, mirroring the macOS branch of .github/workflows/release.yml.
# Produces dist/PCAPpullerGUI.app and release/PCAPpullerGUI-macos.zip.
# Requires an active Python environment (e.g. `source .venv/bin/activate`); the script installs
# PyInstaller and the package extras into it, the same as CI. Version comes from pcappuller.__version__.
# Usage: packaging/macos/build_pyinstaller.sh
set -euo pipefail

repo_root=$(cd "$(dirname "$0")"/../.. && pwd)
cd "$repo_root"

python3 -m pip install --upgrade pyinstaller >/dev/null
python3 -m pip install -e ".[datetime,gui]" >/dev/null

VERSION=$(python3 -c "import pcappuller; print(pcappuller.__version__)")
mkdir -p release

pyinstaller --noconfirm --windowed --name PCAPpullerGUI \
  --osx-bundle-identifier com.ktalons.PCAPpuller \
  --icon assets/PCAPpuller.icns \
  --add-data "pcappuller/assets/pcappuller.png:pcappuller/assets" \
  gui_pcappuller.py

# Same post-build steps as CI: stamp the version, re-seal, verify, zip with symlinks intact.
APP=dist/PCAPpullerGUI.app
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$VERSION" "$APP/Contents/Info.plist"
codesign --force --sign - "$APP"
codesign --verify --deep --strict "$APP"
test "$(plutil -extract CFBundleShortVersionString raw -o - "$APP/Contents/Info.plist")" = "$VERSION"
rm -f release/PCAPpullerGUI-macos.zip
(cd dist && zip -ry ../release/PCAPpullerGUI-macos.zip PCAPpullerGUI.app)

echo "Built $APP (version $VERSION) and release/PCAPpullerGUI-macos.zip"
