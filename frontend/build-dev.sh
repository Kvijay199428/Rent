#!/bin/bash
set -e

echo "=== Building Rent Frontend Apps (dev) ==="
echo "=== Bakes VITE_APP_URL from frontend/.env.development (ngrok tunnel) so ==="
echo "=== share/WhatsApp/QR links point at dev instead of prod ==="

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
  echo "=== Loaded frontend/.env (VITE_* build vars) ==="
fi

if [ -f .env.development ]; then
  set -a
  . ./.env.development
  set +a
  echo "=== Loaded frontend/.env.development (VITE_APP_URL=${VITE_APP_URL:-<unset>}) ==="
else
  echo "=== WARNING: frontend/.env.development not found — VITE_APP_URL unset; ==="
  echo "=== getPublicAppUrl() will fall back to prod (rent.vijaykrsha.online) ==="
fi

echo ""
echo "=== Running the standard build (see build.sh) ==="
exec bash build.sh
