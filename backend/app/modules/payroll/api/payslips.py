"""API Bulletins de paie — consultation, calcul, workflow."""
from __future__ import annotations

import asyncio
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.schemas import InputCreate, PayslipRead, WorkedDayCreate
from app.modules.payroll.services.payslip_service import PayslipService

router = APIRouter()


class PayslipCreate(BaseModel):
    contract_id: int
    date_from: date
    date_to: date
    payment_date: date | None = None


@router.get("/payslips", response_model=list[PayslipRead])
async def list_payslips(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    run_id: int | None = None,
    employee_id: int | None = None,
    _: User = Depends(require_permission("payslip", "view")),
):
    return await PayslipService(session).list_payslips(
        skip=skip, limit=limit, run_id=run_id, employee_id=employee_id
    )


@router.post(
    "/payslips", response_model=PayslipRead, status_code=status.HTTP_201_CREATED
)
async def create_payslip(
    body: PayslipCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "create")),
):
    """Crée un bulletin isolé (hors lot) pour un contrat."""
    try:
        return await PayslipService(session).create_payslip(
            contract_id=body.contract_id,
            date_from=body.date_from,
            date_to=body.date_to,
            payment_date=body.payment_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/payslips/{payslip_id}", response_model=PayslipRead)
async def get_payslip(
    payslip_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "view")),
):
    payslip = await PayslipService(session).get(payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Bulletin introuvable")
    return payslip


@router.post("/payslips/{payslip_id}/compute", response_model=PayslipRead)
async def compute_payslip(
    payslip_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "edit")),
):
    """Recalcule les lignes du bulletin à partir des règles de la structure."""
    try:
        return await PayslipService(session).compute_sheet(payslip_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/payslips/{payslip_id}/inputs", response_model=PayslipRead)
async def add_input(
    payslip_id: int,
    body: InputCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "edit")),
):
    """Ajoute un élément variable (prime, retenue) au bulletin."""
    service = PayslipService(session)
    try:
        await service.add_input(
            payslip_id, body.input_code, body.name, body.amount, body.quantity
        )
        return await service.compute_sheet(payslip_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/payslips/{payslip_id}/worked-days", response_model=PayslipRead)
async def add_worked_day(
    payslip_id: int,
    body: WorkedDayCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "edit")),
):
    """Ajoute des jours / heures travaillés puis recalcule le bulletin."""
    service = PayslipService(session)
    try:
        await service.add_worked_day(
            payslip_id,
            body.work_entry_type,
            body.number_of_days,
            body.number_of_hours,
            body.name,
        )
        return await service.compute_sheet(payslip_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/payslips/{payslip_id}/validate", response_model=PayslipRead)
async def validate_payslip(
    payslip_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payslip", "validate")),
):
    """Valide le bulletin et génère l'écriture comptable (idempotente)."""
    try:
        return await PayslipService(session).validate(payslip_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/payslips/{payslip_id}/back-to-draft", response_model=PayslipRead)
async def back_to_draft(
    payslip_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payslip", "validate")),
):
    """Remet le bulletin en brouillon et annule l'écriture comptable."""
    try:
        return await PayslipService(session).back_to_draft(
            payslip_id, user_id=user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/payslips/{payslip_id}/pdf")
async def print_payslip(
    payslip_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payslip", "view")),
):
    """Bulletin de paie au format PDF."""
    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine
    from app.core.documents.naming import content_disposition

    service = PayslipService(session)
    payslip = await service.get(payslip_id)
    if payslip is None:
        raise HTTPException(status_code=404, detail="Bulletin introuvable")
    if payslip.state == "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulletin en brouillon : lancez le calcul avant impression.",
        )
    try:
        context = await ContextBuilder().load_payslip(payslip_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bulletin introuvable")
    path = await asyncio.to_thread(
        DocumentEngine().render_to_pdf, "payslip.html", context
    )
    with open(path, "rb") as handle:
        data = handle.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                context.get("doc_filename") or "bulletin_de_paie.pdf"
            )
        },
    )
