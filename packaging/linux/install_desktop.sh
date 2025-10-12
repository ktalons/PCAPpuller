#!/usr/bin/env bash
# Minimal installer for PCAPpuller desktop integration on Linux
# - Installs desktop entry and icon for system menus
# - Requires root privileges (via sudo)
set -euo pipefail

repo_root=$(cd "$(dirname "$0")"/../.. && pwd)
app_desktop_src="$repo_root/pcappuller-gui.desktop"
icon_src="$repo_root/assets/PCAPpuller.png"

app_desktop_dst="/usr/share/applications/PCAPpuller.desktop"
icon_dst_dir="/usr/share/icons/hicolor/512x512/apps"
icon_dst="$icon_dst_dir/PCAPpuller.png"

if [[ $EUID -ne 0 ]]; then
  echo "This script requires root. Re-running with sudo..."
  exec sudo "$0" "$@"
fi

if [[ ! -f "$app_desktop_src" ]]; then
  echo "Desktop file not found: $app_desktop_src" >&2
  exit 1
fi
if [[ ! -f "$icon_src" ]]; then
  echo "Icon file not found: $icon_src" >&2
  exit 1
fi

install -Dm644 "$app_desktop_src" "$app_desktop_dst"
install -d "$icon_dst_dir"
install -m644 "$icon_src" "$icon_dst"

# Refresh desktop and icon caches if tools are present
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

echo "Installed:"
echo "  $app_desktop_dst"
echo "  $icon_dst"
