#!/usr/bin/env bash
set -euo pipefail
# Build the GUI for this platform with the same recipe as the release CI.
# Thin dispatcher: the per-OS scripts under packaging/ mirror .github/workflows/release.yml,
# so there is exactly one copy of each platform's build steps outside the workflow.
# Usage: scripts/build_gui.sh

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

case "$(uname -s)" in
  Darwin) exec bash "$PROJECT_ROOT/packaging/macos/build_pyinstaller.sh" ;;
  Linux)  exec bash "$PROJECT_ROOT/packaging/linux/build_pyinstaller.sh" ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "On Windows run: pwsh -File packaging\\windows\\build_pyinstaller.ps1" >&2
    exit 1 ;;
  *)
    echo "Unsupported platform: $(uname -s)" >&2
    exit 1 ;;
esac
