#!/usr/bin/env bash
# Server self-pull deploy.
#
# The deployment server is behind home NAT (only reachable over Tailscale), so
# GitHub Actions cannot push to it. Instead a systemd timer runs this script:
# it pulls the branch from GitHub (outbound, always works) and deploys it with
# the same deploy.py used everywhere.
#
#   main    -> deploy.py --main    (development stack, compose.dev.yml)
#   release -> deploy.py --release (blue-green zero-downtime, deploy-release.sh)
#
# Usage:
#   ./deploy/self-pull.sh main
#   ./deploy/self-pull.sh release
#
# Env:
#   REPO_DIR           repo checkout on the server (default: repo root)
#   SECRETS_DIR        dir holding the gitignored .env files (default: /home/vega/rent-secrets)
#   RELEASE_READY_FILE gate marker; release deploys are skipped until it exists
#
# systemd units (install as root):
#   /etc/systemd/system/rent-deploy-dev.service     -> ExecStart=... self-pull.sh main
#   /etc/systemd/system/rent-deploy-release.service -> ExecStart=... self-pull.sh release
#   timers run every 2 minutes (OnUnitActiveSec=2min, Persistent=true)
set -euo pipefail

BRANCH="${1:?usage: self-pull.sh <main|release>}"
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SECRETS_DIR="${SECRETS_DIR:-/home/vega/rent-secrets}"
RELEASE_READY_FILE="${RELEASE_READY_FILE:-$SECRETS_DIR/RELEASE_READY}"

log() { printf '\033[36m[self-pull]\033[0m %s\n' "$*"; }

# Release deploys retire the legacy vega_gateway/rent-backend edge on first run.
# Gate them behind a marker so that only happens once the operator has switched
# the cloudflared tunnel ingress to nginx_gateway (port 8080).
if [ "$BRANCH" = "release" ] && [ ! -f "$RELEASE_READY_FILE" ]; then
  log "release deploy gated — create $RELEASE_READY_FILE to enable"
  exit 0
fi

log "pulling origin/$BRANCH"
cd "$REPO_DIR"
export GIT_TERMINAL_PROMPT=0
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

# Secrets live outside the repo (gitignored) — symlink them in so deploys see them.
for f in .env.release .env.development; do
  if [ -f "$SECRETS_DIR/$f" ] && [ ! -e "$REPO_DIR/$f" ]; then
    ln -s "$SECRETS_DIR/$f" "$REPO_DIR/$f"
  fi
done

if [ "$BRANCH" = "release" ]; then
  python3 deploy.py --release --local --no-build
else
  python3 deploy.py --main --local
fi

log "$BRANCH deployed OK"
