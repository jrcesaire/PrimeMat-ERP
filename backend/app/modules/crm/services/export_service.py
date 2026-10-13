"""Export en masse des partenaires (clients / fournisseurs).

Miroir de ``CrmImportService`` : les colonnes produites sont exactement
celles que l'import attend, ce qui rend le fichier exporté réimportable
tel quel (aller‑retour « export → transfert → import »).

- ``role`` : ``client`` / ``fournisseur`` / ``both`` (valeurs lisibles,
  reconnues par ``_ROLE_MAP``) ;
- ``type_entite`` : ``particulier`` / ``entreprise`` / ``professionnel`` ;
- ``adresse`` / ``ville`` : adresse principale du partenaire.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crm.models.partner import Partner

PARTNER_HEADERS = [
    "nom",
    "code",
    "role",
    "type_entite",
    "telephone",
    "email",
    "site_web",
    "numero_fiscal",
    "numero_registre",
    "limite_credit",
    "delai_paiement",
    "adresse",
    "ville",
]

# Valeur stockée (modèle) → valeur écrite dans le fichier (importable)
_ROLE_LABELS = {"client": "client", "supplier": "fournisseur", "both": "both"}
_ENTITY_LABELS = {
    "individual": "particulier",
    "company": "entreprise",
    "professional": "professionnel",
}


def _primary_address(partner: Partner):
    addresses = partner.addresses or []
    if not addresses:
        return None
    return next((a for a in addresses if a.is_primary), addresses[0])


class CrmExportService:
    """Export des partenaires vers un tableau (en‑têtes + lignes)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def partners(
        self, include_rows: bool = True, role: str | None = None
    ) -> tuple[list[str], list[list[Any]]]:
        stmt = select(Partner).order_by(Partner.id)
        if role:
            # Reprend le filtre de l'écran (onglets Clients / Fournisseurs)
            stmt = stmt.where(Partner.role == role)
        result = await self.session.execute(stmt)
        partners = list(result.scalars().all())
        if not include_rows:
            return PARTNER_HEADERS, []
        return PARTNER_HEADERS, [self._row(p) for p in partners]

    @staticmethod
    def _row(partner: Partner) -> list[Any]:
        address = _primary_address(partner)
        return [
            partner.name,
            partner.code,
            _ROLE_LABELS.get(partner.role, partner.role),
            _ENTITY_LABELS.get(partner.entity_type, partner.entity_type),
            partner.phone,
            partner.email,
            partner.website,
            partner.tax_number,
            partner.registration_number,
            float(partner.credit_limit) if partner.credit_limit is not None else None,
            partner.payment_terms_days,
            address.line_1 if address else None,
            address.city if address else None,
        ]
