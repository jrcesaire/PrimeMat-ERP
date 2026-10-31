"""
API Routes Réglages PoS — paramètres propres au Point de Vente.

    GET  /pos/settings   — lecture des réglages PoS de l'entreprise courante
    PUT  /pos/settings   — mise à jour partielle des réglages PoS

Chemins relatifs : le routeur est monté par le module Ventes sous le
préfixe ``/sales`` → URL finales ``/api/v1/sales/pos/settings``.

Références PRD « Improvements module PoS » :
- §4.1.2.3 : l'heure de clôture automatique des sessions est configurable
  dans les réglages (valeur recopiée sur chaque session ouverte).
- §4.2.2.6 : la tuile « Réglages » du dashboard PoS ne regroupe que les
  paramètres du Point de Vente, pas les réglages généraux de l'ERP.
- §7 : accès réservé aux rôles Administrateur / Gérant — matérialisé par la
  permission ``pos:edit`` en écriture (``pos:view`` en lecture).

Seules des clés réellement consommées par le backend sont exposées : aucune
configuration « morte » n'est proposée dans l'interface.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.services.setting_service import SettingService
from app.modules.sales.services.pos_session_service import (
    SETTING_POS_ACCOUNTING_WRITEUP_HOUR,
    SETTING_POS_CLOSING_HOUR,
)

router = APIRouter()

# Permissions
require_view = require_permission("pos", "view")
require_edit = require_permission("pos", "edit")

# Clé de l'URL du site PoS, imprimée dans le QR code des tickets de caisse.
SETTING_POS_TICKET_URL = "pos_ticket_url"

# Descriptions conservées en base (paramétrage lisible depuis l'admin).
_DESCRIPTIONS = {
    SETTING_POS_CLOSING_HOUR: (
        "Heure de clôture automatique des sessions de caisse (POS), de 0 à 23"
    ),
    SETTING_POS_ACCOUNTING_WRITEUP_HOUR: (
        "Heure-valeur de l'écriture comptable des ventes (POS), de 0 à 23"
    ),
    SETTING_POS_TICKET_URL: (
        "URL publique affichée dans le QR code des tickets de caisse (POS)"
    ),
}


class PosSettingsUpdate(BaseModel):
    """Corps JSON partiel de mise à jour des réglages PoS."""

    closing_hour: int | None = Field(
        default=None,
        ge=0,
        le=23,
        description="Heure de clôture automatique des sessions de caisse (0–23)",
    )
    accounting_write_up_hour: int | None = Field(
        default=None,
        ge=0,
        le=23,
        description="Heure-valeur de l'écriture comptable des ventes (0–23)",
    )
    ticket_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL publique imprimée dans le QR code des tickets de caisse",
    )


async def _read_settings(svc: SettingService) -> dict:
    """Lit les réglages PoS (valeurs par défaut si le paramètre est absent)."""
    closing_hour = await svc.get(SETTING_POS_CLOSING_HOUR, 0)
    writeup_hour = await svc.get(SETTING_POS_ACCOUNTING_WRITEUP_HOUR, 0)
    ticket_url = await svc.get(SETTING_POS_TICKET_URL, "")
    return {
        "closing_hour": int(closing_hour or 0),
        "accounting_write_up_hour": int(writeup_hour or 0),
        "ticket_url": str(ticket_url or ""),
    }


@router.get("/pos/settings")
async def get_pos_settings(
    session: SessionDep,
    _: None = Depends(require_view),
):
    """Réglages du Point de Vente de l'entreprise courante."""
    return await _read_settings(SettingService(session))


@router.put("/pos/settings")
async def update_pos_settings(
    body: PosSettingsUpdate,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    """Met à jour (partiellement) les réglages du Point de Vente."""
    svc = SettingService(session)

    if body.closing_hour is not None:
        await svc.set(
            SETTING_POS_CLOSING_HOUR,
            body.closing_hour,
            "integer",
            True,
            _DESCRIPTIONS[SETTING_POS_CLOSING_HOUR],
        )
    if body.accounting_write_up_hour is not None:
        await svc.set(
            SETTING_POS_ACCOUNTING_WRITEUP_HOUR,
            body.accounting_write_up_hour,
            "integer",
            True,
            _DESCRIPTIONS[SETTING_POS_ACCOUNTING_WRITEUP_HOUR],
        )
    if body.ticket_url is not None:
        await svc.set(
            SETTING_POS_TICKET_URL,
            body.ticket_url,
            "string",
            True,
            _DESCRIPTIONS[SETTING_POS_TICKET_URL],
        )

    return await _read_settings(svc)
