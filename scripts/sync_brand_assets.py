#!/usr/bin/env python3
"""Distribute the canonical PROPAURA brand assets to their live locations.

Canonical source tree (user-provided brand assets):
    assets/logo/propaura.svg   (vector lockup)
    assets/logo/propaura.png   (raster lockup - Logo.tsx <img> fallback)
    assets/fevicon/icon.svg    (vector mark/icon)
    assets/fevicon/fevicon.ico (pre-built multi-size 16..256 favicon)
    assets/qr/qr1024.png       (runtime QR mark raster, 1024x1024 RGBA)

This script copies (never regenerates) those files to:
    frontend/shared/brand/assets/{logo.svg,logo.png,icon.svg,favicon.ico}
    frontend/{admin,landing,landlord,tenant}-app/public/favicon.ico
    backend/app/static/propaura_mark.png        (runtime QR mark raster)

Fail-fast validators run before any copy:
    - SVGs parse and carry real <path> geometry; they are trusted as-is even
      though they embed their own <font>/<text> (self-contained glyph paths),
      so only external font/resource references are rejected.
    - favicon.ico is a true multi-size ICO (>= 2 embedded sizes incl. 16 & 32).
    - qr1024.png is 1024x1024 RGBA (square; byte twin of the runtime
      backend/app/static/propaura_mark.png).

Idempotent: copies only when bytes differ. Requires zero third-party imports
beyond stdlib + Pillow (no svglib/cairo/qrcode needed).
"""
from __future__ import annotations

import filecmp
import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "assets")
SHARED_BRAND = os.path.join(REPO, "frontend", "shared", "brand", "assets")
APP_PUBLICS = [
    "admin-app",
    "landing-app",
    "landlord-app",
    "tenant-app",
]

REQUIRED_ICO_MIN = 2  # favicon.ico must be multi-frame (>=2 embedded sizes)
REQUIRED_ICO_SIZES = {(16, 16), (32, 32)}


class AssetError(Exception):
    """Canonical asset failed validation; distribution is stopped."""


def validate_svg(path: str) -> None:
    """SVG must parse, contain path geometry, and not reference external fonts."""
    if not os.path.isfile(path):
        raise AssetError(f"missing canonical SVG: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise AssetError(f"SVG does not parse: {path}: {exc}") from exc
    tag = root.tag.rsplit("}", 1)[-1].lower()
    if tag != "svg":
        raise AssetError(f"not an <svg> root: {path} (tag={tag})")

    has_path = any(
        elem.tag.rsplit("}", 1)[-1].lower() == "path"
        and (elem.get("d") or "").strip()
        for elem in root.iter()
    )
    if not has_path:
        raise AssetError(f"SVG has no path geometry: {path}")

    for elem in root.iter():
        etag = elem.tag.rsplit("}", 1)[-1].lower()
        attr = " ".join(f"{k} {v}".lower() for k, v in (elem.attrib or {}).items())
        # Reject external font/resource references, but permit self-contained
        # embedded <font>/<glyph> outlines (how the Corel lockups are stored).
        # A <font-face> is only a problem if it actually sources an external font.
        if etag in ("font-face",) and (elem.get("src") or "").strip():
            raise AssetError(f"SVG <font-face> has an external src: {path}")
        if "xlink" in attr and ("http://" in attr or "https://" in attr):
            raise AssetError(f"SVG references external resources: {path}")
        if "url(" in attr and ("http://" in attr or "https://" in attr):
            raise AssetError(f"SVG references external URLs: {path}")

    print(f"  ok  svg  {os.path.relpath(path, REPO)}")


def validate_ico(path: str) -> None:
    if not os.path.isfile(path):
        raise AssetError(f"missing canonical ICO: {path}")
    with Image.open(path) as ico:
        ico.load()
        try:
            sizes = set(ico.ico.sizes())
        except Exception:
            sizes = {ico.size}
        if len(sizes) < REQUIRED_ICO_MIN or not REQUIRED_ICO_SIZES.issubset(sizes):
            raise AssetError(
                f"ICO must be multi-size incl. 16 & 32: {path} has {sorted(sizes)}"
            )
    print(f"  ok  ico  {os.path.relpath(path, REPO)}  {sorted(sizes)}")


def validate_qr_png(path: str) -> None:
    if not os.path.isfile(path):
        raise AssetError(f"missing canonical QR raster: {path}")
    with Image.open(path) as img:
        if img.size != (1024, 1024):
            raise AssetError(f"qr1024.png must be 1024x1024, got {img.size}")
        if img.mode != "RGBA":
            raise AssetError(f"qr1024.png must be RGBA, got {img.mode}")
    print(f"  ok  png  {os.path.relpath(path, REPO)}  (1024x1024 RGBA)")


def sync_file(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False):
        print(f"  =   {os.path.relpath(dst, REPO)}  (unchanged)")
        return
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        f.write(data)
    print(f"  ->  {os.path.relpath(dst, REPO)}  ({len(data)} bytes)")


def main() -> int:
    canonical = {
        "logo_svg": os.path.join(ASSETS, "logo", "propaura.svg"),
        "logo_png": os.path.join(ASSETS, "logo", "propaura.png"),
        "icon": os.path.join(ASSETS, "fevicon", "icon.svg"),
        "ico": os.path.join(ASSETS, "fevicon", "fevicon.ico"),
        "qr": os.path.join(ASSETS, "qr", "qr1024.png"),
    }

    print("=== Validating canonical assets ===")
    try:
        validate_svg(canonical["logo_svg"])
        validate_svg(canonical["icon"])
        validate_ico(canonical["ico"])
        validate_qr_png(canonical["qr"])
    except AssetError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("\n=== Distributing ===")
    sync_file(canonical["logo_svg"], os.path.join(SHARED_BRAND, "logo.svg"))
    sync_file(canonical["logo_png"], os.path.join(SHARED_BRAND, "logo.png"))
    sync_file(canonical["icon"], os.path.join(SHARED_BRAND, "icon.svg"))
    sync_file(canonical["ico"], os.path.join(SHARED_BRAND, "favicon.ico"))
    for app in APP_PUBLICS:
        sync_file(canonical["ico"], os.path.join(REPO, "frontend", app, "public", "favicon.ico"))
    sync_file(canonical["qr"], os.path.join(REPO, "backend", "app", "static", "propaura_mark.png"))

    print("\n=== Sync complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
