#!/usr/bin/env bash
set -euo pipefail
# Tag a release from the version in pyproject.toml and push it.
# Usage: scripts/tag_release.sh

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Version is dynamic (pyproject reads pcappuller.__version__); parse the source
VERSION=$(sed -nE 's/^__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"/\1/p' pcappuller/__init__.py)
if [[ -z "${VERSION:-}" ]]; then
  echo "Could not parse version from pcappuller/__init__.py" >&2
  exit 1
fi
TAG="v${VERSION}"

echo "Tagging ${TAG}..."
git tag "${TAG}" || { echo "Failed to create tag" >&2; exit 1; }

echo "Pushing ${TAG}..."
git push origin "${TAG}"

echo "Done. The Release workflow will build and publish binaries."
