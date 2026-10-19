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
    # Seuil de validation hiérarchique des demandes d'achat
    "purchase_approval_threshold": {
        "value": "500000",
        "type": "integer",
        "is_public": True,
        "description": "Seuil de validation hiérarchique des demandes d'achat (FCFA)",
    },
    # Conditions generales de vente (derniere page des devis et factures)
    "cgv_content": {
        "value": "",
        "type": "string",
        "is_public": True,
        "description": "Conditions Générales de Vente (page finale des devis et factures)",
    },
    # Opacité du filigrane des documents A4 (pourcentage 1-100)
    "watermark_opacity": {
        "value": "10",
        "type": "integer",
        "is_public": True,
        "description": "Opacité du filigrane des documents A4, en pourcentage (1–100)",
    },
    # URL du site du POS, affichée dans le QR code des tickets de caisse
    "pos_ticket_url": {
        "value": "",
        "type": "string",
        "is_public": True,
        "description": "URL publique affichée dans le QR code des tickets de caisse (POS)",
    },
    # Nomenclature des documents (préfixe / série / suffixe par type)
    "doc_nomenclature": {
        "value": {
            "quote": {"prefix": "DEV", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
            "order": {"prefix": "COM", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
            "invoice": {"prefix": "FAC", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
            "delivery": {"prefix": "BL", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
            "payment": {"prefix": "REC", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
            "expense": {"prefix": "DEP", "padding": 6, "reset": "never", "suffix_type": "none", "suffix_custom": ""},
            "product": {"prefix": "PRD", "padding": 6, "reset": "never", "suffix_type": "none", "suffix_custom": ""},
            "journal": {"prefix": "ECR", "padding": 6, "reset": "year", "suffix_type": "none", "suffix_custom": ""},
        },
        "type": "json",
        "is_public": True,
        "description": "Nomenclature des documents : préfixe, longueur de série, période de réinitialisation et suffixe par type",
    },
}

_CACHE: dict[tuple[int | None, str], Any] = {}


class SettingService:
    """Service pour lire/écrire les paramètres de configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: Any = None) -> Any:
        """Récupère la valeur d'un paramètre (cache + entreprise + global).

        Le cache est indexé par ``(company_id, key)`` pour éviter qu'une
        entreprise lise le paramètre (déjà chargé) d'une autre.
        """
        # 1) Contexte tenant courant (défini par l'authentification)
        from app.core.tenant import get_current_company

        cid = get_current_company()

        # 2) Cache par (entreprise, clé)
        cache_key = (cid, key)
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        # 3) Lecture DB — filtrée par le listener multi-tenant
        result = await self.session.execute(
            select(Setting).where(Setting.key == key).order_by(Setting.company_id)
        )
        setting: Setting | None = result.scalars().first()

        if setting is None:
            if key in DEFAULT_SETTINGS:
                val = DEFAULT_SETTINGS[key]["value"]
                _CACHE[cache_key] = val
                return val
            return default

        val = self._deserialize(setting.value, setting.type)
        _CACHE[cache_key] = val
        return val

    async def update(
        self, key: str, value: Any, type: str | None = None,
        is_public: bool | None = None, description: str | None = None,
company_id: int | None = None,
    ) -> Setting | None:
        """Met a jour un parametre existant (None si introuvable)."""
        result = await self.session.execute(
            select(Setting).where(
                Setting.key == key, Setting.company_id == company_id,
            )
        )
        setting: Setting | None = result.scalars().first()
        if setting is None:
            return None
        setting.value = self._serialize(value, type or setting.type)
        if type:
            setting.type = type
        if is_public is not None:
            setting.is_public = is_public
        if description:
            setting.description = description
        await self.session.commit()
        await self.session.refresh(setting)
        # Invalide les entrées de cache de cette clé (toutes entreprises)
        for ck in [k for k in _CACHE if k[1] == key]:
            _CACHE.pop(ck, None)
        return setting

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
        # Invalide les entrées de cache de cette clé (toutes entreprises)
        for ck in [k for k in _CACHE if k[1] == key]:
            _CACHE.pop(ck, None)
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
