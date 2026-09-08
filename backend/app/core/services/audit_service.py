"""
Service d'audit — journalise les actions sensibles.

Chaque action importante est enregistrée de manière immuable :
- utilisateur, entreprise, action, entité, ancien/nouveau état, IP, user-agent.
"""
from __future__ import annotations

import logging
import json
from typing import Any

from fastapi import Request

from app.core.models.audit_log import AuditLog
from app.core.database import AsyncSession

logger = logging.getLogger(__name__)


class AuditService:
    """Service d'audit — journalise les actions sensibles."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        *,
        company_id: int | None = None,
        user_id: int | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        """
        Enregistre une entrée d'audit.

        Exemple ::

            await audit.log(
                action="invoice.cancelled",
                entity_type="invoice",
                entity_id=42,
                old_values={"status": "posted"},
                new_values={"status": "cancelled"},
                request=request,
            )
        """
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

        entry = AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(entry)
        await self.session.flush()
        logger.info("Audit: %s on %s:%s", action, entity_type, entity_id)
        return entry

    async def get_audit_trail(
        self,
        entity_type: str,
        entity_id: int,
        *,
        company_id: int | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Récupère l'historique d'audit d'une entité."""
        from sqlalchemy import select
        stmt = select(AuditLog).where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )
        if company_id is not None:
            stmt = stmt.where(AuditLog.company_id == company_id)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
