"""
Service Écritures comptables (Grand Livre).

Responsabilités :
- création d'une écriture équilibrée (débit == crédit)
- contrôle du solde avant publication
- numérotation des écritures (via SequenceService)
- agrégation des mouvements par compte (pour balances)
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.modules.accounting.models.invoice_allocation import InvoiceAllocation
from app.modules.accounting.models.journal_entry import (
    JournalEntry,
    JournalEntryLine,
)
from app.modules.accounting.schemas import JournalEntryCreate
from app.modules.accounting.services.account_service import AccountService

logger = logging.getLogger(__name__)

BALANCE_EPSILON = Decimal("0.001")


class LedgerService:
    """Grand-livre : écritures comptables."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)
        self.accounts = AccountService(session)

    # ------------------------------------------------------------------ #
    # Création / publication
    # ------------------------------------------------------------------ #
    async def create_entry(
        self, company_id: int, data: JournalEntryCreate, *, post: bool = True
    ) -> JournalEntry:
        """Crée une écriture. Lève ``ValueError`` si non équilibrée."""
        total_debit = sum(Decimal(str(l.debit)) for l in data.lines)
        total_credit = sum(Decimal(str(l.credit)) for l in data.lines)
        if total_debit != total_credit:
            raise ValueError(
                f"Écriture non équilibrée : débit {total_debit} ≠ crédit {total_credit}"
            )
        if total_debit <= 0:
            raise ValueError("Écriture vide (aucun montant).")
        if not all(Decimal(str(l.debit)) * Decimal(str(l.credit)) == 0 for l in data.lines):
            raise ValueError("Une ligne ne peut pas être à la fois débit et crédit.")

        # Comptes existants
        accounts = {a.code: a for a in await self.accounts.list_accounts(
            company_id, active_only=False, limit=2000
        )}
        for line in data.lines:
            if line.account_code not in accounts:
                raise ValueError(f"Compte inconnu : {line.account_code}")

        reference = await self.sequences.next_value(
            "journal_entry", "EC", company_id=company_id
        )

        entry = JournalEntry(
            reference=reference,
            entry_date=data.entry_date,
            journal_code=data.journal_code,
            source_type=data.source_type,
            source_id=data.source_id,
            description=data.description,
            total_debit=total_debit,
            total_credit=total_credit,
            status="draft",
            company_id=company_id,
        )
        for i, l in enumerate(data.lines):
            entry.lines.append(
                JournalEntryLine(
                    account_code=l.account_code,
                    label=l.label,
                    debit=l.debit,
                    credit=l.credit,
                    partner_id=l.partner_id,
                    position=i,
                    company_id=company_id,
                )
            )
        self.session.add(entry)
        await self.session.flush()

        if post:
            await self.post_entry(entry.id, company_id)
        return entry

    async def post_entry(self, entry_id: int, company_id: int) -> JournalEntry:
        """Valide et publie une écriture (draft → posted)."""
        entry = await self.get_entry(entry_id, company_id)
        if entry is None:
            raise ValueError(f"Écriture {entry_id} introuvable")
        if entry.status == "posted":
            return entry
        total_debit = sum(Decimal(str(l.debit)) for l in entry.lines)
        total_credit = sum(Decimal(str(l.credit)) for l in entry.lines)
        if abs(total_debit - total_credit) > BALANCE_EPSILON:
            raise ValueError(
                f"Écriture {entry.reference} non équilibrée : "
                f"{total_debit} ≠ {total_credit}"
            )
        entry.status = "posted"
        await self.session.flush()
        return entry

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def get_entry(
        self, entry_id: int, company_id: int
    ) -> JournalEntry | None:
        result = await self.session.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(
                JournalEntry.id == entry_id,
                JournalEntry.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_entries(
        self, company_id: int, skip: int = 0, limit: int = 100,
        account_code: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        journal_code: str | None = None,
    ) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.company_id == company_id)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
            .offset(skip)
            .limit(limit)
        )
        if account_code:
            stmt = stmt.join(JournalEntryLine).where(
                JournalEntryLine.account_code == account_code
            )
        if date_from:
            stmt = stmt.where(JournalEntry.entry_date >= date_from)
        if date_to:
            stmt = stmt.where(JournalEntry.entry_date <= date_to)
        if journal_code:
            stmt = stmt.where(JournalEntry.journal_code == journal_code)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    # ------------------------------------------------------------------ #
    # Agrégats
    # ------------------------------------------------------------------ #
    async def account_balances(
        self, company_id: int, account_code: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ) -> list[dict]:
        """Soldes par compte (débit, crédit, solde) sur les écritures publiées."""
        stmt = (
            select(
                JournalEntryLine.account_code,
                func.coalesce(func.sum(JournalEntryLine.debit), 0),
                func.coalesce(func.sum(JournalEntryLine.credit), 0),
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
            )
            .group_by(JournalEntryLine.account_code)
            .order_by(JournalEntryLine.account_code)
        )
        if account_code:
            stmt = stmt.where(JournalEntryLine.account_code == account_code)
        if date_from:
            stmt = stmt.where(JournalEntry.entry_date >= date_from)
        if date_to:
            stmt = stmt.where(JournalEntry.entry_date <= date_to)
        result = await self.session.execute(stmt)
        rows = []
        for code, debit, credit in result.all():
            debit = Decimal(str(debit))
            credit = Decimal(str(credit))
            rows.append(
                {
                    "account_code": code,
                    "debit": float(debit),
                    "credit": float(credit),
                    "balance": float(debit - credit),
                }
            )
        return rows

    # ------------------------------------------------------------------ #
    # Grand livre — mouvements d'un compte avec solde cumulé
    # ------------------------------------------------------------------ #
    async def account_movements(
        self, company_id: int, account_code: str,
        date_from: date | None = None, date_to: date | None = None,
    ) -> tuple[list[dict], float, float, float, float]:
        """Mouvements chronologiques d'un compte + soldes (ouv., clôt.) débit/crédit.

        Retourne ``(movements, opening_balance, closing_balance, total)`` où
        ``opening_balance`` = solde cumulé avant ``date_from`` (ou 0).
        """
        stmt = (
            select(
                JournalEntryLine.entry_id,
                JournalEntry.reference,
                JournalEntry.entry_date,
                JournalEntry.journal_code,
                JournalEntryLine.label,
                JournalEntryLine.debit,
                JournalEntryLine.credit,
                JournalEntryLine.position,
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
                JournalEntryLine.account_code == account_code,
            )
            .order_by(JournalEntry.entry_date, JournalEntry.id, JournalEntryLine.position)
        )
        rows = (await self.session.execute(stmt)).all()

        # Solde d'ouverture (mouvements avant la période)
        opening = 0.0
        if date_from:
            opening_stmt = (
                select(
                    func.coalesce(func.sum(JournalEntryLine.debit), 0)
                    - func.coalesce(func.sum(JournalEntryLine.credit), 0)
                )
                .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
                .where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.status == "posted",
                    JournalEntryLine.account_code == account_code,
                    JournalEntry.entry_date < date_from,
                )
            )
            opening = float((await self.session.execute(opening_stmt)).scalar() or 0)

        movements = []
        running = opening
        for entry_id, reference, entry_date, journal_code, label, debit, credit, pos in rows:
            running += float(debit) - float(credit)
            movements.append(
                {
                    "entry_id": entry_id,
                    "reference": reference,
                    "entry_date": entry_date,
                    "journal_code": journal_code,
                    "label": label,
                    "debit": float(debit),
                    "credit": float(credit),
                    "balance": round(running, 2),
                }
            )
        total_debit = sum(m["debit"] for m in movements)
        total_credit = sum(m["credit"] for m in movements)
        closing = opening + total_debit - total_credit
        return movements, opening, closing, total_debit, total_credit


    # ------------------------------------------------------------------ #
    # Lettrage tiers — rapprochement paiement ↔ facture
    # ------------------------------------------------------------------ #
    async def allocate_payment(
        self,
        company_id: int,
        invoice_id: int,
        payment_id: int,
        allocated_amount: float,
        allocation_date: date,
        notes: str | None = None,
    ) -> InvoiceAllocation:
        """Alloue un paiement à une facture (lettrage tiers).

        Vérifie que le montant alloué ne dépasse ni le solde restant de la
        facture, ni le solde disponible du paiement. L'écriture comptable
        sous-jacente (D 511 / C 411 ou D 401 / C 511) a déjà été créée lors
        de la comptabilisation du paiement ; ce lettrage est un marquage
        analytique qui lie les deux documents.
        """
        from app.modules.invoicing.models.invoice import Invoice
        from app.modules.payments.models.payment import Payment

        invoice = await self.session.get(Invoice, invoice_id)
        if invoice is None or invoice.company_id != company_id:
            raise ValueError(f"Facture {invoice_id} introuvable pour cette entreprise")

        payment = await self.session.get(Payment, payment_id)
        if payment is None or payment.company_id != company_id:
            raise ValueError(f"Paiement {payment_id} introuvable pour cette entreprise")

        # Solde restant de la facture (montant total - déjà alloué)
        existing_alloc = await self.session.execute(
            select(func.coalesce(func.sum(InvoiceAllocation.allocated_amount), 0)).where(
                InvoiceAllocation.invoice_id == invoice_id
            )
        )
        allocated_so_far = float(existing_alloc.scalar() or 0)
        invoice_remaining = float(invoice.amount_total) - allocated_so_far

        # Solde disponible du paiement (montant - déjà alloué sur ce paiement)
        existing_pay_alloc = await self.session.execute(
            select(func.coalesce(func.sum(InvoiceAllocation.allocated_amount), 0)).where(
                InvoiceAllocation.payment_id == payment_id
            )
        )
        payment_allocated = float(existing_pay_alloc.scalar() or 0)
        payment_remaining = float(payment.amount) - payment_allocated

        if allocated_amount <= 0:
            raise ValueError("Le montant alloué doit être positif")
        if allocated_amount > invoice_remaining:
            raise ValueError(
                f"Montant alloué {allocated_amount} dépasse le solde restant de la facture ({invoice_remaining})"
            )
        if allocated_amount > payment_remaining:
            raise ValueError(
                f"Montant alloué {allocated_amount} dépasse le solde disponible du paiement ({payment_remaining})"
            )

        allocation = InvoiceAllocation(
            invoice_id=invoice_id,
            payment_id=payment_id,
            allocated_amount=allocated_amount,
            allocation_date=allocation_date,
            notes=notes,
            company_id=company_id,
        )
        self.session.add(allocation)
        await self.session.flush()
        return allocation

    async def get_allocations_for_invoice(
        self, company_id: int, invoice_id: int
    ) -> list[InvoiceAllocation]:
        """Retourne tous les lettrages d'une facture."""
        stmt = select(InvoiceAllocation).where(
            InvoiceAllocation.company_id == company_id,
            InvoiceAllocation.invoice_id == invoice_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_allocations_for_payment(
        self, company_id: int, payment_id: int
    ) -> list[InvoiceAllocation]:
        """Retourne tous les lettrages d'un paiement."""
        stmt = select(InvoiceAllocation).where(
            InvoiceAllocation.company_id == company_id,
            InvoiceAllocation.payment_id == payment_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


__all__ = ["LedgerService"]