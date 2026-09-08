"""
Endpoints API du module CRM — partenaires, contacts, adresses, chantiers.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.crm.models.partner import Partner
from app.modules.crm.schemas import (
    ContactCreate,
    PartnerCreate,
    PartnerRead,
    PartnerUpdate,
    SiteCreate,
    SiteRead,
)
from app.modules.crm.services.crm_service import CrmService

router = APIRouter()


@router.get("/partners", response_model=list[PartnerRead])
async def list_partners(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    search: str | None = None,
    _: User = Depends(require_permission("partner", "view")),
):
    service = CrmService(session)
    return await service.list_partners(
        skip=skip, limit=limit, role=role, search=search
    )


@router.post("/partners", response_model=PartnerRead, status_code=status.HTTP_201_CREATED)
async def create_partner(
    body: PartnerCreate,
    session: SessionDep,
    user: User = Depends(require_permission("partner", "create")),
):
    service = CrmService(session)
    return await service.create_partner(body, company_id=user.company_id)


@router.get("/partners/{partner_id}", response_model=PartnerRead)
async def get_partner(
    partner_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("partner", "view")),
):
    service = CrmService(session)
    partner = await service.get_partner(partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    return partner


@router.put("/partners/{partner_id}", response_model=PartnerRead)
async def update_partner(
    partner_id: int,
    body: PartnerUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("partner", "edit")),
):
    service = CrmService(session)
    partner = await service.update_partner(partner_id, body)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    return partner


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    partner_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("partner", "delete")),
):
    service = CrmService(session)
    if not await service.delete_partner(partner_id):
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    return None


# ------------------------------------------------------------------ #
# Contacts
# ------------------------------------------------------------------ #
@router.post("/partners/{partner_id}/contacts", status_code=status.HTTP_201_CREATED)
async def add_contact(
    partner_id: int,
    body: ContactCreate,
    session: SessionDep,
    _: User = Depends(require_permission("partner", "edit")),
):
    service = CrmService(session)
    partner = await service.get_partner(partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    from app.modules.crm.models.partner import Contact

    contact = Contact(**body.model_dump(), partner_id=partner_id)
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    return contact


# ------------------------------------------------------------------ #
# Chantiers (sites)
# ------------------------------------------------------------------ #
@router.get("/sites", response_model=list[SiteRead])
async def list_sites(
    session: SessionDep,
    partner_id: int | None = None,
    _: User = Depends(require_permission("site", "view")),
):
    service = CrmService(session)
    return await service.list_sites(partner_id=partner_id)


@router.post("/sites", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    session: SessionDep,
    partner_id: int,
    _: User = Depends(require_permission("site", "create")),
):
    service = CrmService(session)
    partner = await service.get_partner(partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partenaire introuvable")
    return await service.create_site(partner_id, body)