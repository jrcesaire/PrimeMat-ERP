"""
Service États financiers (SYSCOHADA).

Fournit :
- ``balance_report``   — balance générale (soldes débit/crédit par compte)
- ``trial_balance``    — balance de vérification (soldes non nuls)
- ``general_ledger``   — grand livre d'un compte (mouvements + cumul)
- ``journal_report``   — journal général (écritures d'une période)
- ``income_statement`` — compte de résultat (produits - charges)
- ``balance_sheet``    — bilan (actif / passif par grandes masses)

Principes :
- seules les écritures ``posted`` sont prises en compte
- le multi-entreprise est géré via ``company_id`` (tenant)
- les montants sont renvoyés en float, arrondis à 2 décimales
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.journal_entry import JournalEntry, JournalEntryLine
from app.modules.accounting.services.account_service import AccountService
from app.modules.accounting.services.journal_service import LedgerService
from app.modules.crm.models.partner import Partner
from app.modules.invoicing.models.invoice import Invoice
from app.modules.purchases.models import SupplierInvoice

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Sections du bilan — (libellé, préfixes de comptes)
# ------------------------------------------------------------------ #
# Sections du bilan — (libellé, préfixes de comptes, est une déduction).
#
# Une section « déduction » regroupe les comptes d'amortissements et de
# dépréciations (soldes normalement créditeurs) : ils réduisent l'actif.
# Les comptes « mixtes » (42x, 43x, 44x, 46x, 47x) sont classés selon le
# signe de leur solde : débit → actif, crédit → passif.
BALANCE_SHEET_ASSETS: list[tuple[str, list[str], bool]] = [
    ("Charges immobilisées", ["201", "202", "206"], False),
    ("Immobilisations incorporelles", ["21"], False),
    ("Immobilisations corporelles", ["22", "23", "24"], False),
    ("Immobilisations financières", ["25", "26", "27"], False),
    ("Amortissements et dépréciations des immobilisations", ["28", "29"], True),
    ("Stocks et encours", ["31", "32", "33", "34", "35", "36", "37", "38"], False),
    ("Dépréciations des stocks", ["39"], True),
    ("Clients et comptes rattachés", ["409", "41"], False),
    ("Autres créances", ["408", "42", "43", "44", "45", "46", "47", "48"], False),
    ("Dépréciations des comptes de tiers", ["49"], True),
    ("Trésorerie-actif", ["50", "51", "52", "53", "54", "55", "57", "58"], False),
    ("Dépréciations de trésorerie", ["59"], True),
]

BALANCE_SHEET_LIABILITIES: list[tuple[str, list[str]]] = [
    ("Capital social", ["101", "102", "103", "109"]),
    ("Primes et réserves", ["104", "105", "106", "107", "108", "15"]),
    ("Report à nouveau", ["11"]),
    ("Résultat net de l'exercice", ["12"]),
    ("Subventions d'investissement", ["13"]),
    ("Provisions réglementées", ["14"]),
    ("Dettes financières et assimilées", ["16", "17", "18"]),
    ("Provisions financières pour risques et charges", ["19"]),
    ("Fournisseurs et comptes rattachés", ["40"]),
    ("Dettes fiscales et sociales", ["42", "43", "44", "45"]),
    ("Autres dettes", ["46", "47"]),
    ("Produits constatés d'avance", ["486"]),
    ("Trésorerie-passif", ["51", "52", "56", "57", "58"]),
]


# ------------------------------------------------------------------ #
# Sections du compte de résultat
# ------------------------------------------------------------------ #
INCOME_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("Ventes", "income", ["70", "71", "72", "73"]),
    ("Subventions d'exploitation", "income", ["74"]),
    ("Autres produits d'exploitation", "income", ["75", "78", "79"]),
    ("Produits financiers", "income", ["76"]),
    ("Produits exceptionnels", "income", ["77"]),
]

EXPENSE_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("Achats", "expense", ["60"]),
    ("Transports", "expense", ["61"]),
    ("Services extérieurs", "expense", ["62"]),
    ("Impôts et taxes", "expense", ["63"]),
    ("Charges de personnel", "expense", ["64"]),
    ("Autres charges d'exploitation", "expense", ["65", "68"]),
    ("Charges financières", "expense", ["66"]),
    ("Charges exceptionnelles", "expense", ["67"]),
    ("Impôts sur le résultat", "expense", ["69"]),
]


class FinancialService:
    """États financiers SYSCOHADA."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountService(session)
        self.ledger = LedgerService(session)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    async def _account_map(self, company_id: int) -> dict[str, Account]:
        rows = await self.accounts.list_accounts(
            company_id, active_only=False, limit=2000
        )
        return {a.code: a for a in rows}

    # ------------------------------------------------------------------ #
    # Balance générale
    # ------------------------------------------------------------------ #
    async def balance_report(
        self, company_id: int, date_from: date | None = None, date_to: date | None = None
    ) -> dict:
        """Balance générale : soldes débit/crédit par compte (toutes classes)."""
        balances = await self.ledger.account_balances(
            company_id, date_from=date_from, date_to=date_to
        )
        account_map = await self._account_map(company_id)

        lines = []
        total_debit = total_credit = 0.0
        for b in balances:
            acc = account_map.get(b["account_code"])
            if acc is None:
                continue
            debit = b["debit"]
            credit = b["credit"]
            total_debit += debit
            total_credit += credit
            lines.append(
                {
                    "account_code": acc.code,
                    "account_name": acc.name,
                    "class_no": acc.class_no,
                    "debit": round(debit, 2),
                    "credit": round(credit, 2),
                    "balance": round(b["balance"], 2),
                }
            )
        return {
            "company_id": company_id,
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
        }

    # ------------------------------------------------------------------ #
    # Balance de vérification (soldes résiduels non nuls)
    # ------------------------------------------------------------------ #
    async def trial_balance(self, company_id: int) -> dict:
        """Soldes non nuls — base de la balance de vérification."""
        balances = await self.ledger.account_balances(company_id)
        account_map = await self._account_map(company_id)
        lines = []
        total_debit = total_credit = 0.0
        for b in balances:
            acc = account_map.get(b["account_code"])
            if acc is None or abs(b["balance"]) < 0.005:
                continue
            balance = b["balance"]
            if balance > 0:
                debit, credit = balance, 0.0
            else:
                debit, credit = 0.0, -balance
            total_debit += debit
            total_credit += credit
            lines.append(
                {
                    "account_code": acc.code,
                    "account_name": acc.name,
                    "debit": round(debit, 2),
                    "credit": round(credit, 2),
                    "balance": round(balance, 2),
                }
            )
        return {
            "company_id": company_id,
            "lines": lines,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "balanced": abs(total_debit - total_credit) < 0.01,
        }

    # ------------------------------------------------------------------ #
    # Grand livre
    # ------------------------------------------------------------------ #
    async def general_ledger(
        self, company_id: int, account_code: str,
        date_from: date | None = None, date_to: date | None = None,
    ) -> dict:
        """Grand livre d'un compte : mouvements chronologiques + cumul."""
        movements, opening, closing, total_debit, total_credit = (
            await self.ledger.account_movements(
                company_id, account_code, date_from=date_from, date_to=date_to
            )
        )
        account = await self.accounts.get_account(company_id, account_code)
        account_name = account.name if account else account_code
        return {
            "account_code": account_code,
            "account_name": account_name,
            "date_from": date_from,
            "date_to": date_to,
            "opening_balance": round(opening, 2),
            "closing_balance": round(closing, 2),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "movements": movements,
        }

    # ------------------------------------------------------------------ #
    # Journal général
    # ------------------------------------------------------------------ #
    async def journal_report(
        self, company_id: int, journal_code: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ) -> dict:
        """Journal général : écritures publiées d'une période (ou par journal)."""
        entries = await self.ledger.list_entries(
            company_id, limit=1000,
            date_from=date_from, date_to=date_to, journal_code=journal_code,
        )
        lines = []
        total_debit = total_credit = 0.0
        for e in entries:
            for l in e.lines:
                total_debit += float(l.debit)
                total_credit += float(l.credit)
            lines.append(
                {
                    "reference": e.reference,
                    "entry_date": e.entry_date,
                    "journal_code": e.journal_code,
                    "description": e.description,
                    "status": e.status,
                    "lines": [
                        {
                            "account_code": l.account_code,
                            "label": l.label,
                            "debit": float(l.debit),
                            "credit": float(l.credit),
                        }
                        for l in e.lines
                    ],
                }
            )
        return {
            "company_id": company_id,
            "journal_code": journal_code,
            "date_from": date_from,
            "date_to": date_to,
            "entries": lines,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
        }

    # ------------------------------------------------------------------ #
    # Compte de résultat
    # ------------------------------------------------------------------ #
    async def income_statement(
        self, company_id: int, date_from: date | None = None, date_to: date | None = None
    ) -> dict:
        """Compte de résultat SYSCOHADA (produits - charges)."""
        balances = await self.ledger.account_balances(
            company_id, date_from=date_from, date_to=date_to
        )
        account_map = await self._account_map(company_id)

        def _sum(codes: list[str], sign: int) -> float:
            return round(
                sum(
                    sign * b["balance"]
                    for b in balances
                    if any(b["account_code"].startswith(c) for c in codes)
                ),
                2,
            )

        # Produits : solde créditeur (négatif) → signe -1 pour un montant positif.
        income_lines = [
            {"label": label, "codes": codes, "amount": _sum(codes, sign=-1)}
            for label, _, codes in INCOME_SECTIONS
        ]
        # Charges : solde débiteur (positif) → signe +1.
        expense_lines = [
            {"label": label, "codes": codes, "amount": _sum(codes, sign=1)}
            for label, _, codes in EXPENSE_SECTIONS
        ]

        total_income = round(sum(l["amount"] for l in income_lines), 2)
        total_expense = round(sum(l["amount"] for l in expense_lines), 2)
        net_income = round(total_income - total_expense, 2)

        return {
            "company_id": company_id,
            "date_from": date_from,
            "date_to": date_to,
            "income": income_lines,
            "expenses": expense_lines,
            "total_income": total_income,
            "total_expenses": total_expense,
            "net_income": net_income,
        }

    # ------------------------------------------------------------------ #
    # Bilan
    # ------------------------------------------------------------------ #
    async def balance_sheet(
        self, company_id: int, as_of: date | None = None
    ) -> dict:
        """Bilan SYSCOHADA (actif / passif par grandes masses).

        Règles :
        - les comptes « mixtes » (42x, 43x, 44x, 46x, 47x…) sont classés
          selon le signe de leur solde : débiteur → actif, crédititeur → passif ;
        - les sections « déduction » (amortissements 28x/29x, dépréciations
          39x/49x/59x) réduisent l'actif ;
        - le résultat net de l'exercice (classes 6-8 non soldées) est reporté
          au passif (bénéfice) ou à l'actif (perte) tant que la clôture n'a
          pas été comptabilisée au compte 12.
        """
        balances = await self.ledger.account_balances(company_id, date_to=as_of)

        def _amount(b: dict, prefixes: list[str], mode: str) -> float:
            if not any(b["account_code"].startswith(p) for p in prefixes):
                return 0.0
            bal = b["balance"]
            if mode == "debit":        # actif : solde débiteur uniquement
                return max(bal, 0.0)
            if mode == "credit":       # passif : solde créditeur uniquement
                return max(-bal, 0.0)
            return max(-bal, 0.0)      # déduction : solde créditeur déduit

        def _section(
            sections: list[tuple[str, list[str], bool]] | list[tuple[str, list[str]]],
            mode: str,
        ) -> tuple[list[dict], float]:
            out = []
            total = 0.0
            for section in sections:
                label, prefixes = section[0], section[1]
                is_deduction = bool(section[2]) if len(section) > 2 else False
                sec_mode = "deduction" if is_deduction else mode
                amount = round(
                    sum(_amount(b, prefixes, sec_mode) for b in balances), 2
                )
                total += amount
                out.append({"label": label, "amount": amount})
            return out, round(total, 2)

        assets, total_assets = _section(BALANCE_SHEET_ASSETS, mode="debit")
        liabilities, total_liabilities = _section(
            BALANCE_SHEET_LIABILITIES, mode="credit"
        )

        # Résultat net non soldé (classes 6-8) : crédits - débits.
        closing_result = round(
            sum(-b["balance"] for b in balances if b["account_code"][:1] in "678"),
            2,
        )
        has_account_12 = any(
            b["account_code"].startswith("12") and abs(b["balance"]) > 0.005
            for b in balances
        )
        if not has_account_12:
            if closing_result >= 0:
                for line in liabilities:
                    if line["label"] == "Résultat net de l'exercice":
                        line["amount"] = round(line["amount"] + closing_result, 2)
                total_liabilities = round(total_liabilities + closing_result, 2)
            else:
                loss = round(-closing_result, 2)
                assets.append({"label": "Résultat net de l'exercice (perte)", "amount": loss})
                total_assets = round(total_assets + loss, 2)

        return {
            "company_id": company_id,
            "as_of": as_of,
            "assets": assets,
            "liabilities": liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_income": closing_result,
        }

    # ------------------------------------------------------------------ #
    # Balance âgée (aging clients / fournisseurs)
    # ------------------------------------------------------------------ #
    async def aged_balance(
        self,
        company_id: int,
        partner_type: str = "customer",
        as_of: date | None = None,
    ) -> dict:
        """Balance âgée par tiers : créances (clients) ou dettes (fournisseurs).

        Tranches d'échéance : ``not_due`` (non échues), ``d0_30``, ``d31_60``,
        ``d61_90``, ``d90_plus`` jours de retard. L'ancienneté se calcule
        depuis ``due_date`` (à défaut ``invoice_date``).

        Seules les factures non soldées émises au plus tard ``as_of`` sont
        retenues — brouillons, proformas, annulations et avoirs exclus.
        """
        as_of = as_of or date.today()
        excluded = ("draft", "proforma", "cancelled", "credit")

        if partner_type == "supplier":
            residual = SupplierInvoice.amount_total - SupplierInvoice.paid_amount
            stmt = (
                select(SupplierInvoice, Partner.name.label("partner_name"))
                .join(Partner, Partner.id == SupplierInvoice.supplier_id)
                .where(
                    SupplierInvoice.company_id == company_id,
                    ~SupplierInvoice.status.in_(excluded),
                    residual > 0.005,
                    SupplierInvoice.invoice_date <= as_of,
                )
            )
        else:
            partner_type = "customer"
            residual = Invoice.amount_total - Invoice.paid_amount
            stmt = (
                select(Invoice, Partner.name.label("partner_name"))
                .join(Partner, Partner.id == Invoice.partner_id)
                .where(
                    Invoice.company_id == company_id,
                    ~Invoice.status.in_(excluded),
                    residual > 0.005,
                    Invoice.invoice_date <= as_of,
                )
            )

        rows = (await self.session.execute(stmt)).all()

        grouped: dict[int, dict] = {}
        for obj, partner_name in rows:
            due = obj.due_date or obj.invoice_date
            late_days = (as_of - due).days
            if late_days < 0:
                key = "not_due"
            elif late_days <= 30:
                key = "d0_30"
            elif late_days <= 60:
                key = "d31_60"
            elif late_days <= 90:
                key = "d61_90"
            else:
                key = "d90_plus"

            pid = obj.partner_id if partner_type == "customer" else obj.supplier_id
            entry = grouped.get(pid)
            if entry is None:
                entry = grouped[pid] = {
                    "partner_id": pid,
                    "partner_name": partner_name,
                    "invoice_count": 0,
                    "total_due": 0.0,
                    "not_due": 0.0,
                    "d0_30": 0.0,
                    "d31_60": 0.0,
                    "d61_90": 0.0,
                    "d90_plus": 0.0,
                }
            amount = max(float(obj.amount_total) - float(obj.paid_amount), 0.0)
            entry["invoice_count"] += 1
            entry["total_due"] += amount
            entry[key] += amount

        keys = ("total_due", "not_due", "d0_30", "d31_60", "d61_90", "d90_plus")
        lines = sorted(grouped.values(), key=lambda x: -x["total_due"])
        totals = {k: 0.0 for k in keys}
        for line in lines:
            for k in keys:
                line[k] = round(line[k], 2)
                totals[k] += line[k]
        totals = {k: round(v, 2) for k, v in totals.items()}

        return {
            "company_id": company_id,
            "partner_type": partner_type,
            "as_of": as_of,
            "lines": lines,
            "totals": totals,
            "total_due": totals["total_due"],
        }

    # ------------------------------------------------------------------ #
    # Cash-flow (flux de trésorerie)
    # ------------------------------------------------------------------ #
    async def cash_flow(
        self,
        company_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Flux de trésorerie : soldes d'ouverture/fin et mouvements par compte.

        Ne retient que les comptes de trésorerie (51x-53x, 54x, 55x, 57x,
        58x) des écritures ``posted``. ``inflows`` = débits (encaissements),
        ``outflows`` = crédits (décaissements), valeurs positives.
        """
        prefixes = ("51", "52", "53", "54", "55", "57", "58")
        is_treasury = or_(
            *[JournalEntryLine.account_code.like(f"{p}%") for p in prefixes]
        )
        account_map = await self._account_map(company_id)

        async def _movements(
            before: date | None = None,
            start: date | None = None,
            end: date | None = None,
        ) -> dict[str, tuple[float, float]]:
            stmt = (
                select(
                    JournalEntryLine.account_code,
                    func.coalesce(func.sum(JournalEntryLine.debit), 0.0).label("d"),
                    func.coalesce(func.sum(JournalEntryLine.credit), 0.0).label("c"),
                )
                .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
                .where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.status == "posted",
                    is_treasury,
                )
                .group_by(JournalEntryLine.account_code)
            )
            if before is not None:
                stmt = stmt.where(JournalEntry.entry_date < before)
            if start is not None:
                stmt = stmt.where(JournalEntry.entry_date >= start)
            if end is not None:
                stmt = stmt.where(JournalEntry.entry_date <= end)
            rows = (await self.session.execute(stmt)).all()
            return {code: (float(d), float(c)) for code, d, c in rows}

        opening_map = await _movements(before=date_from) if date_from else {}
        period_map = await _movements(start=date_from, end=date_to)

        by_account: list[dict] = []
        opening_balance = inflows = outflows = 0.0
        for code in sorted(set(opening_map) | set(period_map)):
            od, oc = opening_map.get(code, (0.0, 0.0))
            d, c = period_map.get(code, (0.0, 0.0))
            open_bal = od - oc
            close_bal = open_bal + d - c
            account = account_map.get(code)
            by_account.append(
                {
                    "account_code": code,
                    "account_name": account.name if account else code,
                    "opening_balance": round(open_bal, 2),
                    "inflows": round(d, 2),
                    "outflows": round(c, 2),
                    "net_flow": round(d - c, 2),
                    "closing_balance": round(close_bal, 2),
                }
            )
            opening_balance += open_bal
            inflows += d
            outflows += c

        return {
            "company_id": company_id,
            "date_from": date_from,
            "date_to": date_to,
            "opening_balance": round(opening_balance, 2),
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "net_flow": round(inflows - outflows, 2),
            "closing_balance": round(opening_balance + inflows - outflows, 2),
            "by_account": by_account,
        }


def _section_for(code: str, sections: list[tuple[str, list[str]]]) -> str:
    """Retourne le libellé de section pour un code, sinon ``""``."""
    for label, prefixes in sections:
        for p in prefixes:
            if code.startswith(p):
                return label
    return ""


__all__ = ["FinancialService"]