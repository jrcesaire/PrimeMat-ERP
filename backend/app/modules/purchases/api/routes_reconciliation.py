"""
API Routes Rapprochement 3 voies (BC × BR × facture).

    GET /purchases/reconciliation?order_id=&invoice_id=
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.services.supplier_invoice_service import SupplierInvoiceService

router = APIRouter()

require_view = require_permission("purchase_invoice", "view")


# ------------------------------------------------------------------ #
# Rapprochement
# ------------------------------------------------------------------ #
@router.get("/reconciliation")
async def reconciliation(
    session: SessionDep,
    order_id: int | None = None,
    invoice_id: int | None = None,
    _: None = Depends(require_view),
):
    """Calcule le rapprochement BC × BR × facture.

    On fournit soit ``invoice_id`` (le rapprochement est calculé pour cette
    facture), soit ``order_id`` (on regroupe les factures liées à la
    commande, si plusieurs factures existent).
    """
    if invoice_id is None and order_id is None:
        raise HTTPException(
            status_code=400,
            detail="Paramètres requis : ``invoice_id`` ou ``order_id``.",
        )

    service = SupplierInvoiceService(session)

    if invoice_id is not None:
        return await service.matching(invoice_id)

    # Regroupement par commande : on récupère les factures liées à la BC,
    # puis on fait le rapprochement pour chacune d'elles.
    invoices = await service.list_invoices(supplier_id=None)
    matching_invoices = [
        inv for inv in invoices if inv.order_id == order_id and inv.status in ("draft", "posted")
    ]
    if not matching_invoices:
        raise HTTPException(
            status_code=404,
            detail="Aucune facture liée à cette commande.",
        )

    results = []
    for invoice in matching_invoices:
        result = await service.matching(invoice.id)
        results.append(
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.reference,
                "status": result.status,
                "ordered_total": result.ordered_total,
                "invoiced_total": result.invoiced_total,
                "lines": result.lines,
            }
        )

    return {
        "order_id": order_id,
        "items": results,
    }
