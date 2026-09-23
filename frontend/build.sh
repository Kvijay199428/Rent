#!/bin/bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== Building Rent Frontend Apps ==="

load_env() {
  local f="$1"
  [ -f "$f" ] || return 1
  # Export only NON-EMPTY VITE_* values from the env file into the shell.
  # Empty values are deliberately skipped: Vite's env loading assigns process.env
  # the HIGHEST priority (a present-but-empty VITE_API_BASE_URL in process.env
  # would blank the production origin that's set in the committed .env.production).
  # Dev same-origin stays correct because Vite reads .env/.env.development itself.
  # We also never overwrite a var already set to a non-empty value (CI wins).
  local line key val current
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                       # strip inline comments
    line="${line%"${line##*[![:space:]]}"}"  # trim trailing whitespace
    [ -n "$line" ] || continue
    key="${line%%=*}"
    key="${key//[^A-Za-z0-9_]/}"
    case "$key" in
      VITE_*)
        val="${line#*=}"
        val="${val%\"}"; val="${val#\"}"
        [ -n "$val" ] || continue            # skip empty values (see above)
        # eval (not ${!key}) so this works on minimal bash (w64devkit) too.
        current=""; eval "current=\"\${$key:-}\""
        if [ -z "$current" ]; then           # only set if not already non-empty
          export "$key=$val"
        fi
        ;;
    esac
  done < "$f"
  echo "=== Loaded $f (non-empty VITE_* build vars, incoming env preserved) ==="
  return 0
}

# Priority: incoming env vars > frontend/.env > the .env/ source of truth.
if ! load_env .env; then
  if load_env ../.env/.env.release; then
    :
  elif load_env ../.env/.env.development; then
    :
  else
    echo "=== WARNING: no env found — VITE_* build vars unset ==="
  fi
fi

APPS="landing-app admin-app landlord-app tenant-app"

echo ""
echo "=== Mirroring canonical brand assets into app public dirs ==="
# Pure copy from the canonical assets/ tree (see scripts/sync_brand_assets.py).
for app in $APPS; do
  if [ -f "../assets/fevicon/fevicon.ico" ]; then
    cp "../assets/fevicon/fevicon.ico" "$app/public/favicon.ico"
    echo "  favicon.ico -> $app/public/"
  fi
  # Retire any stale fevicon.svg left by an older build.
  rm -f "$app/public/fevicon.svg"
done

for app in $APPS; do
  echo ""
  echo "=== $app ==="
  (cd "$app" && npm install && npm run build)
done

echo ""
echo "=== Assembling output ==="
rm -rf build-output
mkdir -p build-output

# Landing app -> root
cp -r landing-app/dist/* build-output/
# Admin app -> /admin
mkdir -p build-output/admin
cp -r admin-app/dist/* build-output/admin/
# Landlord app -> /landlord
mkdir -p build-output/landlord
cp -r landlord-app/dist/* build-output/landlord/
# Tenant app trailing base -> /t (assets); deep links served by _middleware
mkdir -p build-output/t
cp -r tenant-app/dist/* build-output/t/

mkdir -p build-output/functions
cp -r functions/* build-output/functions/

cat > build-output/_redirects << 'EOF'
# SPA rewrite rules (status 200): an unmatched path inside an app serves that
# app's index.html. Static files always win over _redirects, so /assets/* and
# /landlord/assets/* /admin/assets/* /t/assets/* still serve the raw assets.
# This is the durable per-app fallback; build-output/functions/_middleware.js
# covers the same paths plus the canonical tenant portal URLs
# (/tenant/{landlordUuid}/QR/{property}/{tenant}/{token}) when Pages Functions
# are enabled.
/admin/*      /admin/index.html    200
/landlord/*   /landlord/index.html 200
/t/*          /t/index.html        200
/tenant/*     /t/index.html        200
# Complete drop: landing app is served at / directly. No root redirect.
# Old /rent deep links canonicalize to / (also breaks stale cached /rent bodies).
/rent/*  /  308
EOF

cat > build-output/_headers << 'EOF'
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/*.js
  Cache-Control: public, max-age=31536000, immutable
/*.css
  Cache-Control: public, max-age=31536000, immutable
/*.html
  Cache-Control: public, max-age=0, must-revalidate
EOF


cat > build-output/_routes.json << 'EOF'
{
  "version": 1,
  "include": [
    "/*"
  ],
  "exclude": [
    "/assets/*",
    "/admin/assets/*",
    "/landlord/assets/*",
    "/t/assets/*",
    "/*.js",
    "/*.css",
    "/*.png",
    "/*.jpg",
    "/*.jpeg",
    "/*.gif",
    "/*.svg",
    "/*.ico",
    "/*.woff2",
    "/*.woff",
    "/*.eot",
    "/*.ttf",
    "/favicon.ico"
  ]
}
EOF

echo ""
echo "=== Build complete ==="/
echo "Output: build-output/"
ls -la build-output/
echo ""
echo "--- _redirects ---"
cat build-output/_redirects
