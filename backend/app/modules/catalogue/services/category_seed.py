"""
Seed du catalogue — arborescence standard des catégories de produits.

- Les 36 catégories racines métier (voir « Catégories produits »)
- Sous-arborescence « Tôles et couverture » :

    Tôles et couverture                     (unit)
    ├── Tôles BAC                           (length) ← déclencheur mètre linéaire
    │   ├── Tôle BAC Alu                    (hérite length)
    │   ├── Tôle BAC Selflock (ghanéenne)   (hérite length)
    │   └── Tuile BAC                       (hérite length)
    ├── Accessoires de tôlerie              (dual : au ml ou pièce standard)
    │   ├── Solins et rives
    │   ├── Faîtières et closoirs
    │   └── Planches de rive
    └── Tôles ondulées et laquées           (unit)

Idempotent : ne recrée pas une catégorie existante (clé code + entreprise).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product import ProductCategory

logger = logging.getLogger(__name__)

# Les 36 catégories racines du référentiel
ROOT_CATEGORIES: list[tuple[str, str]] = [
    ("TOIT", "Tôles et couverture"),
    ("CIM", "Ciment et liants"),
    ("FER", "Ferraillage et armatures"),
    ("ACI", "Acier et profilés métalliques"),
    ("QNC", "Quincaillerie"),
    ("BOI", "Bois et dérivés"),
    ("PLO", "Plomberie et adduction d'eau"),
    ("ELE", "Électricité"),
    ("PEI", "Peinture et revêtements"),
    ("CAR", "Carrelage et revêtements de sol"),
    ("SDB", "Sanitaires et équipements de salle de bain"),
    ("MAC", "Matériaux de maçonnerie"),
    ("GRA", "Granulats et matériaux de construction"),
    ("ETA", "Étanchéité et isolation"),
    ("MEN", "Menuiserie"),
    ("VIT", "Vitrerie"),
    ("SER", "Serrurerie et sécurité"),
    ("OUT", "Outillage"),
    ("EAC", "Équipements et accessoires de chantier"),
    ("EPI", "EPI et sécurité"),
    ("COL", "Colles, mastics, adhésifs et produits chimiques"),
    ("VIS", "Visserie, boulonnerie et fixation"),
    ("CLO", "Clôture et aménagement extérieur"),
    ("JAR", "Jardinage et espaces verts"),
    ("FIN", "Produits de finition et décoration"),
    ("EVA", "Évacuation et assainissement"),
    ("VEN", "Ventilation et traitement de l'air"),
    ("HYD", "Équipements hydrauliques et pompage"),
    ("ENE", "Équipements électriques et énergie"),
    ("ECH", "Équipements de chantier"),
    ("CCH", "Consommables de chantier"),
    ("TRA", "Transport et manutention"),
    ("PRE", "Produits préfabriqués et béton"),
    ("MTT", "Matériaux pour toiture et accessoires"),
    ("AGR", "Produits agricoles et connexes"),
    ("DIV", "Produits divers"),
    ("SRV", "Services"),
]

# Sous-arborescence « Tôles et couverture »
# (code, nom, mode, parent_code)
TOITURE_SUBTREE: list[tuple[str, str, str, str]] = [
    ("TOIT-BAC", "Tôles BAC", "length", "TOIT"),
    ("TOIT-BAC-ALU", "Tôle BAC Alu", None, "TOIT-BAC"),          # hérite length
    ("TOIT-BAC-SELF", "Tôle BAC Selflock (ghanéenne)", None, "TOIT-BAC"),
    ("TOIT-BAC-TUILE", "Tuile BAC", None, "TOIT-BAC"),
    ("TOIT-ACC", "Accessoires de tôlerie", "dual", "TOIT"),
    ("TOIT-ACC-SOLIN", "Solins et rives", None, "TOIT-ACC"),
    ("TOIT-ACC-FAIT", "Faîtières et closoirs", None, "TOIT-ACC"),
    ("TOIT-ACC-PRV", "Planches de rive", None, "TOIT-ACC"),
    ("TOIT-OND", "Tôles ondulées et laquées", "unit", "TOIT"),
]


async def seed_categories(session: AsyncSession, company_id: int) -> list[str]:
    """Crée l'arborescence de catégories pour une entreprise. Retourne les créations."""
    created: list[str] = []
    cache: dict[str, ProductCategory] = {}

    async def _get_or_create(
        code: str, name: str, sale_mode: str | None, parent_id: int | None
    ) -> ProductCategory:
        existing = (await session.execute(
            select(ProductCategory).where(
                ProductCategory.code == code,
                ProductCategory.company_id == company_id,
            )
        )).scalar_one_or_none()
        if existing:
            cache[code] = existing
            return existing
        cat = ProductCategory(
            name=name,
            code=code,
            parent_id=parent_id,
            sale_mode=sale_mode or "unit",
            company_id=company_id,
            is_active=True,
        )
        session.add(cat)
        await session.flush()
        cache[code] = cat
        created.append(f"{code} ({name})")
        return cat

    # Racines
    for code, name in ROOT_CATEGORIES:
        await _get_or_create(code, name, "unit", None)

    # Sous-arborescence toiture
    for code, name, mode, parent_code in TOITURE_SUBTREE:
        parent = cache.get(parent_code)
        await _get_or_create(code, name, mode, parent.id if parent else None)

    await session.flush()
    return created