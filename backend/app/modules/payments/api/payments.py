"""API Paiements + reçus PDF."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payments.schemas import PaymentCreate, PaymentRead
from app.modules.payments.services.payment_service import PaymentService

router = APIRouter()


@router.get("/payments", response_model=list[PaymentRead])
async def list_payments(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("payment", "view")),
):
    service = PaymentService(session)
    return await service.list_payments(skip=skip, limit=limit)


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payment", "create")),
):
    service = PaymentService(session)
    return await service.create_payment(body)


@router.get("/payments/{payment_id}/receipt")
async def print_receipt(
    payment_id: int,
    _: User = Depends(require_permission("payment", "view")),
):
    """Reçu de paiement — format modèle GEA (A4 léger)."""
    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_payment(payment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    engine = DocumentEngine()
    path = engine.render_to_pdf("receipt.html", context)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=receipt.pdf"},
    )