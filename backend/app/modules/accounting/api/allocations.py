"""
API Comptabilité — lettrage tiers (rapprochement paiement ↔ facture).

Routes préfixées par /api/v1/accounting, isolées par tenant (company_id).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.schemas import (
    InvoiceAllocationCreate,
    InvoiceAllocationRead,
    InvoiceAllocationSummary,
)
from app.modules.accounting.services.journal_service import LedgerService

router = APIRouter()


@router.post(
    "/allocations",
    response_model=InvoiceAllocationRead,
    status_code=201,
)
async def create_allocation(
    body: InvoiceAllocationCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Lettrage : alloue un paiement à une facture (idempotent par couple)."""
    service = LedgerService(session)
    try:
        allocation = await service.allocate_payment(
            company_id=company_id,
            invoice_id=body.invoice_id,
            payment_id=body.payment_id,
            allocated_amount=body.allocated_amount,
            allocation_date=body.allocation_date,
            notes=body.notes,
        )
        await session.commit()
        return allocation
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/allocations/invoice/{invoice_id}",
    response_model=list[InvoiceAllocationRead],
)
async def list_allocations_for_invoice(
    invoice_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Liste les lettrages d'une facture."""
    service = LedgerService(session)
    return await service.get_allocations_for_invoice(company_id, invoice_id)


@router.get(
    "/allocations/payment/{payment_id}",
    response_model=list[InvoiceAllocationRead],
)
async def list_allocations_for_payment(
    payment_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Liste les lettrages d'un paiement."""
    service = LedgerService(session)
    return await service.get_allocations_for_payment(company_id, payment_id)


@router.get(
    "/allocations/summary",
    response_model=list[InvoiceAllocationSummary],
)
async def allocation_summary(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    partner_id: int | None = Query(
        default=None, description="Filtrer par tiers (client/fournisseur)"
    ),
    _: User = Depends(require_permission("account", "view")),
):
    """Résumé des factures avec montant alloué et solde restant."""
    from sqlalchemy import func, select

    from app.modules.invoicing.models.invoice import Invoice
    from app.modules.accounting.models.invoice_allocation import InvoiceAllocation

    # Factures de l'entreprise
    stmt = select(Invoice).where(Invoice.company_id == company_id)
    if partner_id is not None:
        stmt = stmt.where(Invoice.partner_id == partner_id)

    invoices = (await session.execute(stmt)).scalars().all()
    if not invoices:
        return []

    # Sommes allouées par facture
    alloc_stmt = (
        select(
            InvoiceAllocation.invoice_id,
            func.coalesce(func.sum(InvoiceAllocation.allocated_amount), 0).label(
                "allocated"
            ),
        )
        .where(InvoiceAllocation.company_id == company_id)
        .group_by(InvoiceAllocation.invoice_id)
    )
    alloc_map = {
        row.invoice_id: float(row.allocated)
        for row in (await session.execute(alloc_stmt)).all()
    }

    result = []
    for inv in invoices:
        allocated = alloc_map.get(inv.id, 0.0)
        result.append(
            InvoiceAllocationSummary(
                invoice_id=inv.id,
                invoice_reference=inv.reference,
                amount_total=float(inv.amount_total),
                allocated_amount=allocated,
                remaining_amount=round(float(inv.amount_total) - allocated, 2),
            )
        )
    return result


__all__ = ["router"]
