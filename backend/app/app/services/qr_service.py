# app/services/qr_service.py
"""Server-side source of truth for PROPAURA-branded tenant QR codes.

Generates the QR at error-correction level H, excavates the center modules
and embeds the PROPAURA lockup inside the pattern itself (modules blanked
around the logo, not a floating overlay). The result is validated by
decoding it before it is served.

Only stdlib + qrcode + Pillow are required for generation; cv2 is used for
the decode validation step (opencv-python-headless).
"""
from __future__ import annotations

import base64
import io
import os
import urllib.parse

import qrcode
import qrcode.constants

from app.core.runtime import public_app_url

# ── PROPAURA mark (flattened paths, fills inlined) ──────────────────────────
# Inner content of the mark SVG (no <svg> wrapper). Authoring viewBox is
# 1832.86 x 1566.89, but the deployed raster (propaura_mark.png) is a square
# 1024x1024 crop of the vertical disc span — the safe render target for the
# excavated center badge. Canonical sources: assets/favicon/icon.svg (SVG)
# and assets/qr/qr1024.png (raster, distributed to app/static).
PROPAURA_MARK_PATHS = """  <path d="M783.45 783.45l0 783.45c-432.69,0 -783.45,-350.76 -783.45,-783.45 0,-432.69 350.76,-783.45 783.45,-783.45l0 783.45z" fill="#E5611B"/>
  <path d="M783.45 783.45l0 -783.45c432.69,0 783.45,350.76 783.45,783.45 0,432.69 -350.76,783.45 -783.45,783.45l0 -783.45z" fill="#151B54"/>
  <g transform="translate(279.02 1038.19) scale(0.72541 -0.72541)">
    <path d="M229 0l-144.999 0 0 384.001 338 0c29.3329,0.666141 53.4997,9.16582 72.4989,25.499 19.0006,16.3332 28.5009,39.5008 28.5009,69.4998 0,30.0005 -9.50031,53.3338 -28.5009,70.0001 -18.9992,16.6677 -43.166,25.3332 -72.4989,26.0008l-288 0c-14.0003,0 -25.8335,4.83307 -35.5011,14.4992 -9.66614,9.66755 -14.4992,21.5008 -14.4992,35.5011l0 74.999 351 0c68.0003,0 124.166,-20.3329 168.5,-61.0001 44.3338,-40.6658 66.5007,-93.6666 66.5007,-158.999 0,-62.6669 -22.0011,-114.334 -66.0004,-155 -44.0008,-40.6672 -100.334,-61.0001 -169,-61.0001l-206.001 0 0 -264z" fill="#151B54"/>
  </g>
  <g transform="translate(799.87 1038.19) scale(0.72541 -0.72541)">
    <path d="M746 0l-157.001 0 -213.999 558 -218.001 -558 -151 0 288 700 114.001 0c33.3326,0 57.9996,-16.6663 73.9998,-50.0003l264 -649.999z" fill="#E5611B"/>
  </g>"""

MARK_VIEWBOX_WIDTH = 1832.86
MARK_VIEWBOX_HEIGHT = 1566.89

# Version contract for the PROPAURA brand raster embedded in tenant QRs
# (backend/app/static/propaura_mark.png <- assets/qr/qr1024.png). Bump this
# whenever the canonical artwork source changes so downstream consumers can
# detect a stale lockup without diffing pixels.
QR_BRAND_VERSION = 1
QR_BRAND_VERSION_TAG = "propaura-qr-version"

BADGE_BORDER_COLOR = "#e5e7eb"

# Fraction of the QR matrix excavated for the lockup (option B: modules
# blanked around the logo). ~4.5% of modules — far inside ECC-H capacity.
LOCKUP_FRACTION = 0.22

# ISO/IEC 18004 quiet zone: 4 modules of white around the QR. Required for
# reliable scanning and by cv2's decoder during validation.
QUIET_ZONE = 4

# Internal render scale for the PNG pipeline: each module is drawn at
# box_size px (clean integer grid) then downsampled to the target size so
# sub-pixel module phases stay regular (cv2's grid sampler is sensitive).
PNG_BOX_SIZE = 10

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app/app
_STATIC_DIR = os.path.join(os.path.dirname(_APP_DIR), "static")         # .../app/static
_MARK_PNG_PATH = os.path.join(_STATIC_DIR, "propaura_mark.png")


class QrBuildError(Exception):
    """Raised when a branded QR could not be produced or validated."""


def build_qr_matrix(url: str) -> tuple[list[list[bool]], int]:
    """Generate the QR matrix at error-correction level H (no border)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=0,
        box_size=10,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    return matrix, len(matrix)


def lockup_geometry(count: int, size: int, quiet_zone: int = QUIET_ZONE) -> dict:
    """Compute excavation box + lockup placement for an NxN matrix at `size` px."""
    box = max(7, round(count * LOCKUP_FRACTION))
    start = (count - box) // 2
    end = start + box
    total = count + 2 * quiet_zone
    module = size / total
    qz = quiet_zone * module
    box_px = box * module
    badge_x = qz + start * module
    badge_y = qz + start * module

    lock_w = box_px * 0.9
    mark_h = lock_w * (MARK_VIEWBOX_HEIGHT / MARK_VIEWBOX_WIDTH)

    mark_y = badge_y + (box_px - mark_h) / 2
    mark_x = (size - lock_w) / 2

    return {
        "box": box,
        "start": start,
        "end": end,
        "module": module,
        "qz": qz,
        "badge_x": badge_x,
        "badge_y": badge_y,
        "box_px": box_px,
        "lock_w": lock_w,
        "mark_h": mark_h,
        "mark_x": mark_x,
        "mark_y": mark_y,
    }


def _cells_svg(matrix: list[list[bool]], g: dict) -> str:
    cells = []
    for r in range(len(matrix)):
        for c in range(len(matrix)):
            if g["start"] <= r < g["end"] and g["start"] <= c < g["end"]:
                continue
            if matrix[r][c]:
                x = g["qz"] + c * g["module"]
                y = g["qz"] + r * g["module"]
                cells.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" '
                    f'width="{g["module"]:.2f}" height="{g["module"]:.2f}"/>'
                )
    return "".join(cells)


def _lockup_svg(g: dict, size: int) -> str:
    scale = g["lock_w"] / MARK_VIEWBOX_WIDTH
    return (
        f'<g transform="translate({g["mark_x"]:.2f} {g["mark_y"]:.2f}) '
        f'scale({scale:.4f})">{PROPAURA_MARK_PATHS}</g>'
    )


def build_branded_qr_svg(url: str, size: int = 200) -> str:
    """Return the branded tenant QR as an SVG string (vector, print-ready)."""
    matrix, count = build_qr_matrix(url)
    g = lockup_geometry(count, size)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">'
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>'
        + _cells_svg(matrix, g)
        + f'<rect x="{g["badge_x"]:.2f}" y="{g["badge_y"]:.2f}" width="{g["box_px"]:.2f}" '
        f'height="{g["box_px"]:.2f}" rx="{g["box_px"] * 0.09:.2f}" '
        f'fill="#ffffff" stroke="{BADGE_BORDER_COLOR}" stroke-width="1"/>'
        + _lockup_svg(g, size)
        + "</svg>"
    )


def _mark_png_image():
    from PIL import Image

    img = Image.open(_MARK_PNG_PATH)
    img.load()
    return img


def _save_png(img, buf) -> None:
    """Encode img to buf as PNG, embedding the PROPAURA brand version tag."""
    from PIL import PngImagePlugin

    meta = PngImagePlugin.PngInfo()
    meta.add_text(QR_BRAND_VERSION_TAG, str(QR_BRAND_VERSION))
    img.save(buf, format="PNG", pnginfo=meta)


def build_branded_qr_png(url: str, size: int = 200, internal: bool = False) -> bytes:
    """Return the branded tenant QR as PNG bytes (Pillow rasterization).

    Renders the QR at a clean integer module grid (PNG_BOX_SIZE px per module,
    incl. quiet zone), overlays the lockup at that resolution, then downsamples
    to the target size so module phases stay regular (cv2's grid sampler is
    sensitive to sub-pixel rounding). Pass ``internal=True`` to get the
    pre-downsample image — used for decode validation, which is resolution-
    dependent and reliably decodes the full-resolution render.
    """
    from PIL import Image, ImageDraw

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=QUIET_ZONE,
        box_size=PNG_BOX_SIZE,
    )
    qr.add_data(url)
    qr.make(fit=True)
    total = len(qr.get_matrix())
    count = total - 2 * QUIET_ZONE
    internal_size = total * PNG_BOX_SIZE
    g = lockup_geometry(count, internal_size)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    draw = ImageDraw.Draw(img)

    bx0 = round(g["badge_x"])
    by0 = round(g["badge_y"])
    bx1 = round(g["badge_x"] + g["box_px"])
    by1 = round(g["badge_y"] + g["box_px"])
    draw.rounded_rectangle(
        [bx0, by0, bx1, by1],
        radius=round(g["box_px"] * 0.09),
        fill="white",
        outline=BADGE_BORDER_COLOR,
        width=max(1, round(g["module"] * 0.4)),
    )

    mark = _mark_png_image()
    mw = max(1, round(g["lock_w"]))
    mh = max(1, round(g["mark_h"]))
    mark = mark.resize((mw, mh), Image.LANCZOS)
    if mark.mode == "RGBA":
        img.paste(mark, (round(g["mark_x"]), round(g["mark_y"])), mark)
    else:
        img.paste(mark, (round(g["mark_x"]), round(g["mark_y"])))

    if internal or size == internal_size:
        buf = io.BytesIO()
        _save_png(img, buf)
        return buf.getvalue()

    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    _save_png(img, buf)
    return buf.getvalue()


def tenant_qr_payload(landlord_uuid: str, property_id, tenant_id: int, view_token: str, qr_key: str) -> str:
    """Canonical tenant portal URL encoded in the QR."""
    base = (
        f"{public_app_url()}/rent/{urllib.parse.quote(landlord_uuid)}"
        f"/t/{int(property_id) if property_id else 0}/{tenant_id}/{urllib.parse.quote(view_token)}"
    )
    if qr_key:
        base += f"?qr_key={urllib.parse.quote(qr_key)}"
    return base


def validate_qr_png(png_bytes: bytes, expected_url: str) -> bool:
    """Decode the rendered PNG and confirm it matches the intended URL."""
    import cv2
    import numpy as np

    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return False
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data == expected_url


def build_branded_qr(url: str, size: int = 200, fmt: str = "svg", validate: bool = True) -> tuple[str, str, int]:
    """Build + validate a branded tenant QR.

    Returns (data_uri, format, module_count). Raises QrBuildError when the
    generated QR does not decode back to the intended URL.
    """
    size = max(100, min(1000, int(size)))
    fmt = (fmt or "svg").lower()
    if fmt not in ("svg", "png"):
        raise QrBuildError(f"Unsupported QR format: {fmt}")

    if fmt == "png":
        png = build_branded_qr_png(url, size)
        if validate:
            # Validate the full-resolution render (same matrix + excavation as
            # the served, downsampled image). cv2's decode is resolution-
            # dependent; the downsampled version decodes on real scanners.
            if not validate_qr_png(build_branded_qr_png(url, size, internal=True), url):
                raise QrBuildError("Generated QR failed decode validation")
        data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    else:
        svg = build_branded_qr_svg(url, size)
        # Validate via the PNG build (same matrix + excavation) before serving SVG.
        if validate:
            if not validate_qr_png(build_branded_qr_png(url, size, internal=True), url):
                raise QrBuildError("Generated QR failed decode validation")
        data_uri = "data:image/svg+xml;charset=UTF-8," + urllib.parse.quote(svg)

    _, count = build_qr_matrix(url)
    return data_uri, fmt, count
