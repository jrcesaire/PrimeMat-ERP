"""
Service PosFundMovement — journal des mouvements de fonds manuels en caisse.

Permet d'enregistrer et de lister les dépôts et retraits de fonds
non liés à une vente, rattachés à une session de caisse.
Conforme au PRD §4.1.2 §5.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.models.pos_fund_movement import PosFundMovement
from app.modules.sales.models.pos_session import PosSession
from app.modules.sales.schemas import PosFundMovementCreate
from app.shared.enums import PosFundMovementType, PosSessionStatus

logger = logging.getLogger(__name__)


class PosFundMovementService:
    """Gestion des mouvements de fonds manuels en caisse."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_fund_movements(
        self, company_id: int, session_id: int | None = None, limit: int = 100, skip: int = 0
    ) -> list[PosFundMovement]:
        stmt = select(PosFundMovement).where(
            PosFundMovement.company_id == company_id,
        )
        if session_id is not None:
            stmt = stmt.where(PosFundMovement.session_id == session_id)
        stmt = (
            stmt.order_by(PosFundMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_fund_movements(
        self, company_id: int, session_id: int | None = None
    ) -> int:
        """Nombre total de mouvements de fonds (pagination)."""
        from sqlalchemy import func

        cond = PosFundMovement.company_id == company_id
        if session_id is not None:
            cond = cond & (PosFundMovement.session_id == session_id)
        return (
            await self.session.execute(
                select(func.count()).select_from(PosFundMovement).where(cond)
            )
        ).scalar_one()

    async def get_fund_movement(self, movement_id: int) -> PosFundMovement | None:
        return await self.session.get(PosFundMovement, movement_id)

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_fund_movement(
        self, company_id: int, user_id: int, data: PosFundMovementCreate
    ) -> PosFundMovement:
        movement_type = data.movement_type.lower()
        if movement_type not in (PosFundMovementType.DEPOSIT.value, PosFundMovementType.WITHDRAWAL.value):
            raise ValueError(
                f"Type de mouvement invalide : {data.movement_type}. "
                f"Valeurs autorisées : {PosFundMovementType.DEPOSIT.value}, {PosFundMovementType.WITHDRAWAL.value}."
            )
        if data.amount <= 0:
            raise ValueError("Le montant doit être strictement positif.")
        if not data.label or not data.label.strip():
            raise ValueError("Le libellé est obligatoire.")

        # Un mouvement de fonds ne se justifie que sur une session ouverte :
        # une session clôturée (ou en cours de clôture) a un solde figé par son
        # rapport de clôture (PRD §4.1.2 §5).
        pos_session = await self.session.get(PosSession, data.session_id)
        if pos_session is None or pos_session.company_id != company_id:
            raise ValueError(
                "Session de caisse introuvable pour ce mouvement de fonds."
            )
        if pos_session.status != PosSessionStatus.OPEN.value:
            raise ValueError(
                "Impossible d'enregistrer un mouvement de fonds sur une session "
                f"non ouverte (statut : {pos_session.status})."
            )

        movement = PosFundMovement(
            company_id=company_id,
            session_id=data.session_id,
            movement_type=movement_type,
            amount=float(data.amount),
            label=data.label.strip(),
            reference=data.reference,
            notes=data.notes,
            created_by=user_id,
        )
        self.session.add(movement)
        await self.session.commit()
        await self.session.refresh(movement)
        return movement
