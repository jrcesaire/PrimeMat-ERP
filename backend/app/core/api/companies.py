"""
Endpoints de gestion des entreprises et agences.

- GET  /companies          — liste
- POST /companies          — création
- GET  /companies/{id}     — détail
- PUT  /companies/{id}     — mise à jour
- GET  /companies/{id}/agencies — agences
- POST /companies/{id}/agencies — créer agence
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_superuser
from app.core.models.company import Agency, Company
from app.core.models.user import User
from app.core.schemas.company import (
    AgencyCreate,
    AgencyRead,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[CompanyRead])
async def list_companies(
    session: SessionDep,
    _: User = Depends(require_superuser),
):
    """Liste toutes les entreprises (super-admin uniquement)."""
    from sqlalchemy import select
    result = await session.execute(select(Company).order_by(Company.id))
    return list(result.scalars().all())


@router.post("/", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    session: SessionDep,
    body: CompanyCreate,
    _: User = Depends(require_superuser),
):
    """Crée une nouvelle entreprise."""
    company = Company(**body.model_dump())
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    session: SessionDep,
    company_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Retourne une entreprise (un non-superadmin ne voit que la sienne)."""
    if not current_user.is_superuser and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Accès restreint à votre entreprise")
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    return company


@router.put("/{company_id}", response_model=CompanyRead)
async def update_company(
    session: SessionDep,
    company_id: int,
    body: CompanyUpdate,
    _: User = Depends(require_superuser),
):
    """Met à jour une entreprise (mise à jour partielle)."""
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    update_data = body.model_dump(exclude_unset=True)

    # Nom et code ne peuvent pas être vidés (colonnes NOT NULL)
    for field in ("name", "code"):
        if field in update_data and not update_data[field]:
            del update_data[field]

    for field, value in update_data.items():
        setattr(company, field, value)

    await session.commit()
    await session.refresh(company)
    return company


@router.get("/{company_id}/agencies", response_model=list[AgencyRead])
async def list_agencies(
    session: SessionDep,
    company_id: int,
    _: User = Depends(get_current_active_user),
):
    """Liste les agences d'une entreprise."""
    from sqlalchemy import select
    result = await session.execute(
        select(Agency).where(Agency.company_id == company_id).order_by(Agency.id)
    )
    return list(result.scalars().all())


@router.post(
    "/{company_id}/agencies",
    response_model=AgencyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_agency(
    session: SessionDep,
    company_id: int,
    body: AgencyCreate,
    _: User = Depends(require_superuser),
):
    """Crée une agence pour une entreprise."""
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    agency = Agency(**body.model_dump(), company_id=company_id)
    session.add(agency)
    await session.commit()
    await session.refresh(agency)
    return agency
