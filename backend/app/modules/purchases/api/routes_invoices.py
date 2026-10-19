"""
API Routes Factures fournisseur.

    GET    /purchases/invoices
    POST   /purchases/invoices
    GET    /purchases/invoices/{invoice_id}
    PUT    /purchases/invoices/{invoice_id}
    POST   /purchases/invoices/{invoice_id}/match
    POST   /purchases/invoices/{invoice_id}/post
    POST   /purchases/invoices/{invoice_id}/pay
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.models.user import User
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.schemas import (
    MatchingResult,
    SupplierInvoiceCreate,
    SupplierInvoicePay,
    SupplierInvoiceRead,
    SupplierInvoiceUpdate,
)
from app.modules.purchases.services.supplier_invoice_service import SupplierInvoiceService

router = APIRouter()

require_view = require_permission("purchase_invoice", "view")
require_edit = require_permission("purchase_invoice", "edit")
require_post = require_permission("purchase_invoice", "post")
require_pay = require_permission("purchase_invoice", "pay")


# ------------------------------------------------------------------ #
# Liste / consultation
# ------------------------------------------------------------------ #
@router.get("/invoices", response_model=list[SupplierInvoiceRead])
async def list_invoices(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    supplier_id: int | None = None,
    _: None = Depends(require_view),
):
    service = SupplierInvoiceService(session)
    return await service.list_invoices(
        skip=skip, limit=limit, status=status, supplier_id=supplier_id
    )


@router.get("/invoices/{invoice_id}", response_model=SupplierInvoiceRead)
async def get_invoice(
    invoice_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = SupplierInvoiceService(session)
    invoice = await service.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture fournisseur introuvable.")
    return invoice


# ------------------------------------------------------------------ #
# Écriture
# ------------------------------------------------------------------ #
@router.post(
    "/invoices",
    response_model=SupplierInvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice(
    body: SupplierInvoiceCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_edit),
):
    service = SupplierInvoiceService(session)
    return await service.create_invoice(body, current_user.company_id)


@router.put("/invoices/{invoice_id}", response_model=SupplierInvoiceRead)
async def update_invoice(
    invoice_id: int,
    body: SupplierInvoiceUpdate,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = SupplierInvoiceService(session)
    try:
        invoice = await service.update_invoice(invoice_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture fournisseur introuvable.")
    return invoice


# ------------------------------------------------------------------ #
# Workflow
# ------------------------------------------------------------------ #
@router.post("/invoices/{invoice_id}/match", response_model=MatchingResult)
async def match_invoice(
    invoice_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = SupplierInvoiceService(session)
    try:
        return await service.matching(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/invoices/{invoice_id}/post", response_model=SupplierInvoiceRead)
async def post_invoice(
    invoice_id: int,
    session: SessionDep,
    _: None = Depends(require_post),
):
    service = SupplierInvoiceService(session)
    try:
        invoice = await service.post(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture fournisseur introuvable.")
    return invoice


@router.post("/invoices/{invoice_id}/pay", response_model=SupplierInvoiceRead)
async def pay_invoice(
    invoice_id: int,
    body: SupplierInvoicePay,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_pay),
):
    service = SupplierInvoiceService(session)
    try:
        invoice = await service.pay(invoice_id, body.amount, body.payment_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture fournisseur introuvable.")
    return invoice
