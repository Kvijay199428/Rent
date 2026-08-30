#!/usr/bin/env bash
# Release deploy — single active backend slot.
#
# Strategy: the backend image is built, the existing propaura_backend_prod
# container is force-recreated (brief restart), waited on via /health, then the
# edge nginx is reloaded and smoke-tested. SQLite lives in ./storage/release and
# is only ever written by this one container.
#
# Usage:
#   ./deploy/deploy-release.sh [--no-frontend] [--no-build]
#
# Env:
#   REPO_DIR  repo path on the server (default: repo root of this script)
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR"

ENV_FILE=".env.release"
COMPOSE="compose.prod.yml"
# Compose service names (used with `docker compose build/up`).
BACKEND_SVC="backend_prod"
FRONTEND_SVC="frontend_prod"
EDGE_SVC="nginx_gateway_prod"
# Container names (used with `docker exec/inspect`).
BACKEND="propaura_backend_prod"
FRONTEND="propaura_frontend_prod"
EDGE_NGINX="propaura_nginx_gateway_prod"
BACKEND_PORT=28005

WITH_FRONTEND=1
WITH_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --no-frontend) WITH_FRONTEND=0 ;;
    --no-build) WITH_BUILD=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[36m[deploy]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[deploy]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[deploy]\033[0m %s\n' "$*"; }

wait_health() {
  local container="$1" port tries i
  port="${2:-$BACKEND_PORT}"
  tries="${3:-30}"
  for i in $(seq 1 "$tries"); do
    if docker exec "$container" python -c "import urllib.request; urllib.request.urlopen('http://localhost:${port}/health', timeout=5)" >/dev/null 2>&1; then
      ok "$container healthy (try $i/$tries)"
      return 0
    fi
    printf '..  waiting for %s (%s/%s)\n' "$container" "$i" "$tries"
    sleep 3
  done
  fail "$container did not become healthy within $((tries * 3))s"
  return 1
}

reload_edge() {
  local reloaded=0
  if docker exec "$EDGE_NGINX" nginx -s reload >/dev/null 2>&1; then
    ok "reloaded edge nginx ($EDGE_NGINX)"
    reloaded=1
  fi
  if docker exec propaura_legacy_gateway nginx -s reload >/dev/null 2>&1; then
    ok "reloaded legacy edge nginx (propaura_legacy_gateway)"
    reloaded=1
  fi
  if [ "$reloaded" -eq 0 ]; then
    warn "no edge nginx container found to reload — is compose.prod.yml $EDGE_NGINX running?"
  fi
}

smoke_test() {
  if curl -fsS "http://127.0.0.1:28005/health" >/dev/null 2>&1; then
    ok "edge smoke test passed (/health via 127.0.0.1:28005)"
    return 0
  fi
  if curl -fsS "https://api.vijaykrsha.online/health" >/dev/null 2>&1; then
    ok "edge smoke test passed (/health via https://api.vijaykrsha.online)"
    return 0
  fi
  warn "edge smoke test could not reach /health (network/firewall?) — backend verified directly"
  return 0
}

build_frontend() {
  if ! command -v node >/dev/null 2>&1; then
    warn "node not found on server — skipping frontend build"
    warn "propaura_frontend_prod (host 28004) needs frontend/build-output; build it locally and scp it,"
    warn "or install node on the server and rerun the deploy"
    return 0
  fi
  log "building frontend (VITE_API_BASE_URL=$VITE_API_BASE_URL)"
  (cd frontend && bash build.sh)
}

frontend_missing() {
  [ ! -f "frontend/build-output/rent/index.html" ]
}

main() {
  # ── Lock: prevent overlapping runs ─────────────────────────────────────
  # The systemd timer fires every 2 min; an image build can take longer, so
  # a second run would otherwise race the first on the container lifecycle.
  LOCK_FILE="${LOCK_FILE:-/tmp/rent-deploy-release.lock}"
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    fail "another deploy-release.sh is already running (lock held on $LOCK_FILE)"
    exit 1
  fi

  # ── Preflight ───────────────────────────────────────────────────────────
  command -v docker >/dev/null || { fail "docker not found"; exit 1; }
  command -v curl >/dev/null || { fail "curl not found"; exit 1; }
  [ -f "$ENV_FILE" ] || { fail "$ENV_FILE missing — copy .env.release.example and fill in secrets"; exit 1; }
  [ -f "$COMPOSE" ] || { fail "$COMPOSE missing"; exit 1; }

  export VITE_API_BASE_URL
  VITE_API_BASE_URL="$(grep -E '^VITE_API_BASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"')"
  VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.vijaykrsha.online}"

  docker network create propaura-network 2>/dev/null || true

  if [ "$WITH_FRONTEND" -eq 1 ] && frontend_missing; then
    warn "frontend/build-output missing — building (release frontend for host port 28004)"
    build_frontend
  fi

  if [ "$WITH_BUILD" -eq 1 ]; then
    log "building backend image"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" build "$BACKEND_SVC"
  else
    warn "--no-build: using existing image"
  fi

  # ── Deploy the backend slot (brief restart) ──────────────────────────────
  if docker inspect "$BACKEND" >/dev/null 2>&1; then
    log "recreating $BACKEND"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --force-recreate --no-deps "$BACKEND_SVC"
  else
    log "starting $BACKEND (first deployment)"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --no-deps "$BACKEND_SVC"
  fi
  wait_health "$BACKEND" "$BACKEND_PORT"

  # ── Bring up the edge + frontend if they are not already running ────────
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --no-deps "$FRONTEND_SVC" "$EDGE_SVC"
  sleep 3
  reload_edge
  smoke_test
  ok "release deploy complete — $BACKEND on port $BACKEND_PORT"
}

main "$@"
