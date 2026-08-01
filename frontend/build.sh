#!/bin/bash
set -e

echo "=== Building Rent Frontend Apps ==="

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
  echo "=== Loaded frontend/.env (VITE_* build vars) ==="
else
  echo "=== WARNING: frontend/.env not found — VITE_* build vars unset ==="
fi

APPS="landing-app admin-app landlord-app tenant-app"

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
mkdir -p build-output/rent/tenant
cp -r tenant-app/dist/* build-output/rent/tenant/

cat > build-output/_redirects << 'EOF'
# SPA fallback: all routes under /rent/* serve index.html
/rent/admin/*   /rent/admin/index.html   200
/rent/landlord/* /rent/landlord/index.html 200
/rent/t/*       /rent/t/index.html        200
/rent/*         /rent/index.html          200
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
