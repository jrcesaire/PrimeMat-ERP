"""Génère les icônes animées du lanceur d'accueil (GIF fournis -> WebP animé).

Les visuels animés de ``D:\\Travail\\Projets\\JR\\Icones`` sont convertis en WebP
animé pour les tuiles correspondantes :

- ``Contacts.gif``       -> ``crm``        (carnet d'adresses)
- ``Factures.gif``       -> ``invoicing``  (document / facture)
- ``Paiement caisse.gif``-> ``pos``        (terminal d'encaissement)

Le GIF étant un format très lourd (jusqu'à 1,6 Mo et 119 images), la conversion
en WebP animé divise le poids par 5 à 10 sans toucher au dessin.

Trois traitements sont appliqués à chaque visuel :

1. **Cadrage sur le contenu** — les GIF laissent une large marge blanche ; on
   recadre sur la boîte englobante du dessin pour que l'icône occupe la même
   surface que les icônes vectorielles (viewBox 96×96) à taille de tuile égale.
2. **Boucle infinie** (``loop=0``) — l'animation tourne en continu.
3. **Image fixe de repli** — la première image est aussi écrite en ``-static``
   pour être servie aux visiteurs ayant activé ``prefers-reduced-motion``.

Sortie : ``public/icons/<clé>.webp`` et ``public/icons/<clé>-static.webp``.

Usage : ``python scripts/build_animated_icons.py`` (depuis ``frontend/``).
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageChops

SOURCE_DIR = r"D:\Travail\Projets\JR\Icones"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "icons")

# Visuel source -> clé de module (cf. `src/lib/module-registry.ts`).
ICONS = {
    "crm": "Contacts.gif",
    "invoicing": "Factures.gif",
    "pos": "Paiement caisse.gif",
}

# Côté du carré produit. 144 px couvre la tuile (64 px) avec une marge pour les
# écrans haute densité, sans alourdir inutilement le fichier.
SIZE = 144
PADDING = 0.06
QUALITY = 80
WHITE_THRESHOLD = 12


def content_box(frames: list[Image.Image]) -> tuple[int, int, int, int]:
    """Boîte englobante du dessin, calculée sur un échantillon d'images.

    Le décalage est calculé sur plusieurs images pour que le cadrage reste
    stable même si le dessin se déplace légèrement pendant l'animation.
    """
    step = max(1, len(frames) // 12)
    background = Image.new("RGB", frames[0].size, (255, 255, 255))
    boxes = []
    for frame in frames[::step]:
        mask = ImageChops.difference(frame.convert("RGB"), background).convert("L")
        box = mask.point(lambda value: 255 if value > WHITE_THRESHOLD else 0).getbbox()
        if box:
            boxes.append(box)
    if not boxes:
        return (0, 0, *frames[0].size)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def square(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Étend la boîte en carré centré, borné à l'image."""
    width, height = box[2] - box[0], box[3] - box[1]
    side = max(width, height)
    margin = int(side * PADDING)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    half = side / 2 + margin
    left, top = int(cx - half), int(cy - half)
    left = max(0, min(left, size[0] - 2 * int(half)))
    top = max(0, min(top, size[1] - 2 * int(half)))
    return (left, top, left + int(half) * 2, top + int(half) * 2)


def convert(name: str, key: str) -> None:
    path = os.path.join(SOURCE_DIR, name)
    if not os.path.exists(path):
        raise SystemExit(f"Visuel introuvable : {path}")

    source = Image.open(path)
    frames, durations = [], []
    for index in range(getattr(source, "n_frames", 1)):
        source.seek(index)
        frames.append(source.convert("RGB").copy())
        durations.append(source.info.get("duration") or 20)

    crop = square(content_box(frames), source.size)
    frames = [frame.crop(crop).resize((SIZE, SIZE), Image.LANCZOS) for frame in frames]

    animated = os.path.join(OUTPUT_DIR, f"{key}.webp")
    frames[0].save(
        animated,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,  # boucle infinie
        quality=QUALITY,
        method=6,
    )
    frames[0].save(os.path.join(OUTPUT_DIR, f"{key}-static.webp"), format="WEBP", quality=QUALITY, method=6)

    before = os.path.getsize(path) / 1024
    after = os.path.getsize(animated) / 1024
    print(f"{key:10} {len(frames):4} images  {before:7.0f} Ko -> {after:6.0f} Ko  ({after / before:.0%})")


def main() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for key, name in ICONS.items():
        convert(name, key)
    print(f"\n{len(ICONS)} icônes animées écrites dans {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
