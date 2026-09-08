"""
API Comptabilité — plan comptable, journaux et écritures (socle).

Le module est multi-entreprise : les requêtes sont isolées par le
filtre de tenant (``company_id``) appliqué au niveau ORM. Le seed du
plan est exécuté silencieusement au premier accès si absent.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user, get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
# noqa: F401 — enregistre les modèles comptables dans la metadata
from app.modules.accounting.models import (
    Account,
    FiscalYear,
    Journal,
    JournalEntry,
    JournalEntryLine,
)
from app.modules.accounting.schemas import (
    AccountRead,
    FiscalYearCreate,
    FiscalYearRead,
    JournalEntryCreate,
    JournalEntryRead,
    JournalRead,
    SeedResult,
)
from app.modules.accounting.services.account_service import AccountService
from app.modules.accounting.services.journal_service import LedgerService

router = APIRouter()


@router.get("/accounts", response_model=list[AccountRead])
async def list_accounts(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    account_class: str | None = None,
    skip: int = 0,
    limit: int = 500,
    _: User = Depends(require_permission("account", "view")),
):
    """Liste des comptes du plan (filtrable par classe 1-9)."""
    service = AccountService(session)
    await service.ensure_seeded(company_id)
    return await service.list_accounts(
        company_id, account_class=account_class, skip=skip, limit=limit
    )


@router.post("/accounts/seed", response_model=SeedResult)
async def seed_plan(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "create")),
):
    """(Ré)initialise le plan comptable OHADA pour l'entreprise — idempotent."""
    service = AccountService(session)
    created = await service.seed_ohada_chart(company_id)
    j_created = await service.seed_default_journals(company_id)
    await session.commit()
    return SeedResult(
        created=created,
        total=len(await service.list_accounts(company_id, active_only=False, limit=2000)),
        journals_created=j_created,
    )


@router.get("/journals", response_model=list[JournalRead])
async def list_journals(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Journaux disponibles (VTE, ACH, BAN, CAI, PAY, OD)."""
    service = AccountService(session)
    await service.ensure_seeded(company_id)
    await service.seed_default_journals(company_id)
    await session.flush()
    from sqlalchemy import select

    rows = (
        await session.execute(select(Journal).where(Journal.company_id == company_id))
    ).scalars().all()
    return list(rows)
# ------------------------------------------------------------------ #
# Exercices comptables
# ------------------------------------------------------------------ #
@router.get("/fiscal-years", response_model=list[FiscalYearRead])
async def list_fiscal_years(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    from sqlalchemy import select

    rows = (
        await session.execute(
            select(FiscalYear).where(FiscalYear.company_id == company_id)
        )
    ).scalars().all()
    return list(rows)


@router.post("/fiscal-years", response_model=FiscalYearRead, status_code=201)
async def create_fiscal_year(
    body: FiscalYearCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "create")),
):
    if body.start_date >= body.end_date:
        raise HTTPException(
            status_code=400, detail="La date de début doit précéder la fin."
        )
    fiscal = FiscalYear(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        status="open",
        company_id=company_id,
    )
    session.add(fiscal)
    await session.commit()
    return fiscal


# ------------------------------------------------------------------ #
# Écritures comptables
# ------------------------------------------------------------------ #
@router.get("/journal-entries", response_model=list[JournalEntryRead])
async def list_entries(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    account_code: str | None = None,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("account", "view")),
):
    """Écritures comptables (filtrées par compte éventuellement)."""
    service = LedgerService(session)
    return await service.list_entries(
        company_id, skip=skip, limit=limit, account_code=account_code
    )


@router.post("/journal-entries", response_model=JournalEntryRead, status_code=201)
async def create_entry(
    body: JournalEntryCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "create")),
):
    """Crée et publie une écriture manuelle (débit == crédit)."""
    service = LedgerService(session)
    try:
        entry = await service.create_entry(company_id, body, post=True)
        await session.commit()
        return await service.get_entry(entry.id, company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryRead)
async def get_entry(
    entry_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    service = LedgerService(session)
    entry = await service.get_entry(entry_id, company_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Écriture introuvable")
    return entry


@router.post("/journal-entries/{entry_id}/post", response_model=JournalEntryRead)
async def post_entry(
    entry_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Valide et publie une écriture (draft → posted)."""
    service = LedgerService(session)
    try:
        entry = await service.post_entry(entry_id, company_id)
        await session.commit()
        return await service.get_entry(entry.id, company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------ #
# Soldes & balances (pré-états)
# ------------------------------------------------------------------ #
@router.get("/balances")
async def account_balances(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Soldes par compte (sur écritures publiées)."""
    service = LedgerService(session)
    return await service.account_balances(company_id)


__all__ = ["router"]