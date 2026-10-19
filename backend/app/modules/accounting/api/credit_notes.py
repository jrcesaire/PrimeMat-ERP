"""
API Comptabilité — avoirs / notes de crédit.

Routes préfixées par /api/v1/accounting, isolées par tenant (company_id).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.models.credit_note import CreditNote
from app.modules.accounting.schemas import (
    CreditNoteApply,
    CreditNoteCreate,
    CreditNoteIssue,
    CreditNoteRead,
    CreditNoteSummary,
    CreditNoteUpdate,
)
from app.modules.accounting.services.posting_service import PostingService

router = APIRouter()


# ------------------------------------------------------------------ #
# Création / lecture / mise à jour d'avoir
# ------------------------------------------------------------------ #
@router.post(
    "/credit-notes",
    response_model=CreditNoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_credit_note(
    body: CreditNoteCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Crée un avoir au statut draft (pas encore comptabilisé)."""
    from app.core.services.sequence_service import SequenceService

    body.company_id = company_id
    payload = body.model_dump()
    # La colonne reference est NOT NULL : numérotation via SequenceService
    # (même mécanique que INV pour les factures, BC pour les bons de commande).
    payload["reference"] = await SequenceService(session).next_value(
        "credit_note", "AV", company_id=company_id
    )
    cn = CreditNote(**payload)
    session.add(cn)
    await session.flush()
    await session.commit()
    return cn


@router.get(
    "/credit-notes",
    response_model=list[CreditNoteSummary],
)
async def list_credit_notes(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filtrer par statut (draft/issued/applied)"
    ),
    partner_id: int | None = Query(
        default=None, description="Filtrer par tiers (client/fournisseur)"
    ),
    cn_type: str | None = Query(
        default=None, alias="type", description="customer ou supplier"
    ),
    _: User = Depends(require_permission("journal_entry", "view")),
):
    """Liste les avoirs de l'entreprise."""
    from sqlalchemy import select

    stmt = select(CreditNote).where(CreditNote.company_id == company_id)
    if status_filter:
        stmt = stmt.where(CreditNote.status == status_filter)
    if partner_id is not None:
        stmt = stmt.where(CreditNote.partner_id == partner_id)
    if cn_type:
        stmt = stmt.where(CreditNote.type == cn_type)
    stmt = stmt.order_by(CreditNote.credit_date.desc(), CreditNote.id.desc())

    result = await session.execute(stmt)
    notes = result.scalars().all()
    return [
        CreditNoteSummary(
            id=n.id,
            reference=n.reference,
            type=n.type,
            amount_total=float(n.amount_total or 0),
            currency_code=n.currency_code,
            status=n.status,
            credit_date=n.credit_date,
            partner_id=n.partner_id,
            amount_due=float(n.amount_total or 0),
        )
        for n in notes
    ]


@router.get(
    "/credit-notes/{credit_note_id}",
    response_model=CreditNoteRead,
)
async def get_credit_note(
    credit_note_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "view")),
):
    """Récupère un avoir par son ID."""
    cn = await session.get(CreditNote, credit_note_id)
    if cn is None or cn.company_id != company_id:
        raise HTTPException(status_code=404, detail=f"Avoir {credit_note_id} introuvable")
    return cn


@router.put(
    "/credit-notes/{credit_note_id}",
    response_model=CreditNoteRead,
)
async def update_credit_note(
    credit_note_id: int,
    body: CreditNoteUpdate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Met à jour un avoir (seulement s'il est encore en draft)."""
    cn = await session.get(CreditNote, credit_note_id)
    if cn is None or cn.company_id != company_id:
        raise HTTPException(status_code=404, detail=f"Avoir {credit_note_id} introuvable")
    if cn.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de modifier un avoir déjà {cn.status}",
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cn, field, value)
    await session.commit()
    return cn


@router.post(
    "/credit-notes/{credit_note_id}/issue",
    response_model=CreditNoteRead,
)
async def issue_credit_note(
    credit_note_id: int,
    body: CreditNoteIssue,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Émet (comptabilise) un avoir : passe de draft → issued.

    Génère l'écriture comptable OHADA correspondante (source_type=credit_note).
    Idempotent : une écriture déjà existante pour ce source_id est ignorée.
    """
    cn = await session.get(CreditNote, credit_note_id)
    if cn is None or cn.company_id != company_id:
        raise HTTPException(status_code=404, detail=f"Avoir {credit_note_id} introuvable")
    if cn.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"L'avoir {cn.reference} est déjà {cn.status}",
        )

    # Générer une référence si absente
    if not cn.reference:
        from app.core.services.sequence_service import SequenceService

        seq = SequenceService(session)
        cn.reference = await seq.next_value("credit_note", company_id=company_id)

    # Mettre à jour la date / notes si fournis
    if body.credit_date:
        cn.credit_date = body.credit_date
    if body.notes is not None:
        cn.notes = body.notes

    # Comptabiliser via PostingService (idempotent par source_type/source_id)
    result = await PostingService(session).post_credit_note(cn)
    await session.commit()

    if result is None:
        raise HTTPException(
            status_code=422, detail="Avoir non comptabilisable (montant nul)"
        )

    entry, created = result
    if created:
        cn.journal_entry_id = entry.id
        cn.status = "issued"
        await session.commit()

    return cn


@router.post(
    "/credit-notes/{credit_note_id}/apply",
    response_model=CreditNoteRead,
)
async def apply_credit_note(
    credit_note_id: int,
    body: CreditNoteApply,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Impute un avoir sur sa facture d'origine : passe issued → applied.

    Réduit le solde restant de la facture (paid_amount) du montant imputé.
    Idempotent : un avoir déjà applied est retourné tel quel.
    """
    cn = await session.get(CreditNote, credit_note_id)
    if cn is None or cn.company_id != company_id:
        raise HTTPException(status_code=404, detail=f"Avoir {credit_note_id} introuvable")
    if cn.status == "applied":
        return cn
    if cn.status != "issued":
        raise HTTPException(
            status_code=400,
            detail=(
                f"L'avoir {cn.reference} doit être émis pour être imputé "
                f"(statut actuel : {cn.status})"
            ),
        )

    # Récupère la facture d'origine et vérifie la cohérence tiers / entreprise
    if cn.type == "customer":
        from app.modules.invoicing.models.invoice import Invoice

        invoice = await session.get(Invoice, body.invoice_id)
        if invoice is None or invoice.company_id != company_id:
            raise HTTPException(status_code=404, detail=f"Facture {body.invoice_id} introuvable")
        if invoice.partner_id != cn.partner_id:
            raise HTTPException(
                status_code=400,
                detail="Le tiers de l'avoir ne correspond pas au client de la facture",
            )
    else:
        from app.modules.purchases.models import SupplierInvoice

        invoice = await session.get(SupplierInvoice, body.invoice_id)
        if invoice is None or invoice.company_id != company_id:
            raise HTTPException(status_code=404, detail=f"Facture {body.invoice_id} introuvable")
        if invoice.supplier_id != cn.partner_id:
            raise HTTPException(
                status_code=400,
                detail="Le tiers de l'avoir ne correspond pas au fournisseur de la facture",
            )

    amount_to_apply = float(body.amount_to_apply or cn.amount_total or 0)
    remaining = float(invoice.amount_total) - float(invoice.paid_amount or 0)
    amount_to_apply = min(amount_to_apply, remaining)
    if amount_to_apply <= 0:
        raise HTTPException(status_code=400, detail="La facture est déjà soldée")

    invoice.paid_amount = float(invoice.paid_amount or 0) + amount_to_apply
    cn.status = "applied"
    cn.original_invoice_id = invoice.id

    await session.commit()
    await session.refresh(cn)
    return cn


__all__ = ["router"]