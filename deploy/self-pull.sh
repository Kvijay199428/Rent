#!/usr/bin/env bash
# Server self-pull deploy.
#
# The deployment server is behind home NAT (only reachable over Tailscale), so
# GitHub Actions cannot push to it. Instead a systemd timer runs this script:
# it pulls the branch from GitHub (outbound, always works) and deploys it with
# the same deploy.py used everywhere.
#
#   dev        -> deploy.py --dev      (development stack, compose.dev.yml)
#   production -> deploy.py --prod     (single-slot, deploy-release.sh)
#
# Usage:
#   ./deploy/self-pull.sh dev
#   ./deploy/self-pull.sh production
#
# Env:
#   REPO_DIR           repo checkout on the server (default: repo root)
#   SECRETS_DIR        dir holding the gitignored .env files (default: /home/vega/rent-secrets)
#   RELEASE_READY_FILE gate marker; production deploys are skipped until it exists
#
# systemd units (install as root):
#   /etc/systemd/system/rent-deploy-dev.service      -> ExecStart=... self-pull.sh dev
#   /etc/systemd/system/rent-deploy-production.service -> ExecStart=... self-pull.sh production
#   timers run every 2 minutes (OnUnitActiveSec=2min, Persistent=true)
set -euo pipefail

BRANCH="${1:?usage: self-pull.sh <dev|production>}"
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SECRETS_DIR="${SECRETS_DIR:-/home/vega/rent-secrets}"
RELEASE_READY_FILE="${RELEASE_READY_FILE:-$SECRETS_DIR/RELEASE_READY}"

log() { printf '\033[36m[self-pull]\033[0m %s\n' "$*"; }

# Production deploys are gated behind a marker so they only run once the
# operator has switched the cloudflared tunnel ingress to propaura_nginx_gateway_prod
# (host port 28014).
if [ "$BRANCH" = "production" ] && [ ! -f "$RELEASE_READY_FILE" ]; then
  log "release deploy gated — create $RELEASE_READY_FILE to enable"
  exit 0
fi

log "pulling origin/$BRANCH"
cd "$REPO_DIR"
export GIT_TERMINAL_PROMPT=0

# Secrets live outside the repo (gitignored) — symlink them in so deploys see them.
for f in .env.release .env.development; do
  if [ -f "$SECRETS_DIR/$f" ] && [ ! -e "$REPO_DIR/$f" ]; then
    ln -s "$SECRETS_DIR/$f" "$REPO_DIR/$f"
  fi
done

git fetch origin "$BRANCH" --quiet

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/"$BRANCH")"
if [ "$LOCAL" = "$REMOTE" ]; then
  log "$BRANCH already at $REMOTE (no change)"
  exit 0
fi
log "$BRANCH $LOCAL -> $REMOTE"
git checkout -f -B "$BRANCH" "origin/$BRANCH"
git submodule update --init --recursive 2>/dev/null || true

if [ "$BRANCH" = "production" ]; then
  python3 deploy.py --prod --local --no-build
else
  python3 deploy.py --dev --local
fi

log "$BRANCH deployed OK"
