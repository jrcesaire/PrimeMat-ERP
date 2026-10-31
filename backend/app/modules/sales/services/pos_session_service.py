"""
Service PosSession — ouverture, clôture et gestion des sessions de caisse.

Une session PoS encadre les ventes comptoir sur une journée.
Elle ne peut être ouverte qu'une seule fois par entreprise à un instant T.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.setting_service import SettingService
from app.modules.sales.models.order import SalesOrder
from app.modules.sales.models.pos_fund_movement import PosFundMovement
from app.modules.sales.models.pos_session import PosSession
from app.modules.sales.schemas import (
    PosSessionClose,
    PosSessionCloseReport,
    PosSessionCreate,
    PosSessionRead,
    PosSessionUpdate,
)
from app.shared.enums import PosFundMovementType, PosSessionStatus

logger = logging.getLogger(__name__)

# Clés de settings PoS
SETTING_POS_CLOSING_HOUR = "pos_closing_hour"
SETTING_POS_ACCOUNTING_WRITEUP_HOUR = "pos_accounting_writeup_hour"


class PosSessionService:
    """Gestion des sessions de caisse."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_sessions(
        self, company_id: int, limit: int = 50, skip: int = 0
    ) -> list[PosSession]:
        stmt = (
            select(PosSession)
            .where(PosSession.company_id == company_id)
            .order_by(PosSession.opened_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_sessions(self, company_id: int) -> int:
        """Nombre total de sessions de caisse de l'entreprise (pagination)."""
        from sqlalchemy import func

        return (
            await self.session.execute(
                select(func.count())
                .select_from(PosSession)
                .where(PosSession.company_id == company_id)
            )
        ).scalar_one()

    async def get_session(self, session_id: int) -> PosSession | None:
        return await self.session.get(PosSession, session_id)

    async def get_active_session(self, company_id: int) -> PosSession | None:
        stmt = select(PosSession).where(
            PosSession.company_id == company_id,
            PosSession.status == PosSessionStatus.OPEN.value,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def open_session(
        self, company_id: int, user_id: int, data: PosSessionCreate
    ) -> PosSession:
        active = await self.get_active_session(company_id)
        if active is not None:
            raise ValueError(
                f"Une session est déjà ouverte ({active.reference}). "
                "Clôturez-la avant d'en ouvrir une nouvelle."
            )

        today = datetime.utcnow().strftime("%Y%m%d")
        stmt = select(PosSession).where(
            PosSession.company_id == company_id,
            PosSession.reference.like(f"SESSION-{today}-%"),
        )
        result = await self.session.execute(stmt)
        existing_today = result.scalars().all()
        seq = len(existing_today) + 1
        reference = f"SESSION-{today}-{seq:03d}"

        last_closed = await self._get_last_closed_balance(company_id)
        initial_balance = (
            data.initial_balance
            if data.initial_balance is not None and data.initial_balance > 0
            else last_closed
        )

        settings = SettingService(self.session)
        closing_hour = int(await settings.get(SETTING_POS_CLOSING_HOUR, 0) or 0)
        accounting_write_up_hour = int(
            await settings.get(SETTING_POS_ACCOUNTING_WRITEUP_HOUR, 0) or 0
        )

        session_ = PosSession(
            reference=reference,
            status=PosSessionStatus.OPEN.value,
            closing_hour=closing_hour,
            accounting_write_up_hour=accounting_write_up_hour,
            initial_balance=initial_balance,
            opened_by_id=user_id,
            company_id=company_id,
            notes=data.notes,
        )
        self.session.add(session_)
        await self.session.commit()
        await self.session.refresh(session_)
        logger.info(
            "Session PoS %s ouverte (solde initial %.2f FCFA, heure fermeture %dh)",
            session_.reference,
            initial_balance,
            closing_hour,
        )
        return session_

    async def close_session(
        self, session_id: int, user_id: int, data: PosSessionClose
    ) -> PosSession:
        session_ = await self.get_session(session_id)
        if session_ is None:
            raise ValueError("Session de caisse introuvable.")
        if session_.status != PosSessionStatus.OPEN.value:
            raise ValueError(
                f"Seule une session ouverte peut être clôturée "
                f"(statut actuel : {session_.status})."
            )

        session_.status = PosSessionStatus.CLOSED.value
        session_.closed_at = datetime.utcnow()
        session_.closed_by_id = user_id
        session_.closing_balance = data.closing_balance
        if data.notes is not None:
            session_.notes = data.notes

        await self.session.commit()
        await self.session.refresh(session_)
        logger.info(
            "Session PoS %s fermée (solde final %.2f FCFA)",
            session_.reference,
            data.closing_balance,
        )
        return session_

    async def update_session(
        self, session_id: int, data: PosSessionUpdate
    ) -> PosSession | None:
        session_ = await self.get_session(session_id)
        if session_ is None:
            return None
        if session_.status != PosSessionStatus.OPEN.value:
            raise ValueError("Seule une session ouverte peut être modifiée.")
        if data.notes is not None:
            session_.notes = data.notes
        await self.session.commit()
        await self.session.refresh(session_)
        return session_

    # ------------------------------------------------------------------ #
    # Clôture automatique (cron)
    # ------------------------------------------------------------------ #
    async def auto_close_sessions(self) -> list[str]:
        now = datetime.utcnow()

        stmt = select(PosSession).where(PosSession.status == PosSessionStatus.OPEN.value)
        result = await self.session.execute(stmt)
        open_sessions = result.scalars().all()

        closed_refs: list[str] = []
        for session_ in open_sessions:
            if session_.closing_hour is None or session_.closing_hour < 0:
                continue

            opened_at = session_.opened_at or now
            # Heure de clôture visée = première occurrence de ``closing_hour``
            # postérieure à l'ouverture de la session.
            #   - closing_hour = 20, ouverte à 09h00 → clôture le jour même 20h00
            #   - closing_hour = 0 (minuit), ouverte à 09h00 → clôture à minuit
            #     (fin de journée), et NON à l'heure suivante.
            target = opened_at.replace(
                hour=session_.closing_hour, minute=0, second=0, microsecond=0
            )
            if target <= opened_at:
                target += timedelta(days=1)
            if now < target:
                continue

            # Aucun comptage manuel n'a eu lieu : on retient le solde
            # théorique (fonds de caisse initial + ventes + mouvements de
            # fonds). Écrire ``initial_balance`` seul faussait le rapport de
            # clôture (écart égal à l'intégralité des ventes du jour).
            session_.status = PosSessionStatus.CLOSED.value
            session_.closed_at = now
            session_.closing_balance = await self._expected_balance(session_)
            closed_refs.append(session_.reference)
            logger.info(
                "Clôture auto session %s (heure %dh atteinte, solde %.2f)",
                session_.reference,
                session_.closing_hour,
                session_.closing_balance,
            )

        if closed_refs:
            await self.session.commit()
        return closed_refs

    # ------------------------------------------------------------------ #
    # Rapport de clôture
    # ------------------------------------------------------------------ #
    async def get_close_report(self, session_id: int) -> PosSessionCloseReport | None:
        """Génère l'état récapitulatif de clôture d'une session.

        Agrège les ventes rattachées à la session et calcule le solde
        théorique (initial + ventes) ainsi que l'écart avec le solde
        constaté à la clôture.
        """
        session_ = await self.get_session(session_id)
        if session_ is None:
            return None

        stmt = select(SalesOrder).where(
            SalesOrder.pos_session_id == session_id,
        )
        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        sales_lines = []
        sales_total = 0.0
        for order in orders:
            sales_lines.append(
                PosSessionSaleLine(
                    order_reference=order.reference,
                    created_at=order.created_at.isoformat()
                    if order.created_at
                    else "",
                    partner_name=order.partner.name
                    if order.partner
                    else None,
                    amount_total=float(order.amount_total or 0),
                )
            )
            sales_total += float(order.amount_total or 0)

        initial_balance = float(session_.initial_balance or 0)
        # Les dépôts/retraits manuels font partie du solde disponible : les
        # ignorer afficherait un « écart de caisse » égal au net des
        # mouvements alors qu'aucun écart réel n'existe.
        fund_movements_total = await self._fund_movements_total(session_id)
        theoretical_balance = initial_balance + sales_total + fund_movements_total
        closing_balance = float(session_.closing_balance) if session_.closing_balance is not None else None
        variance = (
            (closing_balance - theoretical_balance) if closing_balance is not None else None
        )

        return PosSessionCloseReport(
            session_id=session_.id,
            reference=session_.reference,
            status=session_.status,
            opened_at=session_.opened_at.isoformat() if session_.opened_at else "",
            closed_at=session_.closed_at.isoformat() if session_.closed_at else None,
            initial_balance=initial_balance,
            closing_balance=closing_balance,
            sales_count=len(sales_lines),
            sales_total=sales_total,
            fund_movements_total=fund_movements_total,
            theoretical_balance=theoretical_balance,
            variance=variance,
            sales=sales_lines,
        )

    # ------------------------------------------------------------------ #
    # Internes
    # ------------------------------------------------------------------ #
    async def _get_last_closed_balance(self, company_id: int) -> float:
        stmt = (
            select(PosSession)
            .where(
                PosSession.company_id == company_id,
                PosSession.status == PosSessionStatus.CLOSED.value,
                PosSession.closing_balance.is_not(None),
            )
            .order_by(PosSession.closed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        last = result.scalars().first()
        return float(last.closing_balance) if last and last.closing_balance else 0.0

    async def _sales_total(self, session_id: int) -> float:
        """Somme des ventes rattachées à une session.

        Sert à la clôture automatique : aucun comptage manuel n'ayant eu
        lieu, le solde retenu est le solde théorique
        (fonds de caisse initial + ventes de la session).
        """
        from sqlalchemy import func

        stmt = select(func.coalesce(func.sum(SalesOrder.amount_total), 0)).where(
            SalesOrder.pos_session_id == session_id
        )
        result = await self.session.execute(stmt)
        return float(result.scalar_one() or 0)

    async def _fund_movements_total(self, session_id: int) -> float:
        """Net des mouvements de fonds manuels d'une session (dépôts − retraits)."""
        stmt = select(PosFundMovement).where(PosFundMovement.session_id == session_id)
        result = await self.session.execute(stmt)
        total = 0.0
        for movement in result.scalars().all():
            amount = float(movement.amount or 0)
            if movement.movement_type == PosFundMovementType.WITHDRAWAL.value:
                total -= amount
            else:
                total += amount
        return total

    async def _expected_balance(self, session_: PosSession) -> float:
        """Solde attendu en caisse d'une session.

        Fonds de caisse initial + ventes rattachées + net des mouvements de
        fonds manuels (dépôts − retraits). C'est la référence à laquelle le
        solde constaté est comparé dans le rapport de clôture.
        """
        return (
            float(session_.initial_balance or 0)
            + await self._sales_total(session_.id)
            + await self._fund_movements_total(session_.id)
        )