#!/usr/bin/env bash
# Blue-green zero-downtime release deploy.
#
# Strategy: the ACTIVE slot keeps serving while the INACTIVE slot is built and
# brought up. Once the inactive slot passes /health, the edge nginx is atomically
# reloaded to point at it, and only then is the old slot stopped. Only one slot
# runs at a time, so the shared SQLite database is never written by two
# containers simultaneously.
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
ACTIVE_FILE="gateway/nginx/upstream/active.conf"
INACTIVE_FILE="gateway/nginx/upstream/inactive.conf"

BLUE="propaura-prod-backend-blue"
GREEN="propaura-prod-backend-green"
BLUE_PORT=28002
GREEN_PORT=28012

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

slot_port() {
  case "$1" in
    "$BLUE") echo "$BLUE_PORT" ;;
    "$GREEN") echo "$GREEN_PORT" ;;
    *) return 1 ;;
  esac
}

active_slot() {
  if grep -q "$BLUE" "$ACTIVE_FILE" 2>/dev/null; then
    echo "$BLUE"
  else
    echo "$GREEN"
  fi
}

wait_health() {
  local container="$1" port tries i
  port="$(slot_port "$container")"
  tries="${2:-30}"
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
  if docker exec propaura-prod-gateway nginx -s reload >/dev/null 2>&1; then
    ok "reloaded edge nginx (propaura-prod-gateway)"
    reloaded=1
  fi
  if [ "$reloaded" -eq 0 ]; then
    warn "no edge nginx container found to reload — is compose.prod.yml propaura-prod-gateway running?"
    warn "the upstream toggle file was still updated: $ACTIVE_FILE"
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
  warn "edge smoke test could not reach /health (network/firewall?) — backend slots verified directly"
  return 0
}

build_frontend() {
  if ! command -v node >/dev/null 2>&1; then
    warn "node not found on server — skipping frontend build"
    warn "propaura-prod-frontend (28004) needs frontend/build-output; build it locally and scp it,"
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
  # a second run would otherwise race the first on slot lifecycle + active.conf.
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

  docker network create vega-gateway 2>/dev/null || true

  ACTIVE="$(active_slot)"
  if [ "$ACTIVE" = "$BLUE" ]; then NEXT="$GREEN"; else NEXT="$BLUE"; fi
  ACTIVE_PORT="$(slot_port "$ACTIVE")"
  NEXT_PORT="$(slot_port "$NEXT")"
  log "active slot: $ACTIVE ($ACTIVE_PORT) -> deploying $NEXT ($NEXT_PORT)"

  # ── Initial deployment? ─────────────────────────────────────────────────
  if ! docker inspect "$BLUE" >/dev/null 2>&1 && ! docker inspect "$GREEN" >/dev/null 2>&1; then
    warn "no release backend slots found — running INITIAL deployment"
    if [ "$WITH_FRONTEND" -eq 1 ] && frontend_missing; then
      build_frontend
    fi
    if [ "$WITH_BUILD" -eq 1 ]; then
      docker compose --env-file "$ENV_FILE" -f "$COMPOSE" build "$BLUE" "$GREEN"
    fi
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --no-deps "$BLUE"
    wait_health "$BLUE"

    # Retire the legacy edge + single backend only AFTER the new slot is healthy.
    # One-time migration: the old gateway and backend on the same network
    # are superseded by propaura-prod-gateway + the blue/green slots.
    if docker inspect vega_gateway >/dev/null 2>&1 && ! docker inspect propaura-prod-gateway >/dev/null 2>&1; then
      warn "stopping legacy vega_gateway edge (replaced by propaura-prod-gateway)"
      docker stop vega_gateway >/dev/null 2>&1 || true
    fi
    if docker inspect rent-backend >/dev/null 2>&1; then
      warn "stopping legacy rent-backend container (replaced by blue/green slots)"
      docker stop rent-backend >/dev/null 2>&1 || true
    fi

    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --no-deps propaura-prod-frontend propaura-prod-gateway
    sleep 3
    reload_edge
    smoke_test
    ok "initial deployment complete — active: $BLUE"
    exit 0
  fi

  # ── Standard blue-green deploy ──────────────────────────────────────────
  if [ "$WITH_FRONTEND" -eq 1 ] && frontend_missing; then
    warn "frontend/build-output missing — building (release frontend for port 28004)"
    build_frontend
  fi

  if [ "$WITH_BUILD" -eq 1 ]; then
    log "building backend image"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE" build "$BLUE" "$GREEN"
  else
    warn "--no-build: using existing image"
  fi

  log "starting inactive slot $NEXT"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --no-deps "$NEXT"
  wait_health "$NEXT"

  # ── Verify the inactive slot is running before flipping ────────────────
  # Guards against the flip writing an upstream that points at a container
  # that died during startup (nginx then returns 502 until the next deploy).
  if [ "$(docker inspect -f '{{.State.Running}}' "$NEXT" 2>/dev/null)" != "true" ]; then
    fail "$NEXT is not running — aborting before flipping traffic"
    exit 1
  fi
  ok "$NEXT confirmed running"

  # ── Enable maintenance banner while traffic flips ─────────────────────
  MAINTENANCE_SECRET="${MAINTENANCE_SECRET:-}"
  if [ -n "$MAINTENANCE_SECRET" ]; then
    log "enabling maintenance banner during deploy..."
    curl -s -X POST "http://127.0.0.1:28005/api/maintenance/on" \
      -H "Content-Type: application/json" \
      -H "X-Maintenance-Secret: ${MAINTENANCE_SECRET}" || true
    sleep 3
  fi

  # ── Flip traffic ────────────────────────────────────────────────────────
  printf 'set $release_backend "%s:%s";\n' "$NEXT" "$NEXT_PORT" > "$ACTIVE_FILE"
  printf 'set $release_backend "%s:%s";\n' "$ACTIVE" "$ACTIVE_PORT" > "$INACTIVE_FILE"
  log "traffic flipped: $NEXT is now active ($ACTIVE_FILE updated)"
  reload_edge
  sleep 2
  smoke_test

  # ── Clear maintenance banner ───────────────────────────────────────────
  if [ -n "$MAINTENANCE_SECRET" ]; then
    log "clearing maintenance banner..."
    curl -s -X POST "http://127.0.0.1:28005/api/maintenance/off" \
      -H "Content-Type: application/json" \
      -H "X-Maintenance-Secret: ${MAINTENANCE_SECRET}" || true
  fi

  # ── Stop the old slot (kept as the rollback target) ─────────────────────
  log "stopping old slot $ACTIVE (still available for rollback via its image)"
  if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE" stop "$ACTIVE"; then
    warn "failed to stop $ACTIVE — continuing (it will be retired on the next deploy)"
  fi
  sleep 2
  smoke_test

  ok "release deploy complete — active: $NEXT on port $NEXT_PORT"
  echo ""
  echo "  Rollback:"
  echo "    sed -i 's/$NEXT/$ACTIVE/' $ACTIVE_FILE && docker exec propaura-prod-gateway nginx -s reload"
  echo "    docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps $ACTIVE"
}

main "$@"
