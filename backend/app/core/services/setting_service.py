"""
Service de gestion des paramètres (Settings).

Gère la sérialisation, un cache en mémoire, et les paramètres par défaut.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.setting import Setting

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "invoice_prefix": {"value": "FA", "type": "string", "is_public": True},
    "quote_prefix": {"value": "DEV", "type": "string", "is_public": True},
    "order_prefix": {"value": "COM", "type": "string", "is_public": True},
    "delivery_prefix": {"value": "BL", "type": "string", "is_public": True},
    "currency_symbol_position": {"value": "after", "type": "string", "is_public": True},
    "date_format": {"value": "DD/MM/YYYY", "type": "string", "is_public": True},
    "tax_enabled": {"value": "true", "type": "boolean", "is_public": True},
    "discount_enabled": {"value": "true", "type": "boolean", "is_public": True},
    "payment_terms_days": {"value": "30", "type": "integer", "is_public": True},
    # URL du site du POS, affichée dans le QR code des tickets de caisse
    "pos_ticket_url": {
        "value": "",
        "type": "string",
        "is_public": True,
        "description": "URL publique affichée dans le QR code des tickets de caisse (POS)",
    },
}

_CACHE: dict[str, Any] = {}


class SettingService:
    """Service pour lire/écrire les paramètres de configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: Any = None) -> Any:
        """Récupère la valeur d'un paramètre (cache + entreprise + global)."""
        if key in _CACHE:
            return _CACHE[key]

        result = await self.session.execute(
            select(Setting).where(Setting.key == key).order_by(Setting.company_id)
        )
        setting: Setting | None = result.scalars().first()

        if setting is None:
            if key in DEFAULT_SETTINGS:
                val = DEFAULT_SETTINGS[key]["value"]
                _CACHE[key] = val
                return val
            return default

        val = self._deserialize(setting.value, setting.type)
        _CACHE[key] = val
        return val

    async def set(
        self, key: str, value: Any, type: str = "string",
        is_public: bool = False, description: str | None = None,
        company_id: int | None = None,
    ) -> Setting:
        """Crée ou met à jour un paramètre."""
        serialized = self._serialize(value, type)
        result = await self.session.execute(
            select(Setting).where(
                Setting.key == key, Setting.company_id == company_id,
            )
        )
        setting: Setting | None = result.scalars().first()
        if setting is None:
            setting = Setting(
                key=key, value=serialized, type=type,
                is_public=is_public, description=description,
                company_id=company_id,
            )
            self.session.add(setting)
        else:
            setting.value = serialized
            setting.type = type
            setting.is_public = is_public
            if description:
                setting.description = description
        await self.session.commit()
        await self.session.refresh(setting)
        _CACHE.pop(key, None)
        return setting

    async def get_all(
        self, company_id: int | None = None, public_only: bool = False,
    ) -> dict[str, Any]:
        """Retourne tous les paramètres sous forme de dictionnaire."""
        stmt = select(Setting)
        if company_id is not None:
            stmt = stmt.where(
                (Setting.company_id == company_id) |
                (Setting.company_id.is_(None))
            )
        if public_only:
            stmt = stmt.where(Setting.is_public.is_(True))
        result = await self.session.execute(stmt.order_by(Setting.key))
        output: dict[str, Any] = {}
        for s in result.scalars().all():
            output[s.key] = self._deserialize(s.value, s.type)
        return output

    def _serialize(self, value: Any, type: str) -> str:
        if type == "json":
            return json.dumps(value)
        if type == "boolean":
            return "true" if value else "false"
        if type == "integer":
            return str(value)
        return str(value)

    def _deserialize(self, value: str, type: str) -> Any:
        if type == "json":
            return json.loads(value)
        if type == "boolean":
            return value.lower() in ("true", "1", "yes")
        if type == "integer":
            return int(value)
        return value
