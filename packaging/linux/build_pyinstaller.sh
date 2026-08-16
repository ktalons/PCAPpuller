#!/usr/bin/env bash
# Build the Linux GUI binary locally, mirroring the Linux branch of .github/workflows/release.yml.
# Produces release/PCAPpullerGUI-linux; package it with packaging/linux/build_fpm.sh.
# Requires an active Python environment (e.g. `source .venv/bin/activate`); the script installs
# PyInstaller and the package extras into it, the same as CI.
# Usage: packaging/linux/build_pyinstaller.sh
set -euo pipefail

repo_root=$(cd "$(dirname "$0")"/../.. && pwd)
cd "$repo_root"

python3 -m pip install --upgrade pyinstaller >/dev/null
python3 -m pip install -e ".[datetime,gui]" >/dev/null

mkdir -p release
pyinstaller --noconfirm --onefile --windowed --name PCAPpullerGUI \
  --add-data "pcappuller/assets/pcappuller.png:pcappuller/assets" \
  gui_pcappuller.py
mv dist/PCAPpullerGUI release/PCAPpullerGUI-linux

echo "Built release/PCAPpullerGUI-linux"
