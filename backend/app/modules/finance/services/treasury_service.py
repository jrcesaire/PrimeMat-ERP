"""
Service Tresorerie — comptes, releves et rapprochement bancaire.

Phase 2 du PRD : rapprochement des lignes de releve avec les ecritures
publiees sur le compte comptable de tresorerie rattache (511, 512, 531...).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.accounting.models.journal_entry import JournalEntry, JournalEntryLine
from app.modules.finance.models.treasury import (
    BankStatement,
    BankStatementLine,
    TreasuryAccount,
)
from app.modules.finance.schemas.treasury import (
    BankStatementCreate,
    BankStatementLineCreate,
    ReconciliationReport,
    ReconcileResult,
    TreasuryAccountCreate,
    TreasuryAccountUpdate,
    UnreconciledEntryLine,
)

logger = logging.getLogger(__name__)

#: Toleree de comparaison des montants (FCFA).
_AMOUNT_TOLERANCE = Decimal("0.01")
#: Fenetre de date pour le rapprochement automatique (jours +|-).
_AUTO_MATCH_DAYS = 5


class TreasuryService:
    """Service metier tresorerie et rapprochement bancaire."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Comptes de tresorerie
    # ------------------------------------------------------------------ #
    async def list_accounts(
        self, company_id: int, active_only: bool = True
    ) -> list[TreasuryAccount]:
        stmt = select(TreasuryAccount).where(TreasuryAccount.company_id == company_id)
        if active_only:
            stmt = stmt.where(TreasuryAccount.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(TreasuryAccount.code))
        return list(result.scalars().all())

    async def get_account(self, company_id: int, account_id: int) -> TreasuryAccount:
        result = await self.session.execute(
            select(TreasuryAccount).where(
                TreasuryAccount.company_id == company_id,
                TreasuryAccount.id == account_id,
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise ValueError(f"Compte de tresorerie {account_id} introuvable.")
        return account

    async def create_account(
        self, company_id: int, data: TreasuryAccountCreate
    ) -> TreasuryAccount:
        existing = await self.session.execute(
            select(TreasuryAccount).where(
                TreasuryAccount.company_id == company_id,
                TreasuryAccount.code == data.code,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Le code tresorerie {data.code} existe deja.")
        account = TreasuryAccount(company_id=company_id, **data.model_dump())
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def update_account(
        self, company_id: int, account_id: int, data: TreasuryAccountUpdate
    ) -> TreasuryAccount:
        account = await self.get_account(company_id, account_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(account, key, value)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def delete_account(self, company_id: int, account_id: int) -> None:
        account = await self.get_account(company_id, account_id)
        await self.session.delete(account)
        await self.session.commit()

    # ------------------------------------------------------------------ #
    # Releves bancaires
    # ------------------------------------------------------------------ #
    async def list_statements(
        self, company_id: int, account_id: int
    ) -> list[BankStatement]:
        await self.get_account(company_id, account_id)
        result = await self.session.execute(
            select(BankStatement)
            .where(
                BankStatement.company_id == company_id,
                BankStatement.account_id == account_id,
            )
            .order_by(BankStatement.statement_date.desc())
        )
        return list(result.scalars().all())

    async def get_statement(
        self, company_id: int, statement_id: int
    ) -> BankStatement:
        result = await self.session.execute(
            select(BankStatement)
            .options(selectinload(BankStatement.lines))
            .where(
                BankStatement.company_id == company_id,
                BankStatement.id == statement_id,
            )
        )
        statement = result.scalar_one_or_none()
        if statement is None:
            raise ValueError(f"Releve {statement_id} introuvable.")
        return statement

    async def create_statement(
        self, company_id: int, account_id: int, data: BankStatementCreate
    ) -> BankStatement:
        await self.get_account(company_id, account_id)
        statement = BankStatement(
            company_id=company_id,
            account_id=account_id,
            **data.model_dump(),
        )
        self.session.add(statement)
        await self.session.commit()
        await self.session.refresh(statement)
        return statement

    async def add_line(
        self, company_id: int, statement_id: int, data: BankStatementLineCreate
    ) -> BankStatementLine:
        statement = await self.get_statement(company_id, statement_id)
        if statement.status != "open":
            raise ValueError("Le releve est cloture : ajoutez un nouveau releve.")
        line = BankStatementLine(
            company_id=company_id,
            statement_id=statement_id,
            **data.model_dump(),
        )
        self.session.add(line)
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def delete_line(self, company_id: int, line_id: int) -> None:
        line = await self._get_line(company_id, line_id)
        if line.entry_line_id is not None:
            raise ValueError("Ligne deja rapprochee : retirez d'abord le rapprochement.")
        statement = await self.get_statement(company_id, line.statement_id)
        if statement.status != "open":
            raise ValueError("Le releve est cloture : ligne verrouillee.")
        await self.session.delete(line)
        await self.session.commit()

    async def close_statement(self, company_id: int, statement_id: int) -> BankStatement:
        statement = await self.get_statement(company_id, statement_id)
        if statement.status == "closed":
            raise ValueError("Le releve est deja cloture.")
        statement.status = "closed"
        await self.session.commit()
        await self.session.refresh(statement)
        return statement

    async def _get_line(self, company_id: int, line_id: int) -> BankStatementLine:
        result = await self.session.execute(
            select(BankStatementLine).where(
                BankStatementLine.company_id == company_id,
                BankStatementLine.id == line_id,
            )
        )
        line = result.scalar_one_or_none()
        if line is None:
            raise ValueError(f"Ligne de releve {line_id} introuvable.")
        return line

    # ------------------------------------------------------------------ #
    # Rapprochement
    # ------------------------------------------------------------------ #
    async def reconcile(
        self,
        company_id: int,
        line_id: int,
        entry_line_id: int,
        user_id: int | None = None,
    ) -> BankStatementLine:
        """Rapproche manuellement une ligne de releve et une ecriture."""
        line = await self._get_line(company_id, line_id)
        if line.entry_line_id is not None:
            raise ValueError("Cette ligne est deja rapprochee.")

        statement = await self.get_statement(company_id, line.statement_id)
        if statement.status != "open":
            raise ValueError("Le releve est cloture : rapprochement impossible.")

        account = await self.get_account(company_id, statement.account_id)
        entry_line = await self._get_posted_entry_line(
            company_id, entry_line_id, account.account_code
        )
        if entry_line is None:
            raise ValueError(
                f"Ligne d'ecriture {entry_line_id} introuvable ou non rattachable "
                f"au compte {account.account_code}."
            )

        amount_line = Decimal(str(line.amount))
        amount_entry = Decimal(str(entry_line.debit or 0)) - Decimal(
            str(entry_line.credit or 0)
        )
        if abs(amount_line - amount_entry) > _AMOUNT_TOLERANCE:
            raise ValueError(
                f"Montants incoherents : releve {amount_line} vs ecriture {amount_entry}."
            )

        line.entry_line_id = entry_line.id
        line.reconciled_at = datetime.utcnow()
        line.reconciled_by = user_id
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def unreconcile(self, company_id: int, line_id: int) -> BankStatementLine:
        """Retire le rapprochement d'une ligne de releve."""
        line = await self._get_line(company_id, line_id)
        if line.entry_line_id is None:
            raise ValueError("Cette ligne n'est pas rapprochee.")
        statement = await self.get_statement(company_id, line.statement_id)
        if statement.status != "open":
            raise ValueError("Le releve est cloture : operation impossible.")
        line.entry_line_id = None
        line.reconciled_at = None
        line.reconciled_by = None
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def auto_reconcile(
        self, company_id: int, statement_id: int
    ) -> ReconcileResult:
        """
        Rapprochement automatique : montant identique + date +|- fenetre.

        Chaque ligne de releve non rapprochee est appariee avec la premiere
        ligne d'ecriture publiee disponible respectant les criteres.
        """
        statement = await self.get_statement(company_id, statement_id)
        if statement.status != "open":
            raise ValueError("Le releve est cloture : rapprochement impossible.")
        account = await self.get_account(company_id, statement.account_id)

        lines = [l for l in statement.lines if l.entry_line_id is None]
        candidates = await self._unreconciled_entry_lines(
            company_id, account.account_code
        )

        matched = 0
        used: set[int] = set()
        for line in lines:
            amount_line = Decimal(str(line.amount))
            for candidate in list(candidates):
                if candidate["id"] in used:
                    continue
                if abs(amount_line - candidate["amount"]) > _AMOUNT_TOLERANCE:
                    continue
                delta = abs(line.line_date - candidate["entry_date"])
                if delta > timedelta(days=_AUTO_MATCH_DAYS):
                    continue
                line.entry_line_id = candidate["id"]
                line.reconciled_at = datetime.utcnow()
                used.add(candidate["id"])
                matched += 1
                break

        await self.session.commit()
        unmatched = len(lines) - matched
        return ReconcileResult(
            matched=matched,
            unmatched=unmatched,
            message=(
                f"{matched} ligne(s) rapprochee(s) automatiquement, "
                f"{unmatched} restante(s)."
            ),
        )

    async def reconciliation_report(
        self, company_id: int, account_id: int
    ) -> ReconciliationReport:
        """Etat de rapprochement : soldes comptable / releve + lignes en attente."""
        account = await self.get_account(company_id, account_id)

        # Solde comptable (ecritures publiees sur le compte rattache)
        result = await self.session.execute(
            select(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
                JournalEntryLine.account_code == account.account_code,
            )
        )
        entry_lines = list(result.scalars().all())
        accounting_balance = sum(
            (Decimal(str(l.debit or 0)) - Decimal(str(l.credit or 0)) for l in entry_lines),
            Decimal("0"),
        )
        rapproched_ids = {
            l.entry_line_id
            for l in await self._all_statement_lines(company_id, account_id)
            if l.entry_line_id is not None
        }
        unreconciled_entry = [
            UnreconciledEntryLine(
                entry_line_id=l.id,
                entry_id=l.entry_id,
                reference=(await self._entry_reference(l.entry_id)) or "",
                entry_date=(await self._entry_date(l.entry_id)),
                label=l.label,
                amount=float(Decimal(str(l.debit or 0)) - Decimal(str(l.credit or 0))),
            )
            for l in entry_lines
            if l.id not in rapproched_ids
        ]

        # Releves : solde de cloture du dernier releve + lignes non rapprochees
        statements = await self.list_statements(company_id, account_id)
        last_closing = (
            Decimal(str(statements[0].closing_balance)) if statements else Decimal("0")
        )
        all_lines = await self._all_statement_lines(company_id, account_id)
        unreconciled_lines = [l for l in all_lines if l.entry_line_id is None]
        reconciled_amount = sum(
            (Decimal(str(l.amount)) for l in all_lines if l.entry_line_id is not None),
            Decimal("0"),
        )

        return ReconciliationReport(
            account_id=account.id,
            account_code=account.account_code,
            accounting_balance=float(accounting_balance),
            statement_balance=float(last_closing),
            reconciled_amount=float(reconciled_amount),
            unreconciled_lines=unreconciled_lines,
            unreconciled_entry_lines=unreconciled_entry,
        )

    # ------------------------------------------------------------------ #
    # Methodes privees
    # ------------------------------------------------------------------ #
    async def _get_posted_entry_line(
        self, company_id: int, entry_line_id: int, account_code: str
    ) -> Optional[JournalEntryLine]:
        result = await self.session.execute(
            select(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .where(
                JournalEntryLine.id == entry_line_id,
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
                JournalEntryLine.account_code == account_code,
            )
        )
        return result.scalar_one_or_none()

    async def _unreconciled_entry_lines(
        self, company_id: int, account_code: str
    ) -> list[dict]:
        result = await self.session.execute(
            select(JournalEntryLine, JournalEntry)
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
                JournalEntryLine.account_code == account_code,
            )
        )
        rows = result.all()
        already = {
            r[0]
            for r in (
                await self.session.execute(
                    select(BankStatementLine.entry_line_id).where(
                        BankStatementLine.company_id == company_id,
                        BankStatementLine.entry_line_id.is_not(None),
                    )
                )
            ).all()
        }
        out: list[dict] = []
        for line, entry in rows:
            if line.id in already:
                continue
            out.append(
                {
                    "id": line.id,
                    "entry_id": line.entry_id,
                    "entry_date": entry.entry_date,
                    "amount": Decimal(str(line.debit or 0))
                    - Decimal(str(line.credit or 0)),
                }
            )
        return out

    async def _all_statement_lines(
        self, company_id: int, account_id: int
    ) -> list[BankStatementLine]:
        result = await self.session.execute(
            select(BankStatementLine)
            .join(BankStatement, BankStatementLine.statement_id == BankStatement.id)
            .where(
                BankStatementLine.company_id == company_id,
                BankStatement.account_id == account_id,
            )
        )
        return list(result.scalars().all())

    async def _entry_reference(self, entry_id: int) -> Optional[str]:
        result = await self.session.execute(
            select(JournalEntry.reference).where(JournalEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def _entry_date(self, entry_id: int):
        result = await self.session.execute(
            select(JournalEntry.entry_date).where(JournalEntry.id == entry_id)
        )
        return result.scalar_one_or_none()
