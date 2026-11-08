"""API Périodes de paie et lots de bulletins."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import noload

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.models.period import PayrollPeriod
from app.modules.payroll.schemas import PeriodCreate, PeriodRead, RunRead
from app.modules.payroll.services.payslip_service import PayslipService

router = APIRouter()


@router.get("/periods", response_model=list[PeriodRead])
async def list_periods(
    session: SessionDep,
    _: User = Depends(require_permission("payroll_period", "view")),
):
    result = await session.execute(
        select(PayrollPeriod)
        # Liste : les lots ne sont pas nécessaires à l'affichage.
        .options(noload(PayrollPeriod.runs))
        .order_by(PayrollPeriod.date_start.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/periods", response_model=PeriodRead, status_code=status.HTTP_201_CREATED
)
async def create_period(
    body: PeriodCreate,
    session: SessionDep,
    user: User = Depends(require_permission("payroll_period", "create")),
):
    period = PayrollPeriod(company_id=user.company_id, **body.model_dump())
    session.add(period)
    await session.commit()
    await session.refresh(period)
    return period


@router.post("/periods/{period_id}/runs", response_model=RunRead)
async def generate_run(
    period_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "create")),
):
    """Génère le lot de la période : un bulletin par contrat actif."""
    try:
        return await PayslipService(session).generate_run(period_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/runs/{run_id}/validate", response_model=RunRead)
async def validate_run(
    run_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payslip", "validate")),
):
    """Valide tous les bulletins du lot (et les comptabilise)."""
    try:
        return await PayslipService(session).validate_run(run_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/runs/{run_id}/pay", response_model=RunRead)
async def pay_run(
    run_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payslip", "pay")),
):
    """Marque le lot comme payé."""
    try:
        return await PayslipService(session).pay(run_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
