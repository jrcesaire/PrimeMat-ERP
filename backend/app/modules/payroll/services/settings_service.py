"""Paramètres du module Paie — taux, barèmes et plafonds configurables.

Stockés dans un réglage JSON unique (``payroll_settings``), par entreprise, ils
alimentent le moteur de calcul (SMIG, taux CNPS, plafond, RICF, exonération
transport) et le barème de l'ITS appliqué à la structure de paie. Les modifier
ne demande aucun code : ce sont des **données**.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.setting import Setting

logger = logging.getLogger(__name__)

PAYROLL_SETTINGS_KEY = "payroll_settings"

#: Barème ITS 2026 (Côte d'Ivoire) — impôt progressif par tranches mensuelles.
ITS_2026_BRACKETS: list[dict] = [
    {"up_to": 75000, "rate": 0},
    {"up_to": 240000, "rate": 16},
    {"up_to": 800000, "rate": 21},
    {"up_to": 2400000, "rate": 24},
    {"up_to": 8000000, "rate": 28},
    {"up_to": None, "rate": 32},
]

#: Valeurs par défaut (SMIG 2026, CNPS, RICF, exonération transport).
DEFAULT_PAYROLL_SETTINGS: dict[str, Any] = {
    "currency": "XOF",
    "smig": 75000.0,
    "cnps_salary_rate": 6.3,
    "cnps_employer_rate": 15.45,
    "cnps_ceiling_multiple": 45,
    "ricf_per_half_part": 5500.0,
    "transport_exempt": 30000.0,
    "its_brackets": ITS_2026_BRACKETS,
}


class PayrollSettingsService:
    """Lecture / écriture des paramètres de paie d'une entreprise."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, company_id: int | None = None) -> dict[str, Any]:
        """Paramètres effectifs = défauts + surcharges enregistrées."""
        result = await self.session.execute(
            select(Setting)
            .where(Setting.key == PAYROLL_SETTINGS_KEY)
            .execution_options(include_all_tenants=True)
        )
        rows = result.scalars().all()
        stored: dict[str, Any] = {}
        for row in rows:
            if row.company_id == company_id:
                stored = self._decode(row.value)
                break
        if not stored:
            for row in rows:
                if row.company_id is None:
                    stored = self._decode(row.value)
                    break
        merged = dict(DEFAULT_PAYROLL_SETTINGS)
        merged.update({k: v for k, v in (stored or {}).items() if v is not None})
        return merged

    async def update(
        self, values: dict[str, Any], company_id: int | None = None
    ) -> dict[str, Any]:
        """Met à jour les paramètres (fusion partielle)."""
        from app.core.services.setting_service import SettingService

        current = await self.get(company_id)
        for key, value in values.items():
            if value is not None:
                current[key] = value
        await SettingService(self.session).set(
            PAYROLL_SETTINGS_KEY, current, "json", True,
            "Paramètres de paie : SMIG, taux CNPS, plafond, RICF, barème ITS",
            company_id,
        )
        return current

    @staticmethod
    def context_params(settings: dict[str, Any]) -> dict[str, float]:
        """Variables numériques injectées dans le moteur de calcul."""
        smig = float(settings.get("smig") or 0)
        ceiling_multiple = float(settings.get("cnps_ceiling_multiple") or 0)
        return {
            "SMIG": smig,
            "CNPS_SAL_RATE": float(settings.get("cnps_salary_rate") or 0),
            "CNPS_PAT_RATE": float(settings.get("cnps_employer_rate") or 0),
            "CNPS_CEILING": smig * ceiling_multiple,
            "RICF_HALF": float(settings.get("ricf_per_half_part") or 0),
            "TRANSPORT_EXEMPT": float(settings.get("transport_exempt") or 0),
        }

    @staticmethod
    def _decode(value: str) -> dict[str, Any]:
        try:
            data = json.loads(value or "{}")
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}
