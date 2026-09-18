#!/usr/bin/env bash
# Read-only smoke probe: hits health/ready endpoints and prints status + timing.
# Never mutates anything, never retries destructively. Exits non-zero on a
# failed base health check so it can gate the rest of Level 1 backend checks.
#
# Usage: ./health_probe.sh <base_url> [health_path] [ready_path]

set -u

BASE_URL="${1:?usage: health_probe.sh <base_url> [health_path] [ready_path]}"
HEALTH_PATH="${2:-/health}"
READY_PATH="${3:-/ready}"

probe () {
  local label="$1" url="$2"
  local start end elapsed_ms code
  start=$(date +%s%N)
  code=$(curl -sS -m 10 -o /tmp/smoke_probe_body.$$ -w "%{http_code}" "$url" 2>/tmp/smoke_probe_err.$$)
  end=$(date +%s%N)
  elapsed_ms=$(( (end - start) / 1000000 ))
  echo "[$label] GET $url -> HTTP $code (${elapsed_ms}ms)" >&2
  if [ -s /tmp/smoke_probe_body.$$ ]; then
    echo "  body: $(head -c 300 /tmp/smoke_probe_body.$$)" >&2
  fi
  if [ -s /tmp/smoke_probe_err.$$ ]; then
    echo "  stderr: $(cat /tmp/smoke_probe_err.$$)" >&2
  fi
  rm -f /tmp/smoke_probe_body.$$ /tmp/smoke_probe_err.$$
  echo "$code"
}

health_code=$(probe "health" "${BASE_URL%/}${HEALTH_PATH}")
ready_code=$(probe "ready" "${BASE_URL%/}${READY_PATH}")

if [ "$health_code" != "200" ]; then
  echo "GATE: FAIL - health check did not return 200. Report backend.health as FAIL, mark dependent Level 1/3/4 items BLOCKED, stop here."
  exit 1
fi

if [ "$ready_code" != "200" ]; then
  echo "GATE: PARTIAL - health OK but readiness (DB or dependency) not confirmed."
  exit 2
fi

echo "GATE: PASS - health and readiness both OK."
exit 0
