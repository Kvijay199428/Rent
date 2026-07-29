#!/bin/bash
set -e

echo "=== Building Rent Frontend Apps ==="

APPS="landing-app platform-admin-app landlord-app tenant-app"

for app in $APPS; do
  echo ""
  echo "=== $app ==="
  npm --prefix "$app" ci
  npm --prefix "$app" run build
done

echo ""
echo "=== Assembling output ==="
rm -rf build-output
mkdir -p build-output/rent

cp -r landing-app/dist/* build-output/rent/
mkdir -p build-output/rent/admin
cp -r platform-admin-app/dist/* build-output/rent/admin/
mkdir -p build-output/rent/landlord
cp -r landlord-app/dist/* build-output/rent/landlord/
mkdir -p build-output/rent/tenant
cp -r tenant-app/dist/* build-output/rent/tenant/

echo ""
echo "=== Build complete ==="
echo "Output: build-output/"
ls -la build-output/rent/
