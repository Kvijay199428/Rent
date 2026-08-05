#!/usr/bin/env bash
# Build the frontend and deploy the static bundle to Cloudflare Pages (release).
#
# Usage:
#   ./deploy/deploy-cloudflare-pages.sh
#
# Env (required):
#   CLOUDFLARE_API_TOKEN
#   CLOUDFLARE_ACCOUNT_ID
#   CLOUDFLARE_PROJECT_NAME   (default: rent)
#   VITE_API_BASE_URL         (default: https://api.vijaykrsha.online)
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR/frontend"

export VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.vijaykrsha.online}"
PROJECT="${CLOUDFLARE_PROJECT_NAME:-rent}"

command -v npx >/dev/null || { echo "npx not found" >&2; exit 1; }
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "CLOUDFLARE_API_TOKEN not set" >&2; exit 1; }
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] || { echo "CLOUDFLARE_ACCOUNT_ID not set" >&2; exit 1; }

echo "=== Building frontend (VITE_API_BASE_URL=$VITE_API_BASE_URL) ==="
bash build.sh

echo "=== Deploying to Cloudflare Pages ($PROJECT, branch: release) ==="
npx wrangler pages deploy build-output \
  --project-name="$PROJECT" \
  --branch=release

echo "=== Deploy complete ==="
