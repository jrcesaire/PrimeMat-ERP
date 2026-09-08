"""
Modèle Expense — dépense enregistrable (mini-Finance).

Une dépense peut être liée à un fournisseur (Partner) et catégorisée.
C'est l'action rapide « Enregistrer une dépense » du tableau de bord.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn

from app.core.database import Base, TenantMixin


class Expense(Base, TenantMixin):
    """Dépense simple."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    label: Mapped[str] = MappedColumn(String(200), nullable=False)
    category: Mapped[str] = MappedColumn(String(50), default="general")
    amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    expense_date: Mapped[date | None] = MappedColumn(Date, default=date.today)
    payment_method: Mapped[str] = MappedColumn(String(20), default="cash")

    supplier_id: Mapped[int | None] = MappedColumn(ForeignKey("partners.id"), nullable=True)
    notes: Mapped[str | None] = MappedColumn(String(500))

    def __repr__(self) -> str:
        return f"<Expense {self.reference} {self.amount}>"