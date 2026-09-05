#!/bin/bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

# Builds each Rent frontend app into a SEPARATE dist-dev/ directory pointed at
# the DEV API (ngrok tunnel) instead of prod. This is what the dev backend
# router (backend/app/app/pages/frontend.py) serves, so every dev deploy calls
# the dev API — never colliding with the prod api.vijaykrsha.online origin.
#
# Prod builds are unaffected: they keep writing to the standard dist/ and
# build-output/ via build.sh with .env.production.
#
# The dev API base URL is expected as the VITE_API_BASE_URL environment
# variable (deploy.py reads it from root .env.development and passes it in).
# It may also be derived from PUBLIC_APP_URL.

DEV_API="${VITE_API_BASE_URL:-}"
if [ -z "$DEV_API" ] && [ -n "$PUBLIC_APP_URL" ]; then
  DEV_API="$PUBLIC_APP_URL"
fi
if [ -z "$DEV_API" ]; then
  echo "ERROR: VITE_API_BASE_URL (or PUBLIC_APP_URL) is required for the dev dist build." >&2
  exit 1
fi
# Strip a single trailing slash.
DEV_API="${DEV_API%/}"
echo "=== Dev API base: $DEV_API ==="

# Mirror canonical brand assets (same as build.sh).
APPS="landing-app admin-app landlord-app tenant-app"
for app in $APPS; do
  if [ -f "../assets/fevicon/fevicon.ico" ]; then
    cp "../assets/fevicon/fevicon.ico" "$app/public/favicon.ico"
  fi
  rm -f "$app/public/fevicon.svg"
done

# Build each app into dist-dev with the dev API base explicitly exported so it
# overrides .env.production (Vite treats existing process.env VITE_* as highest
# priority). outDir is set via the CLI so prod dist/ stays untouched.
for app in $APPS; do
  echo ""
  echo "=== $app (dev dist) ==="
  (cd "$app" && VITE_API_BASE_URL="$DEV_API" npx vite build --outDir dist-dev)
done

echo ""
echo "=== Dev dists built ==="
for app in $APPS; do
  echo "  $app/dist-dev/"
done
