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
  (cd "$app" && npm ci && npm run build)
done

echo ""
echo "=== Assembling output ==="
rm -rf build-output
mkdir -p build-output/rent

cp -r landing-app/dist/* build-output/rent/
mkdir -p build-output/rent/admin
cp -r admin-app/dist/* build-output/rent/admin/
mkdir -p build-output/rent/landlord
cp -r landlord-app/dist/* build-output/rent/landlord/
mkdir -p build-output/rent/t
cp -r tenant-app/dist/* build-output/rent/t/

mkdir -p build-output/functions
cp -r functions/* build-output/functions/

cat > build-output/_redirects << 'EOF'
# Root redirect: bare domain -> landing app
/ /rent/ 301
EOF

cat > build-output/_headers << 'EOF'
/rent/assets/*
  Cache-Control: public, max-age=31536000, immutable
/rent/*.js
  Cache-Control: public, max-age=31536000, immutable
/rent/*.css
  Cache-Control: public, max-age=31536000, immutable
/rent/*.html
  Cache-Control: public, max-age=0, must-revalidate
EOF

echo ""
echo "=== Build complete ==="
echo "Output: build-output/"
ls -la build-output/rent/
echo ""
echo "--- _redirects ---"
cat build-output/_redirects
