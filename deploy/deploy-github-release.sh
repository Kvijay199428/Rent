#!/usr/bin/env bash
# Tag a release and create a GitHub Release with auto-generated notes.
#
# Usage:
#   ./deploy/deploy-github-release.sh v1.2.0
set -euo pipefail

VERSION="${1:?usage: ./deploy/deploy-github-release.sh v1.2.0}"

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR"

command -v gh >/dev/null || { echo "gh CLI not installed" >&2; exit 1; }
command -v git >/dev/null || { echo "git not installed" >&2; exit 1; }

git tag -a "$VERSION" -m "Release $VERSION"
git push origin "$VERSION"

gh release create "$VERSION" --generate-notes
echo "=== GitHub Release $VERSION created ==="
