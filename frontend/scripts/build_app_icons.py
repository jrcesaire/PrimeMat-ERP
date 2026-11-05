"""Genere `app-icons.tsx` a partir des SVG vectorises.

Chaque SVG devient un composant React qui reprend exactement les chemins
produits par vtracer : la fidelite au visuel d'origine est donc totale.
"""

import os
import pathlib
import re

SVG_DIR = pathlib.Path(os.environ["TEMP"]) / "icons_svg"
OUT = pathlib.Path(
    r"D:\Travail\Projets\JR\ERP Matériaux de construction\frontend"
    r"\src\components\icons\app-icons.tsx"
)

#: (nom du fichier source, cle de tuile, nom du composant)
MAP = [
    ("Tableau de bord", "dashboard", "DashboardIcon"),
    ("Ventes", "sales", "SalesIcon"),
    ("Point de vente", "pos", "PosIcon"),
    ("Factures", "invoicing", "InvoicingIcon"),
    ("Catalogue", "catalogue", "CatalogueIcon"),
    ("Stock", "stock", "StockIcon"),
    ("Livraison", "delivery", "DeliveryIcon"),
    ("Paiements", "payments", "PaymentsIcon"),
    ("Trésorerie", "treasury", "TreasuryIcon"),
]

HEADER = '''/**
 * Icônes d'application du lanceur.
 *
 * Fichier **généré** par `scripts/vectorize_icons.py` puis
 * `scripts/build_app_icons.py` : chaque icône reprend les chemins vectorisés
 * depuis le visuel fourni (tracé vtracer), sans réinterprétation — la forme
 * est donc fidèle à l'original.
 *
 * Seules les couleurs ont été alignées sur la charte : chaque teinte d'origine
 * a été remplacée par le jeton du thème le plus proche (`--primary-hue`,
 * `--secondary-hue`, `--accent-hue`, `--danger`, `--muted`). Les icônes
 * suivent ainsi le sélecteur de couleurs et le mode sombre.
 *
 * Pour régénérer : voir l'en-tête de `scripts/vectorize_icons.py`.
 */
import type { ComponentType, SVGProps } from "react";

export type AppIconProps = SVGProps<SVGSVGElement>;

'''

FOOTER_TMPL = '''
/** Correspondance entre la clé d'une tuile (`lib/module-registry`) et son icône. */
export const APP_ICONS: Record<string, ComponentType<AppIconProps>> = {
%s};
'''


def inner(svg: str) -> str:
    """Contenu interne du SVG, sans déclaration XML ni commentaire."""
    body = re.sub(r"<\?xml[^>]*\?>", "", svg)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"^.*?<svg[^>]*>", "", body, flags=re.S)
    body = re.sub(r"</svg>\s*$", "", body, flags=re.S)
    return re.sub(r"\s{2,}", " ", body).strip()


parts = [HEADER]
entries = []

for name, key, component in MAP:
    source = SVG_DIR / f"{name}.svg"
    if not source.exists():
        raise SystemExit(f"SVG manquant : {source}")
    svg = source.read_text(encoding="utf-8")
    view_box = re.search(r'viewBox="([^"]+)"', svg).group(1)
    parts.append(
        f"/** {name} — vectorisé depuis le visuel fourni. */\n"
        f"export function {component}(props: AppIconProps) {{\n"
        f"  return (\n"
        f'    <svg\n'
        f'      viewBox="{view_box}"\n'
        f'      xmlns="http://www.w3.org/2000/svg"\n'
        f'      aria-hidden="true"\n'
        f"      {{...props}}\n"
        f"    >\n"
        f"      {inner(svg)}\n"
        f"    </svg>\n"
        f"  );\n"
        f"}}\n"
    )
    entries.append(f"  {key}: {component},\n")

parts.append(FOOTER_TMPL % "".join(entries))

OUT.write_text("\n".join(parts), encoding="utf-8", newline="")
size = OUT.stat().st_size
print(f"{OUT.name} ecrit : {size} octets, {len(MAP)} icones")
