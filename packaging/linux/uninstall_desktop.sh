#!/usr/bin/env bash
# Minimal uninstaller for PCAPpuller desktop integration on Linux
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "This script requires root. Re-running with sudo..."
  exec sudo "$0" "$@"
fi

app_desktop_dst="/usr/share/applications/PCAPpuller.desktop"
icon_dst="/usr/share/icons/hicolor/512x512/apps/PCAPpuller.png"

rm -f "$app_desktop_dst" "$icon_dst"

# Refresh caches if tools are present
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

echo "Removed:"
echo "  $app_desktop_dst"
echo "  $icon_dst"
