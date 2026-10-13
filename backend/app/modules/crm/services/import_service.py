"""Import en masse des partenaires (clients / fournisseurs).

Colonnes attendues (en-têtes normalisés) ::
    nom (obligatoire), code, role (client|fournisseur|both),
    type_entite (particulier|entreprise|professionnel), telephone, email,
    site_web, numero_fiscal (ncc), numero_registre (rccm),
    limite_credit, delai_paiement (jours), adresse, ville

Comportement : upsert par nom (insensible à la casse) — si le partenaire
existe, ses coordonnées sont mises à jour ; sinon il est créé.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crm.models.partner import Contact, Partner, PartnerAddress
from app.shared.enums import EntityType
from app.shared.file_import import clean_str, to_float, to_int

_ROLE_MAP = {
    "client": "client",
    "customers": "client",
    "customer": "client",
    "fournisseur": "supplier",
    "supplier": "supplier",
    "vendors": "supplier",
    "vendor": "supplier",
    "both": "both",
    "les_deux": "both",
    "client_fournisseur": "both",
}

_ENTITY_MAP = {
    "particulier": EntityType.INDIVIDUAL.value,
    "individual": EntityType.INDIVIDUAL.value,
    "entreprise": EntityType.COMPANY.value,
    "company": EntityType.COMPANY.value,
    "professionnel": EntityType.PROFESSIONAL.value,
    "professional": EntityType.PROFESSIONAL.value,
}


def _map_row(row: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {"__line__": row.get("__line__")}
    direct = {
        "nom": "name", "name": "name", "raison_sociale": "name",
        "code": "code", "role": "role", "type": "entity_type",
        "type_entite": "entity_type", "entity_type": "entity_type",
        "telephone": "phone", "tel": "phone", "phone": "phone",
        "mobile": "phone", "email": "email", "mail": "email",
        "site_web": "website", "website": "website", "web": "website",
        "numero_fiscal": "tax_number", "ncc": "tax_number",
        "tax_number": "tax_number", "numero_registre": "registration_number",
        "rccm": "registration_number", "registration_number": "registration_number",
        "limite_credit": "credit_limit", "credit_limit": "credit_limit",
        "delai_paiement": "payment_terms_days",
        "payment_terms_days": "payment_terms_days",
        "adresse": "address", "address": "address",
        "ville": "city", "city": "city",
        "contact_nom": "contact_name", "contact_prenom": "contact_first_name",
        "contact_tel": "contact_phone",
    }
    for key, value in row.items():
        if key.startswith("__"):
            continue
        field = direct.get(key)
        if field and field not in mapped:
            mapped[field] = value
    return mapped


class CrmImportService:
    """Import des partenaires depuis un fichier Excel / CSV."""

    def __init__(self, session: AsyncSession, company_id: int | None = None):
        self.session = session
        self.company_id = company_id

    async def import_partners(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        created, updated, errors = 0, 0, []

        for row in rows:
            data = _map_row(row)
            line_no = data.get("__line__")
            try:
                name = clean_str(data.get("name"), 200)
                if not name:
                    raise ValueError("Colonne « nom » obligatoire")

                role_raw = (clean_str(data.get("role"), 20) or "").lower()
                role = _ROLE_MAP.get(role_raw, "client")
                entity_raw = (clean_str(data.get("entity_type"), 20) or "").lower()
                entity_type = _ENTITY_MAP.get(entity_raw, EntityType.INDIVIDUAL.value)

                stmt = select(Partner).where(Partner.name.ilike(name))
                if self.company_id:
                    stmt = stmt.where(Partner.company_id == self.company_id)
                partner = (await self.session.execute(stmt)).scalars().first()

                if partner is None:
                    partner = Partner(company_id=self.company_id)
                    self.session.add(partner)
                    created += 1
                else:
                    updated += 1

                partner.name = name
                if self.company_id:
                    partner.company_id = self.company_id
                partner.code = clean_str(data.get("code"), 30)
                partner.role = role
                partner.entity_type = entity_type
                partner.phone = clean_str(data.get("phone"), 50)
                partner.email = clean_str(data.get("email"), 200)
                partner.website = clean_str(data.get("website"), 200)
                partner.tax_number = clean_str(data.get("tax_number"), 50)
                partner.registration_number = clean_str(
                    data.get("registration_number"), 50
                )
                partner.credit_limit = to_float(data.get("credit_limit"))
                partner.payment_terms_days = to_int(data.get("payment_terms_days"))

                address = clean_str(data.get("address"), 200)
                city = clean_str(data.get("city"), 100)
                if (address or city) and not partner.addresses:
                    partner.addresses.append(PartnerAddress(
                        address_type="billing", line_1=address, city=city,
                        is_primary=True, company_id=self.company_id,
                    ))
                elif partner.addresses:
                    if address:
                        partner.addresses[0].line_1 = address
                    if city:
                        partner.addresses[0].city = city

                contact_first = clean_str(data.get("contact_first_name"), 100)
                contact_last = clean_str(data.get("contact_name"), 100)
                if contact_last and not partner.contacts:
                    partner.contacts.append(Contact(
                        first_name=contact_first or "—",
                        last_name=contact_last,
                        phone=clean_str(data.get("contact_phone"), 50),
                        is_primary=True, company_id=self.company_id,
                    ))

                await self.session.flush()
            except Exception as exc:  # noqa: BLE001 — ligne isolée
                await self.session.rollback()
                errors.append({"line": line_no, "error": str(exc) or exc.__class__.__name__})

        if created or updated:
            await self.session.commit()
        return {
            "created": created,
            "updated": updated,
            "errors": errors,
            "total": created + updated + len(errors),
        }
