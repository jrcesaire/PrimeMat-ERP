"""
API Comptabilité — journal d'audit des écritures comptables.

Trace les créations et publications d'écritures (``journal_entry.created``,
``journal_entry.posted``) avec l'auteur, l'horodatage et les valeurs de
l'écriture. Lecture seule : le journal d'audit est immuable.
"""
from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.audit_log import AuditLog
from app.core.models.user import User
from app.modules.accounting.schemas.audit import AuditLogRead

router = APIRouter()


def _bound(value: str, *, end_of_day: bool) -> datetime:
    """Convertit une date ISO en borne temporelle (400 si invalide)."""
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date invalide : {value}")
    return datetime.combine(parsed, time.max if end_of_day else time.min)


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    entity_type: str = Query(
        default="journal_entry", description="Type d'entité tracée"
    ),
    action: str | None = Query(
        default=None, description="ex. journal_entry.posted"
    ),
    user_id: int | None = Query(default=None, description="Auteur de l'action"),
    entity_id: int | None = Query(
        default=None, description="Identifiant de l'écriture concernée"
    ),
    date_from: str | None = Query(default=None, description="Début (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Fin (YYYY-MM-DD)"),
    limit: int = Query(default=200, ge=1, le=1000),
    _: User = Depends(require_permission("audit_log", "view")),
):
    """Journal d'audit comptable, du plus récent au plus ancien."""
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.company_id == company_id,
            AuditLog.entity_type == entity_type,
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= _bound(date_from, end_of_day=False))
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= _bound(date_to, end_of_day=True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


__all__ = ["router"]
