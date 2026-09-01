#!/usr/bin/env python3
"""Outline CorelDRAW brand SVGs (icon.svg, logo.svg) which reference embedded SVG
fonts ("Nevan RUS") into font-independent SVGs by converting each letter to a
<path>, replicating original text positions and advances.

Google Chrome / Edge dropped support for SVG path fonts, so the originals render
as tofu in every modern browser. This regenerates canonical brand assets into:

    frontend/shared/brand/assets/logo.svg     — wordmark (PROP + AURA)
    frontend/shared/brand/assets/icon.svg     — ringed P/A monogram (mark, 1566.89x1566.89, transparent)
    frontend/shared/brand/assets/favicon.svg  — monogram on white (favicon)

It also prints the inner lockup XML (rings + letters) that the QR service pastes
into ``PROPAURA_MARK_PATHS``.

Stdlib only. Re-runnable: python scripts/outline_brand_svg.py
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "frontend" / "shared" / "brand" / "assets"
BRAND_DIR = ROOT / "frontend" / "shared" / "brand"

SRC_ICON = ROOT / "icon.svg"
SRC_LOGO = ROOT / "logo.svg"

NAVY = "#151B54"
ORANGE = "#E5611B"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_css_classes(css: str) -> dict[str, dict[str, str]]:
    """Parse `.cls {prop:value;...}` blocks into a {classname: rules} map."""
    out: dict[str, dict[str, str]] = {}
    for block in re.finditer(r"\.([\w-]+)\s*\{([^}]*)\}", css):
        name, body = block.group(1), block.group(2)
        rules: dict[str, str] = {}
        for prop in body.split(";"):
            if ":" not in prop:
                continue
            k, _, v = prop.strip().partition(":")
            rules[k.strip()] = v.strip()
        out[name] = rules
    return out


def class_rules(elem: ET.Element, css_map: dict[str, dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for cls in (elem.get("class") or "").split():
        merged.update(css_map.get(cls, {}))
    return merged


def find_fonts(root: ET.Element) -> tuple[dict[str, str], float]:
    """Return {unicode_char: glyph_d} and default horiz advance."""
    fonts = [e for e in root.iter() if local(e.tag) == "font"]
    glyphs: dict[str, str] = {}
    default_adv = 751.0
    for font in fonts:
        default_adv = float(font.get("horiz-adv-x") or default_adv)
        for g in font.iter():
            if local(g.tag) != "glyph":
                continue
            uni = g.get("unicode")
            d = g.get("d")
            if uni and d:
                glyphs[uni] = d
    return glyphs, default_adv


class Letter:
    __slots__ = ("char", "transform", "d", "fill")

    def __init__(self, char: str, transform: str, d: str, fill: str) -> None:
        self.char = char
        self.transform = transform
        self.d = d
        self.fill = fill


def extract_letters(
    root: ET.Element,
    css_map: dict[str, dict[str, str]],
    glyphs: dict[str, str],
    default_adv: float,
) -> list[Letter]:
    letters: list[Letter] = []
    for text in root.iter():
        if local(text.tag) != "text":
            continue
        rules = class_rules(text, css_map)
        fill = rules.get("fill", NAVY) if not rules.get("fill", "").startswith("none") else NAVY
        size = float((rules.get("font-size") or "1000px").removesuffix("px"))
        scale = size / 1000.0
        start_x = float(text.get("x") or 0.0)
        baseline_y = float(text.get("y") or 0.0)
        content = "".join(text.itertext())
        advances: list[float] = []
        for ch in content:
            adv = default_adv
            for font in root.iter():
                if local(font.tag) != "font":
                    continue
                for g in font.iter():
                    if local(g.tag) != "glyph" or g.get("unicode") != ch:
                        continue
                    adv = float(g.get("horiz-adv-x") or adv)
                    break
                else:
                    continue
                break
            advances.append(adv)
        offset = 0.0
        for ch, adv in zip(content, advances):
            if ch not in glyphs:
                offset += adv
                continue
            transform = f"translate({start_x + offset:g} {baseline_y:g}) scale({scale:g} -{scale:g})"
            letters.append(Letter(ch, transform, glyphs[ch], fill))
            offset += adv
    return letters


def make_elem(tag: str, attrib: dict[str, str], children: list[ET.Element] = None) -> ET.Element:
    el = ET.Element(tag, attrib)
    for c in children or []:
        el.append(c)
    return el


def svg_tree(viewbox: str, children: list[ET.Element], width=None, height=None) -> ET.Element:
    attrib = {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": viewbox,
    }
    if width is not None:
        attrib.setdefault("width", width)
        attrib.setdefault("height", height)
    return make_elem("svg", attrib, children)


def pretty(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


# ---------------------------------------------------------------------------
# ICON — ringed P/A monogram
# ---------------------------------------------------------------------------

MARK_W = 1566.89
MARK_H = 1566.89


def build_icon() -> tuple[ET.Element, list[Letter], ET.Element]:
    """Flatten the fill-based root icon.svg: solid rings (fil0/fil1) +
    letter outlines (fil2/fil3), no stroke, no translation.
    """
    tree = ET.parse(SRC_ICON)
    root = tree.getroot()
    css_map = parse_css_classes("".join(s.text or "" for s in root.iter() if local(s.tag) == "style"))
    glyphs, default_adv = find_fonts(root)

    ring_class_to_fill = {
        "fil0": ORANGE,  # left ring
        "fil1": NAVY,    # right ring
    }
    rings: list[ET.Element] = []
    for path in root.iter():
        if local(path.tag) != "path":
            continue
        cls = next((c for c in (path.get("class") or "").split() if c in ring_class_to_fill), None)
        if cls is None:
            continue
        rings.append(make_elem("path", {"d": path.get("d", ""), "fill": ring_class_to_fill[cls]}))

    letters = extract_letters(root, css_map, glyphs, default_adv)

    base_group = make_elem(
        "g",
        {},
        rings
        + [
            make_elem(
                "g",
                {"transform": l.transform},
                [make_elem("path", {"d": l.d, "fill": l.fill})],
            )
            for l in letters
        ],
    )
    icon_svg = svg_tree(f"0 0 {MARK_W:g} {MARK_H:g}", [base_group])
    return icon_svg, letters, base_group


# ---------------------------------------------------------------------------
# LOGO — wordmark
# ---------------------------------------------------------------------------


def build_logo() -> tuple[ET.Element, list[Letter]]:
    tree = ET.parse(SRC_LOGO)
    root = tree.getroot()
    css_map = parse_css_classes("".join(s.text or "" for s in root.iter() if local(s.tag) == "style"))
    glyphs, default_adv = find_fonts(root)
    letters = extract_letters(root, css_map, glyphs, default_adv)
    children = [
        make_elem("g", {"transform": l.transform}, [make_elem("path", {"d": l.d, "fill": l.fill})])
        for l in letters
    ]
    logo_svg = svg_tree("0 0 21650.53 5094.95", children)
    return logo_svg, letters


# ---------------------------------------------------------------------------
# favicon — monogram on white
# ---------------------------------------------------------------------------


def build_favicon(icon_inner: ET.Element) -> ET.Element:
    white = make_elem("rect", {"x": "0", "y": "0", "width": f"{MARK_W:g}", "height": f"{MARK_W:g}", "fill": "#ffffff"})
    centered = make_elem(
        "g",
        {"transform": f"translate(0 {(MARK_W - MARK_H) / 2:g})"},
        [icon_inner],
    )
    return svg_tree(
        f"0 0 {MARK_W:g} {MARK_W:g}",
        [white, centered],
        width=f"{MARK_W:g}",
        height=f"{MARK_W:g}",
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    icon_svg, _, base_group = build_icon()
    logo_svg, _ = build_logo()
    favicon_svg = build_favicon(base_group)

    pretty(ASSETS_DIR / "icon.svg", icon_svg)
    pretty(ASSETS_DIR / "logo.svg", logo_svg)
    pretty(ASSETS_DIR / "fevicon.svg", favicon_svg)

    qr_xml = "\n".join(ET.tostring(c, encoding="unicode") for c in base_group)
    print("Generated assets:")
    for p in (ASSETS_DIR / "icon.svg", ASSETS_DIR / "logo.svg", ASSETS_DIR / "fevicon.svg"):
        print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size} bytes)")
    print()
    print("QR MARK_PATHS (indent 6sp, paste into qr_service.py PROPAURA_MARK_PATHS):")
    print(qr_xml)


if __name__ == "__main__":
    main()