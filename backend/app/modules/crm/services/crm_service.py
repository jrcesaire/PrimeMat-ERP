"""Service CRM — logique métier des partenaires et chantiers."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crm.models.partner import Partner, Contact, PartnerAddress
from app.modules.crm.models.site import Site
from app.modules.crm.schemas import PartnerCreate, PartnerUpdate, SiteCreate

logger = logging.getLogger(__name__)


class CrmService:
    """Service du module CRM."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Partenaires
    # ------------------------------------------------------------------ #
    async def create_partner(
        self, data: PartnerCreate, company_id: int | None = None
    ) -> Partner:
        partner = Partner()
        for field in ("name", "code", "role", "entity_type", "gender",
                      "phone", "email", "website", "tax_number",
                      "registration_number", "credit_limit",
                      "payment_terms_days", "default_discount"):
            if getattr(data, field, None) is not None:
                setattr(partner, field, getattr(data, field))

        # Héritage du tenant multi-entreprise
        if company_id:
            partner.company_id = company_id
            for contact_data in data.contacts:
                contact = Contact(**contact_data.model_dump())
                contact.company_id = company_id
                partner.contacts.append(contact)
            for addr_data in data.addresses:
                addr = PartnerAddress(**addr_data.model_dump())
                addr.company_id = company_id
                partner.addresses.append(addr)
        else:
            for contact_data in data.contacts:
                partner.contacts.append(Contact(**contact_data.model_dump()))
            for addr_data in data.addresses:
                partner.addresses.append(PartnerAddress(**addr_data.model_dump()))

        self.session.add(partner)
        await self.session.commit()
        await self.session.refresh(partner)
        return partner

    async def get_partner(self, partner_id: int) -> Partner | None:
        return await self.session.get(Partner, partner_id)

    async def list_partners(
        self, skip: int = 0, limit: int = 100, role: str | None = None,
        search: str | None = None,
    ) -> list[Partner]:
        stmt = select(Partner).offset(skip).limit(limit).order_by(Partner.id)
        if role:
            stmt = stmt.where(Partner.role == role)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Partner.name.ilike(like))
                | (Partner.phone.ilike(like))
                | (Partner.email.ilike(like))
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_partner(self, partner_id: int, data: PartnerUpdate) -> Partner | None:
        partner = await self.session.get(Partner, partner_id)
        if partner is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(partner, field, value)
        await self.session.commit()
        await self.session.refresh(partner)
        return partner

    async def delete_partner(self, partner_id: int) -> bool:
        partner = await self.session.get(Partner, partner_id)
        if partner is None:
            return False
        await self.session.delete(partner)
        await self.session.commit()
        return True

    # ------------------------------------------------------------------ #
    # Chantiers (sites)
    # ------------------------------------------------------------------ #
    async def create_site(self, partner_id: int, data: SiteCreate) -> Site:
        site = Site(**data.model_dump(), partner_id=partner_id)
        self.session.add(site)
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def list_sites(self, partner_id: int | None = None) -> list[Site]:
        stmt = select(Site).order_by(Site.id)
        if partner_id:
            stmt = stmt.where(Site.partner_id == partner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_site(self, site_id: int) -> Site | None:
        return await self.session.get(Site, site_id)

    async def delete_site(self, site_id: int) -> bool:
        site = await self.session.get(Site, site_id)
        if site is None:
            return False
        await self.session.delete(site)
        await self.session.commit()
        return True