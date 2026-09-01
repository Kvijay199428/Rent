#!/usr/bin/env python3
"""One-time (re)generation of the PROPAURA canonical brand asset tree.

Sources of truth (verified flattened, font-independent artwork):
    - frontend/shared/brand/assets/logo.svg   "PROP AURA" wordmark paths
    - frontend/shared/brand/assets/icon.svg   mark: half-disc lockup + P/A
    - backend/app/static/propaura_mark.png    rasterized mark (1024x1024 RGBA,
      transparent background, orange disc + navy ink) — the same bytes the
      QR code service validates against at runtime

Produces the canonical, committed tree under assets/:
    - assets/logo/propaura.svg    (copy of flattened logo.svg)
    - assets/favicon/icon.svg     (copy of flattened icon.svg)
    - assets/favicon/favicon.ico  (multi-size 16/24/32/48/64/128/256,
      mark letterboxed on a transparent square with a small margin)
    - assets/qr/qr1024.png        (canonical QR mark raster, byte-identical
      to backend/app/static/propaura_mark.png)
    - assets/qr/qr256/qr512/qr2048.png (square, ratio-preserving resizes)

Distribution to the live paths is scripts/sync_brand_assets.py (copy-only).
Run this script only when the artwork sources change; require Pillow.
"""
from __future__ import annotations

import os
import shutil

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(REPO, "frontend", "shared", "brand", "assets")
MARK_PNG = os.path.join(REPO, "backend", "app", "static", "propaura_mark.png")
ASSETS = os.path.join(REPO, "assets")

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
QR_SIZES = {2048, 1024, 512, 256}
MARK_SIDE = 1024
ICO_CANVAS = 1100  # symmetric ~3.7% margin around the mark for favicon breathing room


def _copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"  {os.path.relpath(dst, REPO)}  (from {os.path.relpath(src, REPO)})")


def main() -> int:
    checks = (
        (SHARED, True),
        (MARK_PNG, False),
    )
    for path, is_dir in checks:
        ok = os.path.isdir(path) if is_dir else os.path.isfile(path)
        if not ok:
            print(f"ERROR: missing source {path}")
            return 1

    print("=== Generating canonical assets/ ===")
    _copy(os.path.join(SHARED, "logo.svg"), os.path.join(ASSETS, "logo", "propaura.svg"))
    _copy(os.path.join(SHARED, "icon.svg"), os.path.join(ASSETS, "favicon", "icon.svg"))

    mark = Image.open(MARK_PNG)
    mark.load()
    if mark.mode != "RGBA" or mark.size != (MARK_SIDE, MARK_SIDE):
        print(f"ERROR: mark PNG must be RGBA {MARK_SIDE}x{MARK_SIDE}, got {mark.mode} {mark.size}")
        return 1

    # ── favicon.ico: letterbox the mark on a transparent square, multi-size ─
    canvas = Image.new("RGBA", (ICO_CANVAS, ICO_CANVAS), (0, 0, 0, 0))
    off = (ICO_CANVAS - MARK_SIDE) // 2
    canvas.paste(mark, (off, off), mark)
    favicon_ico = os.path.join(ASSETS, "favicon", "favicon.ico")
    os.makedirs(os.path.dirname(favicon_ico), exist_ok=True)
    canvas.save(favicon_ico, format="ICO", sizes=ICO_SIZES)
    print(f"  {os.path.relpath(favicon_ico, REPO)}  (multi-size {len(ICO_SIZES)})")

    # ── QR mark rasters (square, ratio-preserving resizes) ────────────────
    _copy(MARK_PNG, os.path.join(ASSETS, "qr", "qr1024.png"))
    for n in sorted(QR_SIZES - {1024}, reverse=True):
        img = mark.resize((n, n), Image.LANCZOS)
        out = os.path.join(ASSETS, "qr", f"qr{n}.png")
        img.save(out, format="PNG")
        print(f"  {os.path.relpath(out, REPO)}  ({img.size[0]}x{img.size[1]})")

    print("=== Done. Run scripts/sync_brand_assets.py to distribute. ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())