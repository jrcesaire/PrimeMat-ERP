"""Schémas Pydantic — journal d'audit comptable (Phase 2 PRD)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    """Entrée du journal d'audit (écritures comptables)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: Optional[int] = None
    user_id: Optional[int] = None
    #: ``journal_entry.created`` | ``journal_entry.posted``
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    old_values: Optional[dict[str, Any]] = None
    new_values: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


__all__ = ["AuditLogRead"]
