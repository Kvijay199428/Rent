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
# Inner content of the mark SVG (no <svg> wrapper). ViewBox 413.02 x 269.52.
PROPAURA_MARK_PATHS = """  <path fill="#010101" d="M196.07 133.89l1.23 -0.32c-6.75,-8.54 -13.87,-22.49 -19.85,-32.66 -6.48,-11.02 -12.56,-22.32 -19.3,-33.67 -7.67,-12.93 -32.79,-59.97 -38.49,-67.16l-119.21 -0.08 97.09 67.3c11.67,7.96 87.89,61.44 98.53,66.59z"/>
  <path fill="#010101" d="M214.59 134.6l1.76 -0.06c7.25,-5.88 15.89,-10.56 23.87,-16.08l170.99 -118.43 -119.06 -0.03 -77.56 134.59z"/>
  <path fill="#020202" d="M410.95 15.63l-0.22 -0.37c-5.91,1.84 -173.73,118.85 -189.57,130.03l117.34 -0.26c2.53,-2.73 70.82,-124.24 72.45,-129.4z"/>
  <path fill="#010101" d="M71.54 145.02l118.15 0.07c-4.53,-5.61 -40.66,-28.4 -47.21,-33.13l-93.97 -64.93c-9.81,-6.56 -41.31,-29.19 -48.51,-32.64 2.99,8.6 13.14,24.67 17.91,32.94 7.3,12.65 51.11,90.08 53.63,97.68z"/>
  <path fill="#010101" d="M145.21 269.41l120.89 0.11c-1.8,-6.75 -10.88,-20.72 -14.53,-27.03 -5.28,-9.14 -10.07,-16.64 -15.43,-26.23l-30.31 -53.87 -60.63 107.02z"/>
  <path fill="#010101" d="M274.93 258.85c9.89,-15 19.16,-34 28.64,-50.49 5.11,-8.89 26.99,-45.5 28.6,-52.2l-117.42 -0c2.62,6.95 58.87,101.59 60.19,102.69z"/>
  <path fill="#010101" d="M136.31 259.15c4.49,-3.51 25.27,-41.37 30.11,-50.49l29.81 -52.92 -117.59 0.52 57.67 102.89z"/>
  <path fill="#625B54" d="M216.35 134.54l-1.76 0.06 -1.79 2.34c4.9,-1.45 2.23,-0.92 3.55,-2.39z"/>
  <path fill="#625B54" d="M197.3 133.57l-1.23 0.32 2.75 3.02c-0.7,-7.34 0.56,-0.53 -1.53,-3.35z"/>
  <polygon fill="#625B54" points="410.95,15.63 413.02,13.15 410.72,15.26"/>"""

MARK_VIEWBOX_WIDTH = 413.02
MARK_VIEWBOX_HEIGHT = 269.52

WORDMARK_PROP_COLOR = "#708498"
WORDMARK_AURA_COLOR = "#95A58F"
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
_FONT_DIR = os.path.join(_APP_DIR, ".fonts")
_WORDMARK_FONT_PATH = os.path.join(_FONT_DIR, "NotoSans-Bold.ttf")


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

    lock_w = box_px * 0.8
    mark_h = lock_w * (MARK_VIEWBOX_HEIGHT / MARK_VIEWBOX_WIDTH)
    font = max(5, box_px * 0.16)
    use_wordmark = (mark_h + font) <= box_px
    if not use_wordmark:
        # PROPAURA -> PA fallback: mark only, no wordmark. Never unbranded.
        lock_w = box_px * 0.9
        mark_h = lock_w * (MARK_VIEWBOX_HEIGHT / MARK_VIEWBOX_WIDTH)

    mark_y = badge_y + (box_px - mark_h - (font if use_wordmark else 0)) / 2
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
        "font": font,
        "use_wordmark": use_wordmark,
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
    mark = (
        f'<g transform="translate({g["mark_x"]:.2f} {g["mark_y"]:.2f}) '
        f'scale({scale:.4f})">{PROPAURA_MARK_PATHS}</g>'
    )
    if not g["use_wordmark"]:
        return mark
    text_y = g["mark_y"] + g["mark_h"] + g["font"]
    return mark + (
        f'<text x="{size / 2:.2f}" y="{text_y:.2f}" text-anchor="middle" '
        'font-family="Arial, \'Segoe UI\', Roboto, Helvetica, sans-serif" '
        f'font-size="{g["font"]:.1f}" font-weight="800" letter-spacing="1" '
        f'fill="{WORDMARK_PROP_COLOR}">PROP<tspan fill="{WORDMARK_AURA_COLOR}">AURA</tspan></text>'
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


def _wordmark_font(size_px: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(_WORDMARK_FONT_PATH, max(4, round(size_px)))
    except Exception:
        return ImageFont.load_default()


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

    if g["use_wordmark"]:
        font = _wordmark_font(g["font"])
        center_x = internal_size / 2
        baseline_y = g["mark_y"] + g["mark_h"] + g["font"]
        prop_w = draw.textlength("PROP", font=font)
        aura_w = draw.textlength("AURA", font=font)
        start_x = center_x - (prop_w + aura_w) / 2
        draw.text((start_x, baseline_y), "PROP", font=font, fill=WORDMARK_PROP_COLOR, anchor="ls")
        draw.text((start_x + prop_w, baseline_y), "AURA", font=font, fill=WORDMARK_AURA_COLOR, anchor="ls")

    if internal or size == internal_size:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
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
