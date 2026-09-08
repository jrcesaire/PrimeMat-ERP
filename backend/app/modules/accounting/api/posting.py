"""API Comptabilité — comptabilisation manuelle des flux métier.

Permet de (re)comptabiliser une facture, un paiement ou une dépense déjà
existants (rattrapage). La comptabilisation automatique à la création est
branchée directement dans les services métier ; ces endpoints sont
idempotents : une source déjà comptabilisée est simplement retournée.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.services.posting_service import PostingService

router = APIRouter()


@router.post("/post/invoice/{invoice_id}")
async def post_invoice(
    invoice_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Comptabilise une facture client (D 411 / C 701 + 4431) — idempotent."""
    from app.modules.invoicing.models.invoice import Invoice

    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.company_id != company_id:
        raise HTTPException(404, f"Facture {invoice_id} introuvable")
    result = await PostingService(session).post_invoice(invoice)
    await session.commit()
    if result is None:
        raise HTTPException(
            422, f"Facture {invoice.reference} non comptabilisable (statut {invoice.status})"
        )
    entry, _created = result
    return {"reference": entry.reference, "total": float(entry.total_debit)}


@router.post("/post/payment/{payment_id}")
async def post_payment(
    payment_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Comptabilise un paiement (511|531 ↔ 411|401) — idempotent."""
    from app.modules.payments.models.payment import Payment

    payment = await session.get(Payment, payment_id)
    if payment is None or payment.company_id != company_id:
        raise HTTPException(404, f"Paiement {payment_id} introuvable")
    result = await PostingService(session).post_payment(payment)
    await session.commit()
    if result is None:
        raise HTTPException(
            422, f"Paiement {payment.reference} non comptabilisable (statut {payment.status})"
        )
    entry, _created = result
    return {"reference": entry.reference, "total": float(entry.total_debit)}


@router.post("/post/expense/{expense_id}")
async def post_expense(
    expense_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Comptabilise une dépense (charge ↔ 511|531) — idempotent."""
    from app.modules.finance.models.expense import Expense

    expense = await session.get(Expense, expense_id)
    if expense is None or expense.company_id != company_id:
        raise HTTPException(404, f"Dépense {expense_id} introuvable")
    result = await PostingService(session).post_expense(expense)
    await session.commit()
    if result is None:
        raise HTTPException(422, "Dépense vide ou déjà annulée")
    entry, _created = result
    return {"reference": entry.reference, "total": float(entry.total_debit)}


@router.post("/post/backfill")
async def backfill(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Comptabilise en masse tous les flux métier non encore comptabilisés.

    Parcourt les factures (statuts comptabilisables), paiements (paid/pending)
    et dépenses ; les sources déjà comptabilisées sont ignorées (idempotence
    via ``source_type``/``source_id``). Retourne le nombre d'écritures créées.
    """
    from datetime import date as date_type

    from sqlalchemy import select

    from app.modules.finance.models.expense import Expense
    from app.modules.invoicing.models.invoice import Invoice
    from app.modules.payments.models.payment import Payment

    service = PostingService(session)
    created = {"invoices": 0, "payments": 0, "expenses": 0}

    # Factures comptabilisables (exclut proforma/brouillon/annulée/avoir)
    result = await session.execute(
        select(Invoice).where(
            Invoice.status.notin_(["draft", "proforma", "cancelled", "credit"]),
        )
    )
    for invoice in result.scalars():
        posted = await service.post_invoice(invoice)
        if posted is not None and posted[1]:
            created["invoices"] += 1

    # Paiements
    result = await session.execute(
        select(Payment).where(Payment.status.in_(["paid", "pending"]))
    )
    for payment in result.scalars():
        posted = await service.post_payment(payment)
        if posted is not None and posted[1]:
            created["payments"] += 1

    # Dépenses
    result = await session.execute(select(Expense))
    for expense in result.scalars():
        posted = await service.post_expense(expense)
        if posted is not None and posted[1]:
            created["expenses"] += 1

    await session.commit()
    total = sum(created.values())
    return {
        "created": created,
        "total": total,
        "date": date_type.today().isoformat(),
        "message": (
            f"{total} écriture(s) créée(s) : "
            f"{created['invoices']} facture(s), {created['payments']} paiement(s), "
            f"{created['expenses']} dépense(s)."
        ) if total else "Aucun flux restant à comptabiliser.",
    }