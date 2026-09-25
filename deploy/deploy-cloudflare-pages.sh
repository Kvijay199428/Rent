#!/usr/bin/env bash
# Build the frontend and deploy the static bundle to Cloudflare Pages.
#
# The frontend is served ONLY by Cloudflare Pages — the backend never serves
# HTML. This script pushes a build into the Pages project on a specific branch:
#   * production   -> --branch=production (rent-8rf.pages.dev / rent.vijaykrsha.online)
#   * development  -> --branch=dev        (dev.rent-8rf.pages.dev)
#
# Usage:
#   ./deploy/deploy-cloudflare-pages.sh [development|production]
#     (default: production)
#
# Env (required):
#   CLOUDFLARE_API_TOKEN
#   CLOUDFLARE_ACCOUNT_ID
#   CLOUDFLARE_PROJECT_NAME   (default: rent)
#   VITE_API_BASE_URL         (production default: https://api.vijaykrsha.online;
#                              development: left to build.sh's env priority)
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# IMPORTANT: wrangler resolves the Pages Functions directory (frontend/functions)
# from the process cwd. Deploying from the repo root silently skips the Functions
# bundle and _routes.json, producing a static-only (broken sub-app routing) deploy.
# This cd MUST be preserved.
cd "$REPO_DIR/frontend"

ENV_MODE="${1:-production}"
case "$ENV_MODE" in
  development|dev)
    ENV_MODE="development"
    BRANCH="dev"
    # Dev build API base is deliberately NOT hardcoded: hand it in as env
    # (e.g. VITE_API_BASE_URL=https://<tunnel>.ngrok-free.dev) or let build.sh
    # fall back to its own env priority.
    ;;
  production|prod)
    ENV_MODE="production"
    BRANCH="production"
    export VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.vijaykrsha.online}"
    ;;
  *)
    echo "Unknown target: $1 (expected: development|production)" >&2
    exit 2
    ;;
esac

PROJECT="${CLOUDFLARE_PROJECT_NAME:-rent}"

command -v npx >/dev/null || { echo "npx not found" >&2; exit 1; }
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "CLOUDFLARE_API_TOKEN not set" >&2; exit 1; }
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] || { echo "CLOUDFLARE_ACCOUNT_ID not set" >&2; exit 1; }

echo "=== Building frontend (VITE_API_BASE_URL=${VITE_API_BASE_URL:-<env default>}) ==="
bash build.sh

echo "=== Deploying to Cloudflare Pages ($PROJECT, branch: $BRANCH [$ENV_MODE]) ==="
# --branch=dev / --branch=production select the project's deployment branch:
#   dev  -> dev.rent-8rf.pages.dev      (the Pages project's dev branch)
#   prod -> rent-8rf.pages.dev + custom domain rent.vijaykrsha.online
npx wrangler pages deploy build-output \
  --project-name="$PROJECT" \
  --branch="$BRANCH"

echo "=== Deploy complete ==="