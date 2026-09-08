"""Service Finance (mini) — dépenses."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.sequence_service import SequenceService
from app.modules.finance.models.expense import Expense
from app.modules.finance.schemas import ExpenseCreate

logger = logging.getLogger(__name__)


class ExpenseService:
    """Service des dépenses."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def create_expense(self, data: ExpenseCreate) -> Expense:
        from app.core.tenant import get_current_company

        company_id = get_current_company()
        if company_id is None:
            raise ValueError("Entreprise courante introuvable")
        if data.supplier_id:
            from app.modules.crm.models.partner import Partner

            supplier = await self.session.get(Partner, data.supplier_id)
            company_id = supplier.company_id if supplier else company_id

        reference = await self.sequences.next_value("expense", "DEP")

        expense = Expense(
            reference=reference,
            label=data.label,
            category=data.category,
            amount=float(data.amount),
            expense_date=data.expense_date or date.today(),
            payment_method=data.payment_method,
            supplier_id=data.supplier_id,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)

        # Comptabilisation automatique (idempotente) — défensive
        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_expense(expense)
            await self.session.commit()
            await self.session.refresh(expense)
        except Exception:  # pragma: no cover — défensif
            logger.exception(
                "Comptabilisation automatique impossible pour la dépense %s",
                expense.reference,
            )
            await self.session.rollback()

        return expense

    async def list_expenses(self, skip: int = 0, limit: int = 100) -> list[Expense]:
        result = await self.session.execute(
            select(Expense).order_by(Expense.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())