#!/usr/bin/env bash
# Build a portable macOS app using PyInstaller
# Requires: python3 -m pip install pyinstaller
set -euo pipefail

repo_root=$(cd "$(dirname "$0")"/../.. && pwd)
cd "$repo_root"

python3 -m pip install --upgrade pyinstaller >/dev/null

# Use the existing GUI script as the entrypoint
pyinstaller \
  --name "PCAPpuller" \
  --windowed \
  --icon assets/PCAPpuller.icns \
  --noconfirm \
  gui_pcappuller.py

echo "Built app at: dist/PCAPpuller.app"
