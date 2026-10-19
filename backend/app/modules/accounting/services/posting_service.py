"""Service de comptabilisation automatique (Partie 3).

Génère les écritures comptables OHADA à partir des flux métier :

- **Facture client**  → débit 411 (Client) / crédit 701 (Ventes) + 4431 (TVA facturée)
- **Facture fournisseur** → débit 601 (Achats) + 4452 (TVA déductible) / crédit 401 (Fournisseur)
- **Paiement reçu**   → débit 511/531 (Banque/Caisse) / crédit 411
- **Paiement émis**   → débit 401 (Fournisseur) / crédit 511/531
- **Dépense**         → débit compte de charge (selon catégorie) / crédit 511/531

Chaque écriture porte ``source_type``/``source_id`` pour l'**idempotence** :
une source déjà comptabilisée n'est jamais comptabilisée deux fois.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.schemas import (
    JournalEntryCreate,
    JournalEntryLineCreate,
)
from app.modules.accounting.services.account_service import AccountService
from app.modules.accounting.services.journal_service import LedgerService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------- #
# Mappings de comptabilisation
# ---------------------------------------------------------------------- #

# Méthode de paiement → compte de trésorerie (classe 5).
TREASURY_ACCOUNTS: dict[str, str] = {
    "cash": "531",           # Caisse - siège social
    "bank_transfer": "511",  # Banques locales
    "check": "511",
    "card": "511",
    "mobile_money": "511",
    "other": "511",
}

# Catégorie de dépense → compte de charge (classe 6).
EXPENSE_ACCOUNTS: dict[str, str] = {
    "achat": "601",            # Achats de marchandises
    "marchandise": "601",
    "stock": "601",
    "matiere": "6021",         # Achats de matières premières
    "fourniture": "6055",      # Fournitures de bureau non stockables
    "eau": "6051",
    "electricite": "6052",
    "electricity": "6052",
    "energie": "6053",
    "fuel": "6042",            # Matières combustibles
    "carburant": "6042",
    "transport": "612",        # Transports sur ventes
    "livraison": "612",
    "loyer": "621",            # Locations et charges locatives
    "entretien": "623",        # Entretien et réparations
    "maintenance": "6233",
    "assurance": "624",        # Assurances
    "publicite": "626",        # Publicité, relations publiques
    "marketing": "626",
    "documentation": "625",
    "telecom": "6271",         # Frais de téléphone
    "telephone": "6271",
    "internet": "6271",
    "frais_bancaires": "6288", # Autres frais bancaires
    "honoraires": "6293",
    "impots": "6318",          # Autres impôts et taxes directs
    "taxes": "6318",
    "salaire": "6411",         # Salaires, appointements et commissions
    "salaires": "6411",
    "personnel": "6411",
}
DEFAULT_EXPENSE_ACCOUNT = "6298"  # Divers frais


class PostingService:
    """Comptabilisation automatique des flux métier (idempotente)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger = LedgerService(session)

    # ------------------------------------------------------------------ #
    # Idempotence
    # ------------------------------------------------------------------ #
    async def find_by_source(
        self, company_id: int, source_type: str, source_id: int
    ) -> JournalEntry | None:
        """Retourne l'écriture déjà générée pour cette source, si présente."""
        result = await self.session.execute(
            select(JournalEntry).where(
                JournalEntry.company_id == company_id,
                JournalEntry.source_type == source_type,
                JournalEntry.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def _post(
        self,
        company_id: int,
        source_type: str,
        source_id: int,
        data: JournalEntryCreate,
    ) -> tuple[JournalEntry, bool]:
        """Crée l'écriture sauf si la source a déjà été comptabilisée.

        Retourne ``(écriture, créée)`` — ``créée`` est faux si la source
        avait déjà été comptabilisée (idempotence).
        """
        existing = await self.find_by_source(company_id, source_type, source_id)
        if existing is not None:
            logger.info(
                "Source %s#%s déjà comptabilisée (%s) — ignorée",
                source_type, source_id, existing.reference,
            )
            return existing, False
        entry = await self.ledger.create_entry(company_id, data, post=True)
        logger.info(
            "Écriture %s générée pour %s#%s (%.2f)",
            entry.reference, source_type, source_id, float(entry.total_debit),
        )
        return entry, True

    # ------------------------------------------------------------------ #
    # Facture client (vente)
    # ------------------------------------------------------------------ #
    async def post_invoice(self, invoice) -> tuple[JournalEntry, bool] | None:
        """Facture client : D 411 / C 701 + C 4431.

        Nécessite un statut comptabilisable (posted/paid/partially_paid).
        """
        if invoice.status in ("draft", "proforma", "cancelled", "credit"):
            logger.info(
                "Facture %s non comptabilisable (statut %s)",
                invoice.reference, invoice.status,
            )
            return None

        total = Decimal(str(invoice.amount_total or 0))
        tax = Decimal(str(invoice.tax_amount or 0))
        if total <= 0:
            return None
        if tax < 0 or tax > total:
            tax = Decimal("0")
        untaxed = total - tax  # garantit l'équilibre 411 = 701 + 4431

        lines = [
            JournalEntryLineCreate(
                account_code="411",
                label=f"Client — facture {invoice.reference}",
                debit=float(total),
                credit=0,
                partner_id=invoice.partner_id,
            )
        ]
        if untaxed > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code="701",
                    label=f"Ventes de marchandises — facture {invoice.reference}",
                    debit=0,
                    credit=float(untaxed),
                )
            )
        if tax > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code="4431",
                    label=f"TVA facturée — facture {invoice.reference}",
                    debit=0,
                    credit=float(tax),
                )
            )

        data = JournalEntryCreate(
            entry_date=invoice.invoice_date or date.today(),
            journal_code="VTE",
            source_type="invoice",
            source_id=invoice.id,
            description=f"Vente — facture {invoice.reference}",
            lines=lines,
        )
        return await self._post(invoice.company_id, "invoice", invoice.id, data)

    # ------------------------------------------------------------------
    # Facture fournisseur (module Achats)
    # ------------------------------------------------------------------
    async def post_supplier_invoice(self, invoice) -> tuple[JournalEntry, bool] | None:
        """Facture fournisseur : D 601 + D 4452 / C 401 (journal ACH).

        L'idempotence est assurée par ``_post`` via
        ``source_type="supplier_invoice"`` / ``source_id``.
        """
        number = getattr(invoice, "reference", None) or getattr(invoice, "number", "") or ""
        total = Decimal(str(invoice.amount_total or 0))
        if total <= 0:
            return None
        untaxed = Decimal(str(invoice.amount_untaxed or 0))
        tax = Decimal(str(invoice.tax_amount or 0))
        if untaxed <= 0:
            untaxed = total - tax
        if untaxed <= 0:
            untaxed = total
            tax = Decimal("0")

        await AccountService(self.session).ensure_seeded(invoice.company_id)

        lines = [
            JournalEntryLineCreate(
                account_code="601",
                label=f"Achats marchandises - {number}",
                debit=float(untaxed),
                credit=0,
                partner_id=invoice.supplier_id,
            ),
        ]
        if tax > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code="4452",
                    label=f"TVA deductible - {number}",
                    debit=float(tax),
                    credit=0,
                    partner_id=invoice.supplier_id,
                )
            )
        lines.append(
            JournalEntryLineCreate(
                account_code="401",
                label=f"Fournisseur - {number}",
                debit=0,
                credit=float(total),
                partner_id=invoice.supplier_id,
            )
        )

        data = JournalEntryCreate(
            entry_date=invoice.invoice_date or date.today(),
            journal_code="ACH",
            source_type="supplier_invoice",
            source_id=invoice.id,
            description=f"Facture fournisseur - {number}",
            lines=lines,
        )
        return await self._post(invoice.company_id, "supplier_invoice", invoice.id, data)

    async def post_supplier_payment(
        self, invoice, amount: float, payment_date: date | None = None
    ) -> tuple[JournalEntry, bool] | None:
        """Règlement fournisseur : D 401 / C 511 (journal BAN).

        Idempotence via ``source_type="supplier_payment"`` /
        ``source_id=invoice.id`` (un règlement cumulé par facture).
        """
        total = Decimal(str(amount or 0))
        if total <= 0:
            return None

        await AccountService(self.session).ensure_seeded(invoice.company_id)

        number = getattr(invoice, "reference", None) or getattr(invoice, "number", "") or ""
        lines = [
            JournalEntryLineCreate(
                account_code="401",
                label=f"Fournisseur - reglement {number}",
                debit=float(total),
                credit=0,
                partner_id=invoice.supplier_id,
            ),
            JournalEntryLineCreate(
                account_code="511",
                label=f"Decaissement {number}",
                debit=0,
                credit=float(total),
            ),
        ]

        data = JournalEntryCreate(
            entry_date=payment_date or date.today(),
            journal_code="BAN",
            source_type="supplier_payment",
            source_id=invoice.id,
            description=f"Paiement fournisseur - {number}",
            lines=lines,
        )
        return await self._post(
            invoice.company_id, "supplier_payment", invoice.id, data
        )

    # ------------------------------------------------------------------ #
    # Paiement (encaissement / décaissement)
    # ------------------------------------------------------------------ #
    async def post_payment(self, payment) -> tuple[JournalEntry, bool] | None:
        """Paiement : D 511|531 / C 411 (reçu) ou D 401 / C 511|531 (émis)."""
        if payment.status not in ("paid", "pending"):
            logger.info(
                "Paiement %s non comptabilisable (statut %s)",
                payment.reference, payment.status,
            )
            return None

        amount = Decimal(str(payment.amount or 0))
        if amount <= 0:
            return None

        treasury = TREASURY_ACCOUNTS.get(payment.method, "511")
        # Journal explicite porté par le paiement (caisse, banque, mobile
        # money...) ; à défaut, déduit du mode d'encaissement.
        journal = (getattr(payment, "journal_code", None) or "").strip() or (
            "BAN" if treasury == "511" else "CAI"
        )

        if payment.direction == "in":
            lines = [
                JournalEntryLineCreate(
                    account_code=treasury,
                    label=f"Encaissement {payment.reference}",
                    debit=float(amount),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code="411",
                    label=f"Client — règlement {payment.reference}",
                    debit=0,
                    credit=float(amount),
                    partner_id=payment.partner_id,
                ),
            ]
            description = f"Encaissement client — {payment.reference}"
        else:
            lines = [
                JournalEntryLineCreate(
                    account_code="401",
                    label=f"Fournisseur — règlement {payment.reference}",
                    debit=float(amount),
                    credit=0,
                    partner_id=payment.partner_id,
                ),
                JournalEntryLineCreate(
                    account_code=treasury,
                    label=f"Décaissement {payment.reference}",
                    debit=0,
                    credit=float(amount),
                ),
            ]
            description = f"Paiement fournisseur — {payment.reference}"

        data = JournalEntryCreate(
            entry_date=payment.payment_date or date.today(),
            journal_code=journal,
            source_type="payment",
            source_id=payment.id,
            description=description,
            lines=lines,
        )
        return await self._post(payment.company_id, "payment", payment.id, data)

    # ------------------------------------------------------------------ #
    # Dépense
    # ------------------------------------------------------------------ #
    async def post_expense(self, expense) -> tuple[JournalEntry, bool] | None:
        """Dépense : D compte de charge (selon catégorie) / C 511|531."""
        amount = Decimal(str(expense.amount or 0))
        if amount <= 0:
            return None

        charge_account = EXPENSE_ACCOUNTS.get(
            (expense.category or "").lower(), DEFAULT_EXPENSE_ACCOUNT
        )
        treasury = TREASURY_ACCOUNTS.get(expense.payment_method, "531")

        lines = [
            JournalEntryLineCreate(
                account_code=charge_account,
                label=f"{expense.label} — {expense.reference}",
                debit=float(amount),
                credit=0,
            ),
            JournalEntryLineCreate(
                account_code=treasury,
                label=f"Décaissement — {expense.reference}",
                debit=0,
                credit=float(amount),
            ),
        ]

        data = JournalEntryCreate(
            entry_date=expense.expense_date or date.today(),
            journal_code="CAI" if treasury == "531" else "BAN",
            source_type="expense",
            source_id=expense.id,
            description=f"Dépense — {expense.label}",
            lines=lines,
        )
        return await self._post(expense.company_id, "expense", expense.id, data)

    # ------------------------------------------------------------------ #
    # Avoir / note de crédit
    # ------------------------------------------------------------------ #
    async def post_credit_note(self, credit_note) -> tuple[JournalEntry, bool] | None:
        """Avoir : comptabilisation OHADA selon le sens (client / fournisseur).

        - Avoir client   : D 709 (ventes retournées) + 4431 (TVA collectée) / C 411 (client)
        - Avoir fournisseur : D 401 (fournisseur) / C 609 (achats retournés) + 4452 (TVA déductible)
        """
        total = Decimal(str(credit_note.amount_total or 0))
        tax = Decimal(str(credit_note.tax_amount or 0))
        if total <= 0:
            return None

        untaxed = Decimal(str(credit_note.amount_untaxed or 0))
        if untaxed <= 0:
            untaxed = total - tax
        if untaxed <= 0:
            untaxed = total
            tax = Decimal("0")

        credit_date = getattr(credit_note, "credit_date", None) or date.today()
        description = f"Avoir {credit_note.type} — {credit_note.reference}"
        source_type = "credit_note"
        source_id = credit_note.id
        partner_id = getattr(credit_note, "partner_id", None)

        if credit_note.type == "customer":
            # Avoir client : D 709 (ventes retournées HT) + D 4431 (TVA à répercuter) / C 411 (client)
            lines = [
                JournalEntryLineCreate(
                    account_code="709",
                    label=f"Ventes retournées — {credit_note.reference}",
                    debit=float(untaxed),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code="4431",
                    label=f"TVA à répercuter — {credit_note.reference}",
                    debit=float(tax),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code="411",
                    label=f"Client — avoir {credit_note.reference}",
                    debit=0,
                    credit=float(total),
                    partner_id=partner_id,
                ),
            ]
        else:
            # Avoir fournisseur : D 401 (fournisseur) / C 609 (achats retournés HT) + C 4452 (TVA déductible)
            lines = [
                JournalEntryLineCreate(
                    account_code="401",
                    label=f"Fournisseur — avoir {credit_note.reference}",
                    debit=float(total),
                    credit=0,
                    partner_id=partner_id,
                ),
                JournalEntryLineCreate(
                    account_code="609",
                    label=f"Achats retournés — {credit_note.reference}",
                    debit=0,
                    credit=float(untaxed),
                ),
                JournalEntryLineCreate(
                    account_code="4452",
                    label=f"TVA déductible — {credit_note.reference}",
                    debit=0,
                    credit=float(tax),
                ),
            ]

        data = JournalEntryCreate(
            entry_date=credit_date,
            journal_code="ODM",
            source_type=source_type,
            source_id=source_id,
            description=description,
            lines=lines,
        )
        return await self._post(credit_note.company_id, source_type, source_id, data)


__all__ = ["PostingService", "TREASURY_ACCOUNTS", "EXPENSE_ACCOUNTS"]