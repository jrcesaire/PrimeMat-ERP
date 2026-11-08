"""Service de comptabilisation automatique (Partie 3).

Génère les écritures comptables OHADA à partir des flux métier :

- **Facture client**      → débit client / crédit ventes + TVA facturée
- **Facture fournisseur** → débit achats + TVA déductible / crédit fournisseur
- **Paiement reçu**       → débit banque ou caisse / crédit client
- **Paiement émis**       → débit fournisseur / crédit banque ou caisse
- **Dépense**             → débit compte de charge / crédit banque ou caisse
- **Avoir**               → selon le sens (client ou fournisseur)

Aucun code de compte n'est écrit en dur : chaque compte est désigné par une
**clé métier** (``customers``, ``tax_collected``, ``bank``…) que la table
d'alias du référentiel de l'entreprise résout en code — SYSCOHADA commercial ou
SYCEBNL —, puisque le SYSCOHADA Révisé a lui-même renuméroté les classes 1, 5,
6 et 7.

Chaque écriture porte ``source_type``/``source_id`` pour l'**idempotence** :
une source déjà comptabilisée n'est jamais comptabilisée deux fois.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.data import (
    expense_key,
    resolve_accounts,
    treasury_kind,
)
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
# Aucun code de compte n'est codé en dur : le vocabulaire métier (mode de
# règlement, catégorie de dépense) est traduit en **clés d'alias** par
# ``app.modules.accounting.data``, puis résolu en code de compte selon le
# référentiel de l'entreprise.


class PostingService:
    """Comptabilisation automatique des flux métier (idempotente)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger = LedgerService(session)
        self._alias: dict[str, str] | None = None

    # ------------------------------------------------------------------ #
    # Résolution des comptes du référentiel
    # ------------------------------------------------------------------ #
    async def _aliases(self, company_id: int) -> dict[str, str]:
        """Table d'alias du référentiel de l'entreprise (mise en cache)."""
        if self._alias is None:
            template = await AccountService(self.session).company_template(company_id)
            self._alias = resolve_accounts(template)
        return self._alias

    async def _code(self, company_id: int, key: str) -> str:
        """Code du compte désigné par ``key`` pour le référentiel courant."""
        try:
            return (await self._aliases(company_id))[key]
        except KeyError:
            raise ValueError(
                "Le référentiel comptable de l'entreprise ne définit pas "
                f"le compte « {key} »."
            ) from None

    async def _code_or(self, company_id: int, key: str, fallback: str) -> str:
        """Code de ``key``, ou celui de ``fallback`` si le référentiel l'ignore.

        Le SYCEBNL ne distingue par exemple pas les ventes retournées : l'avoir
        client y contre-passe alors directement le compte de ventes.
        """
        aliases = await self._aliases(company_id)
        return aliases.get(key) or await self._code(company_id, fallback)

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
        # Le plan du référentiel doit exister avant toute écriture : c'est ici
        # que le seed est garanti, une fois pour toutes les sources.
        await AccountService(self.session).ensure_seeded(company_id)
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
        untaxed = total - tax  # garantit l'équilibre client = ventes + TVA

        customer = await self._code(invoice.company_id, "customers")
        revenue = await self._code(invoice.company_id, "sales_revenue")
        tax_account = await self._code(invoice.company_id, "tax_collected")

        lines = [
            JournalEntryLineCreate(
                account_code=customer,
                label=f"Client — facture {invoice.reference}",
                debit=float(total),
                credit=0,
                partner_id=invoice.partner_id,
            )
        ]
        if untaxed > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code=revenue,
                    label=f"Ventes — facture {invoice.reference}",
                    debit=0,
                    credit=float(untaxed),
                )
            )
        if tax > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code=tax_account,
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

        purchase = await self._code(invoice.company_id, "purchases")
        tax_account = await self._code(invoice.company_id, "tax_deductible")
        supplier = await self._code(invoice.company_id, "suppliers")

        lines = [
            JournalEntryLineCreate(
                account_code=purchase,
                label=f"Achats marchandises - {number}",
                debit=float(untaxed),
                credit=0,
                partner_id=invoice.supplier_id,
            ),
        ]
        if tax > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code=tax_account,
                    label=f"TVA deductible - {number}",
                    debit=float(tax),
                    credit=0,
                    partner_id=invoice.supplier_id,
                )
            )
        lines.append(
            JournalEntryLineCreate(
                account_code=supplier,
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
        self,
        invoice,
        amount: float,
        payment_date: date | None = None,
        *,
        treasury: str = "bank",
        treasury_account: str | None = None,
        journal_code: str | None = None,
    ) -> tuple[JournalEntry, bool] | None:
        """Règlement fournisseur : D fournisseur / C trésorerie.

        ``treasury`` désigne la **nature** de trésorerie décaissée — ``bank``
        (journal ``BAN``) par défaut, ``cash`` (journal ``CAI``) pour un achat
        comptoir saisi depuis le Point de Vente. ``treasury_account`` permet de
        forcer un compte précis du plan ; ``journal_code`` fixe alors le journal.

        Idempotence via ``source_type="supplier_payment"`` /
        ``source_id=invoice.id`` (un règlement cumulé par facture).
        """
        total = Decimal(str(amount or 0))
        if total <= 0:
            return None

        company_id = invoice.company_id
        debit_account = await self._code(company_id, "suppliers")
        credit_account = treasury_account or await self._code(company_id, treasury)
        if journal_code is None:
            journal_code = "CAI" if treasury == "cash" else "BAN"

        number = getattr(invoice, "reference", None) or getattr(invoice, "number", "") or ""
        lines = [
            JournalEntryLineCreate(
                account_code=debit_account,
                label=f"Fournisseur - reglement {number}",
                debit=float(total),
                credit=0,
                partner_id=invoice.supplier_id,
            ),
            JournalEntryLineCreate(
                account_code=credit_account,
                label=f"Decaissement {number}",
                debit=0,
                credit=float(total),
            ),
        ]

        data = JournalEntryCreate(
            entry_date=payment_date or date.today(),
            journal_code=journal_code,
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

        kind = treasury_kind(payment.method)
        treasury = await self._code(payment.company_id, kind)
        # Journal explicite porté par le paiement (caisse, banque, mobile
        # money...) ; à défaut, déduit de la nature de trésorerie.
        journal = (getattr(payment, "journal_code", None) or "").strip() or (
            "CAI" if kind == "cash" else "BAN"
        )

        customer = await self._code(payment.company_id, "customers")
        supplier = await self._code(payment.company_id, "suppliers")

        if payment.direction == "in":
            lines = [
                JournalEntryLineCreate(
                    account_code=treasury,
                    label=f"Encaissement {payment.reference}",
                    debit=float(amount),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code=customer,
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
                    account_code=supplier,
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

        company_id = expense.company_id
        charge_account = await self._code(company_id, expense_key(expense.category))
        kind = treasury_kind(expense.payment_method)
        treasury = await self._code(company_id, kind)

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
            journal_code="CAI" if kind == "cash" else "BAN",
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

        company_id = credit_note.company_id
        customer = await self._code(company_id, "customers")
        supplier = await self._code(company_id, "suppliers")
        tax_collected = await self._code(company_id, "tax_collected")
        tax_deductible = await self._code(company_id, "tax_deductible")
        purchase_discounts = await self._code(company_id, "purchase_discounts")
        # Le SYCEBNL ne distingue pas les ventes retournées : repli sur les ventes.
        sales_returns = await self._code_or(company_id, "sales_discounts", "sales_revenue")

        if credit_note.type == "customer":
            # Avoir client : D ventes retournées (HT) + D TVA à répercuter / C client
            lines = [
                JournalEntryLineCreate(
                    account_code=sales_returns,
                    label=f"Ventes retournées — {credit_note.reference}",
                    debit=float(untaxed),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code=tax_collected,
                    label=f"TVA à répercuter — {credit_note.reference}",
                    debit=float(tax),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code=customer,
                    label=f"Client — avoir {credit_note.reference}",
                    debit=0,
                    credit=float(total),
                    partner_id=partner_id,
                ),
            ]
        else:
            # Avoir fournisseur : D fournisseur / C achats retournés (HT) + C TVA déductible
            lines = [
                JournalEntryLineCreate(
                    account_code=supplier,
                    label=f"Fournisseur — avoir {credit_note.reference}",
                    debit=float(total),
                    credit=0,
                    partner_id=partner_id,
                ),
                JournalEntryLineCreate(
                    account_code=purchase_discounts,
                    label=f"Achats retournés — {credit_note.reference}",
                    debit=0,
                    credit=float(untaxed),
                ),
                JournalEntryLineCreate(
                    account_code=tax_deductible,
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

    # ------------------------------------------------------------------ #
    # Paie (module Payroll)
    # ------------------------------------------------------------------ #
    async def post_payslip(self, payslip) -> tuple[JournalEntry, bool] | None:
        """Bulletin de paie : D 661 / C 422 + C 43x + C 447 (journal PAI).

        - Débit : charges de personnel (brut) + charges patronales ;
        - Crédit : net à payer, cotisations sociales (salariales + patronales),
          impôt sur salaires (ITS).

        Idempotent via ``source_type="payslip"`` / ``source_id``.
        """
        if payslip.state not in ("done", "paid"):
            return None

        company_id = payslip.company_id
        gross = Decimal(str(payslip.gross or 0))
        net = Decimal(str(payslip.net_wage or 0))
        employer_cost = Decimal(str(payslip.employer_cost or 0))
        patronal = employer_cost - gross
        if gross <= 0 and net <= 0 and patronal <= 0:
            return None

        salaries = await self._code(company_id, "salaries")
        payable = await self._code(company_id, "payroll_payable")
        social = await self._code_or(company_id, "social_charges", "salaries")
        tax = await self._code_or(company_id, "income_tax", "taxes")

        social_total = Decimal("0")
        tax_total = Decimal("0")
        for line in payslip.lines:
            category = (line.category_code or "").upper()
            amount = Decimal(str(line.total or 0))
            if category == "COTIS":
                social_total += amount
            elif category == "IMPOT":
                tax_total += amount

        employee = getattr(payslip, "employee", None)
        partner_id = getattr(employee, "partner_id", None)
        label = f"bulletin {payslip.number}"

        lines = []
        if gross > 0:
            lines.append(JournalEntryLineCreate(
                account_code=salaries, label=f"Charges de personnel — {label}",
                debit=float(gross), credit=0,
            ))
        if patronal > 0:
            lines.append(JournalEntryLineCreate(
                account_code=salaries, label=f"Charges patronales — {label}",
                debit=float(patronal), credit=0,
            ))
        if net > 0:
            lines.append(JournalEntryLineCreate(
                account_code=payable, label=f"Net à payer — {label}",
                debit=0, credit=float(net), partner_id=partner_id,
            ))
        social_due = social_total + patronal
        if social_due > 0:
            lines.append(JournalEntryLineCreate(
                account_code=social, label=f"Cotisations sociales — {label}",
                debit=0, credit=float(social_due),
            ))
        if tax_total > 0:
            lines.append(JournalEntryLineCreate(
                account_code=tax, label=f"Impôts sur salaires (ITS) — {label}",
                debit=0, credit=float(tax_total),
            ))

        data = JournalEntryCreate(
            entry_date=payslip.payment_date or date.today(),
            journal_code="PAI",
            source_type="payslip",
            source_id=payslip.id,
            description=f"Paie — {label}",
            lines=lines,
        )
        return await self._post(company_id, "payslip", payslip.id, data)


__all__ = ["PostingService"]