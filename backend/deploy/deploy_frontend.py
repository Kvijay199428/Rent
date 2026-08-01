#!/usr/bin/env python3
"""
Build and assemble all Rent frontend apps for Cloudflare Pages.

Builds each app independently, then assembles into a single output directory
that can be deployed to Cloudflare Pages as one project.

Output structure:
    build-output/
    └── rent/
        ├── index.html              ← landing-app
        ├── favicon.svg
        ├── assets/                 ← landing-app assets
        ├── admin/
        │   ├── index.html          ← admin-app
        │   └── assets/
        ├── tenant/
        │   ├── index.html          ← tenant-app
        │   └── assets/
        └── landlord/
            ├── index.html          ← landlord-app
            └── assets/

Usage:
    python backend/deploy/deploy_frontend.py              # build all apps
    python backend/deploy/deploy_frontend.py --skip-landing  # skip landing build
    python backend/deploy/deploy_frontend.py --no-build       # only assemble (skip npm)
"""

import os
import sys
import shutil
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "build-output")

APPS = [
    {
        "name": "landing",
        "dir": "../frontend/landing-app",
        "output": "rent",
        "skip_flag": "--skip-landing",
    },
    {
        "name": "platform-admin",
        "dir": "../frontend/admin-app",
        "output": "rent/admin",
        "skip_flag": "--skip-admin",
    },
    {
        "name": "tenant",
        "dir": "../frontend/tenant-app",
        "output": "rent/tenant",
        "skip_flag": "--skip-tenant",
    },
    {
        "name": "landlord",
        "dir": "../frontend/landlord-app",
        "output": "rent/landlord",
        "skip_flag": "--skip-landlord",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(description="Build Rent Frontend for Cloudflare Pages")
    parser.add_argument("--no-build", action="store_true",
                        help="Skip npm builds, only assemble from existing dist/")
    parser.add_argument("--skip-landing", action="store_true", help="Skip landing-app build")
    parser.add_argument("--skip-admin", action="store_true", help="Skip admin-app build")
    parser.add_argument("--skip-tenant", action="store_true", help="Skip tenant-app build")
    parser.add_argument("--skip-landlord", action="store_true", help="Skip landlord-app build")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    return parser.parse_args()


def build_app(app, no_build=False):
    if no_build:
        print(f"\n=== Skipping build for {app['name']} (--no-build) ===")
        return

    app_dir = os.path.join(BASE_DIR, app["dir"])
    dist_dir = os.path.join(app_dir, "dist")

    if not os.path.isdir(app_dir):
        print(f"\n=== WARNING: {app['name']} directory not found at {app_dir} ===")
        return

    print(f"\n=== Building {app['name']} ===")

    # Check for package.json
    if not os.path.isfile(os.path.join(app_dir, "package.json")):
        print(f"  WARNING: No package.json found in {app['dir']}")
        return

    result = subprocess.run(
        "npm install && npm run build",
        cwd=app_dir,
        shell=True,
        timeout=300,
    )

    if result.returncode != 0:
        print(f"\nERROR: Build failed for {app['name']}")
        sys.exit(1)

    if not os.path.isdir(dist_dir):
        print(f"  WARNING: dist/ not found after build for {app['name']}")
        sys.exit(1)

    print(f"  Build complete: {app['name']}")


def assemble(output_dir, skip_flags):
    """Copy built dist/ directories into the assembled output."""
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    for app in APPS:
        # Check if this app was skipped
        flag_name = app["skip_flag"].replace("--skip-", "").replace("-", "_")
        if flag_name.startswith("skip_"):
            flag_name = flag_name[5:]  # remove "skip_" prefix
        if skip_flags.get(flag_name, False):
            print(f"  Skipping {app['name']} (flag)")
            continue

        src_dist = os.path.join(BASE_DIR, app["dir"], "dist")
        dst_dir = os.path.join(output_dir, app["output"])

        if os.path.isdir(src_dist):
            shutil.copytree(src_dist, dst_dir, dirs_exist_ok=True)
            print(f"  Copied {app['name']} → {app['output']}/")
        else:
            print(f"  WARNING: {app['name']} dist not found at {src_dist}")

    # List final structure
    print(f"\nOutput directory: {output_dir}")
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(output_dir, "").count(os.sep)
        indent = "  " * level
        basename = os.path.basename(root)
        if level <= 2:
            print(f"  {indent}{basename}/")


def main():
    args = parse_args()
    output_dir = args.output

    print("=" * 60)
    print(" RENT FRONTEND BUILD")
    print("=" * 60)
    print(f"  No build: {'YES' if args.no_build else 'no'}")
    print(f"  Output:   {output_dir}")
    print("=" * 60)

    skip_flags = {
        "landing": args.skip_landing,
        "admin": args.skip_admin,
        "tenant": args.skip_tenant,
        "landlord": args.skip_landlord,
    }

    for app in APPS:
        flag_name = app["skip_flag"].replace("--skip-", "").replace("-", "_")
        if flag_name.startswith("skip_"):
            flag_name = flag_name[5:]
        if skip_flags.get(flag_name, False):
            print(f"\n=== Skipping {app['name']} ===")
            continue
        build_app(app, no_build=args.no_build)

    assemble(output_dir, skip_flags)

    print("\n" + "=" * 60)
    print(" Build complete.")
    print(f" Upload '{output_dir}/' to Cloudflare Pages.")
    print("=" * 60)


if __name__ == "__main__":
    main()
