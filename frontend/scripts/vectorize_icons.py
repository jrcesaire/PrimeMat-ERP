#!/usr/bin/env python
"""Vectorise les visuels d'icônes en SVG, en conservant leur forme exacte.

Chaîne : PNG/JPG -> vtracer (tracé de contours) -> SVG nettoyé.

Contrairement à une réécriture « à la main », le tracé automatique reproduit
fidèlement l'original. `--remap-colors` (défaut) remplace ensuite chaque couleur
distincte par le jeton du thème le plus proche ; `--keep-colors` conserve les
couleurs d'origine.

Usage :
    python vectorize_icons.py --src <dossier_images> --out <dossier_svg>
        [--remap-colors|--keep-colors]

Dépendances : ``pip install vtracer pillow``
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import vtracer
except ImportError:  # pragma: no cover
    sys.exit("vtracer manquant : pip install vtracer")

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow manquant : pip install pillow")


#: Jetons du design system, avec leur teinte par défaut (voir `globals.css`).
TOKENS: dict[str, tuple[float, float, float]] = {
    "primary": (250.0, 0.62, 0.58),  # violet #6852D6
    "secondary": (164.0, 0.61, 0.33),  # vert  #21876B
    "accent": (33.0, 0.56, 0.43),  # ocre  #AA7330
    "danger": (10.0, 0.45, 0.54),  # rouge #BE6654
    "muted": (234.0, 0.08, 0.49),  # gris  #737588
}

CSS_VAR = {
    "primary": "hsl(var(--primary-hue))",
    "secondary": "hsl(var(--secondary-hue))",
    "accent": "hsl(var(--accent-hue))",
    "danger": "hsl(var(--danger))",
    "muted": "hsl(var(--muted))",
}

HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def hex_to_hsl(value: str) -> tuple[float, float, float]:
    """Convertit #rrggbb en (teinte, saturation, luminosité) HSL."""
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    hi, lo = max(r, g, b), min(r, g, b)
    light = (hi + lo) / 2
    if hi == lo:
        return 0.0, 0.0, light
    delta = hi - lo
    sat = delta / (1 - abs(2 * light - 1)) if light not in (0, 1) else 0.0
    if hi == r:
        hue = ((g - b) / delta) % 6
    elif hi == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    return hue * 60, sat, light


def nearest_token(hex_color: str) -> str:
    """Retourne le jeton du thème le plus proche d'une couleur donnée."""
    hue, sat, light = hex_to_hsl(hex_color)
    # Une couleur quasi neutre reste neutre, quelle que soit sa teinte.
    if sat < 0.12:
        return "muted"
    best, best_d = "primary", 1e9
    for name, (th, ts, tl) in TOKENS.items():
        dh = abs(hue - th)
        dh = min(dh, 360 - dh) / 180.0  # écart circulaire
        d = dh * 3 + abs(sat - ts) + abs(light - tl)
        if d < best_d:
            best, best_d = name, d
    return best


def clean_svg(svg: str, remap: bool, size: tuple[int, int]) -> str:
    """Normalise le SVG produit par vtracer."""
    width, height = size

    # vtracer empile les calques : le premier est le fond opaque issu de
    # l'aplatissement. On le retire pour retrouver un fond transparent.
    first = re.search(r"<path\b[^>]*/>", svg)
    if first:
        box = re.search(r'\sd="([^"]*)"', first.group(0))
        if (
            box
            and box.group(1).strip().startswith("M0 0")
            and f"{width} {height}" in box.group(1)
        ):
            svg = svg[: first.start()] + svg[first.end() :]

    # Dimensions explicites -> viewBox (le composant React fixe la taille).
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg)
    svg = svg.replace("<svg ", f'<svg viewBox="0 0 {width} {height}" ', 1)
    svg = re.sub(r'\s(xml:space|version|id|data-name)="[^"]*"', "", svg)

    if remap:
        cache: dict[str, str] = {}

        def swap(match: re.Match[str]) -> str:
            original = match.group(0)
            if original not in cache:
                cache[original] = CSS_VAR[nearest_token(original)]
            return cache[original]

        svg = HEX_RE.sub(swap, svg)

    return re.sub(r"\s{2,}", " ", svg.replace("\n", " ")).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--remap-colors", dest="remap", action="store_true", default=True)
    parser.add_argument("--keep-colors", dest="remap", action="store_false")
    args = parser.parse_args()

    sources = sorted(
        p
        for p in args.src.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not sources:
        print(f"Aucune image dans {args.src}")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for path in sources:
        # Aplatissement sur blanc : vtracer ne traite pas l'alpha comme une
        # couleur à part.
        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            size = img.size
            flat = Image.new("RGB", size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.split()[3])
            prepared = args.out / f"_flat_{path.stem}.png"
            flat.save(prepared)

        raw = args.out / f"_raw_{path.stem}.svg"
        vtracer.convert_image_to_svg_py(
            str(prepared),
            str(raw),
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=4,
            color_precision=8,
            layer_difference=8,
            corner_threshold=60,
            length_threshold=4.0,
            splice_threshold=45,
            path_precision=3,
        )

        target = args.out / f"{path.stem}.svg"
        target.write_text(
            clean_svg(raw.read_text(encoding="utf-8"), args.remap, size),
            encoding="utf-8",
        )
        raw.unlink()
        prepared.unlink()
        print(f"  {path.name} -> {target.name}")

    print(f"{len(sources)} icône(s) vectorisée(s) dans {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
