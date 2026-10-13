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
    invoice_id: int | None = None,
    _: User = Depends(require_permission("payment", "view")),
):
    """Paiements récents ; ``invoice_id`` filtre sur une facture."""
    service = PaymentService(session)
    return await service.list_payments(skip=skip, limit=limit, invoice_id=invoice_id)


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payment", "create")),
):
    service = PaymentService(session)
    try:
        return await service.create_payment(body)
    except ValueError as exc:
        # Contrôles métier : sur-paiement, facture brouillon/annulée, montant <= 0
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/payments/{payment_id}/receipt")
async def print_receipt(
    payment_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payment", "view")),
):
    """Reçu de paiement — format modèle GEA (A4 léger).

    Refusé pour un paiement en brouillon : un encaissement révoqué ne doit
    pas pouvoir être imprimé (durcissement de la cascade de suppression).
    """
    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine
    from app.core.documents.naming import content_disposition
    from app.modules.payments.models.payment import Payment

    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    if payment.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reçu indisponible : ce paiement est en brouillon.",
        )

    try:
        context = await ContextBuilder().load_payment(payment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    engine = DocumentEngine()
    path = await engine.arender_payment(payment_id)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                context.get("doc_filename") or "document.pdf"
            )
        },
    )


@router.post("/payments/{payment_id}/back-to-draft", response_model=PaymentRead)
async def back_to_draft_payment(
    payment_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payment", "edit")),
):
    """Remet un paiement en brouillon (révocation : facture + écriture)."""
    service = PaymentService(session)
    if await service.get_payment(payment_id) is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    try:
        return await service.back_to_draft(payment_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/payments/{payment_id}/confirm", response_model=PaymentRead)
async def confirm_payment(
    payment_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payment", "edit")),
):
    """Re-confirme un paiement brouillon (recrédite la facture + écriture).

    Symétrique de ``back-to-draft`` : permet de revalider le même paiement
    après une remise au brouillon, avec re-jeu des contrôles métier.
    """
    service = PaymentService(session)
    if await service.get_payment(payment_id) is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    try:
        return await service.confirm(payment_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("payment", "delete")),
):
    """Supprime un paiement — brouillon uniquement (cascade de suppression)."""
    service = PaymentService(session)
    if await service.get_payment(payment_id) is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    try:
        await service.delete_payment(payment_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))