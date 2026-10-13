"""
Service de numérotation — génère les numéros de documents uniques.

Nomenclature pilotée par le paramètre ``doc_nomenclature`` (JSON) :
    {"quote": {"prefix": "DEV", "padding": 6, "reset": "month",
               "suffix_type": "mmaa", "suffix_custom": ""}, ...}

Composition : PREFIX-SERIE-SUFFIXE — ex. ``DEV-000123-2609``
(reset mensuel, suffixe MMYY), ``DEV-000123-2026`` (suffixe AAAA),
``DEV-000123`` (sans suffixe) ou ``DEV-000123-GEA`` (personnalisé).

La table ``sequences`` conserve le compteur et la clé de période :
le compteur est remis à zéro quand la période (mois / trimestre /
semestre / année) change.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.sequence import Sequence

logger = logging.getLogger(__name__)

VALID_RESETS = ("never", "month", "quarter", "semester", "year")


class SequenceService:
    """Génère des numéros de documents uniques."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def next_value(
        self,
        model: str,
        prefix: str | None = None,
        company_id: int = 1,
    ) -> str:
        """Prochaine référence complète — ex. ``DEV-000001-2609``.

        ``prefix`` sert de repli si aucune nomenclature n'est configurée.
        """
        seq = await self._get_or_create(model, company_id, prefix)
        cfg = await self._get_config(model)
        current = self._advance(seq, cfg) + seq.number_increment
        seq.last_number = current
        await self.session.flush()
        return self._compose(cfg, seq, current)

    async def next_number(self, model: str, company_id: int) -> str:
        """Compatibilité — identique à ``next_value`` (config-driven)."""
        seq = await self._get_or_create(model, company_id, None)
        cfg = await self._get_config(model)
        current = self._advance(seq, cfg) + seq.number_increment
        seq.last_number = current
        await self.session.flush()
        return self._compose(cfg, seq, current)

    async def preview(self, model: str, company_id: int = 1) -> str:
        """Aperçu de la prochaine référence SANS consommer le compteur."""
        result = await self.session.execute(
            select(Sequence).where(
                Sequence.model == model,
                Sequence.company_id == company_id,
                Sequence.is_active.is_(True),
            )
        )
        seq: Sequence | None = result.scalars().first()
        cfg = await self._get_config(model)
        reset = str(cfg.get("reset") or "never").lower()
        if reset not in VALID_RESETS:
            reset = "never"
        current = seq.last_number if seq else 0
        key = self._period_key(reset, date.today())
        if key is not None and (
            seq is None or (seq.date_ranges or {}).get("last_period") != key
        ):
            current = 0
        increment = seq.number_increment if seq else 1
        return self._compose(cfg, seq, current + increment)

    # ------------------------------------------------------------------ #
    # Nomenclature (configuration par type de document)
    # ------------------------------------------------------------------ #
    async def _get_config(self, model: str) -> dict:
        """Lit la nomenclature du type de document (paramètre JSON).

        Tolère la valeur renvoyée en dict ou en chaîne JSON (double
        sérialisation possible via l'API des paramètres).
        """
        import json

        from app.core.services.setting_service import SettingService

        raw = await SettingService(self.session).get("doc_nomenclature", None)
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (ValueError, TypeError):
                raw = None
        if isinstance(raw, dict):
            entry = raw.get(model)
            if isinstance(entry, dict):
                return entry
            # Entree absente (ex. type produit ajoute apres coup) :
            # serie 6 chiffres par defaut, prefixe fourni par la Sequence.
            return {"padding": 6, "reset": "never", "suffix_type": "none"}
        return {}

    @staticmethod
    def _resolve_suffix(cfg: dict) -> str:
        """Suffixe courant : MMYY (mmaa), YYYY (aaaa) ou texte personnalisé."""
        stype = str(cfg.get("suffix_type") or "none").lower()
        today = date.today()
        if stype == "mmaa":
            return today.strftime("%m%y")
        if stype == "aaaa":
            return today.strftime("%Y")
        if stype == "custom":
            return str(cfg.get("suffix_custom") or "").strip()
        return ""

    @staticmethod
    def _period_key(reset: str, today: date) -> str | None:
        """Clé de la période courante (None = pas de reset)."""
        if reset == "month":
            return today.strftime("%Y%m")
        if reset == "quarter":
            return f"{today.year}-T{(today.month - 1) // 3 + 1}"
        if reset == "semester":
            return f"{today.year}-S{1 if today.month <= 6 else 2}"
        if reset == "year":
            return today.strftime("%Y")
        return None

    def _compose(self, cfg: dict, seq: Sequence | None, current: int) -> str:
        """Compose la référence : PREFIX-SERIE[-SUFFIXE]."""
        prefix = str(cfg.get("prefix") or "").strip().strip("-")
        if not prefix and seq is not None:
            prefix = (seq.prefix or "").strip().strip("-")
        padding = int(cfg.get("padding") or (seq.number_padding if seq else 6) or 6)
        number_str = str(current).rjust(padding, "0")
        body = f"{prefix}-{number_str}" if prefix else number_str
        suffix = self._resolve_suffix(cfg)
        return f"{body}-{suffix}" if suffix else body

    def _advance(self, seq: Sequence, cfg: dict) -> int:
        """Applique le reset périodique — renvoie le compteur de base."""
        reset = str(cfg.get("reset") or "never").lower()
        if reset not in VALID_RESETS:
            reset = "never"
        seq.reset = reset
        seq.number_padding = int(cfg.get("padding") or seq.number_padding or 6)
        current = seq.last_number
        key = self._period_key(reset, date.today())
        if key is not None:
            ranges = dict(seq.date_ranges or {})
            if ranges.get("last_period") != key:
                ranges["last_period"] = key
                seq.date_ranges = ranges
                current = 0
        return current

    async def _get_or_create(
        self, model: str, company_id: int, prefix: str | None
    ) -> Sequence:
        result = await self.session.execute(
            select(Sequence)
            .where(
                Sequence.model == model,
                Sequence.company_id == company_id,
                Sequence.is_active.is_(True),
            )
            .with_for_update()
        )
        seq: Sequence | None = result.scalars().first()
        if seq is None:
            seq = Sequence(
                company_id=company_id,
                model=model,
                name=f"Sequence {model}",
                prefix=(prefix or model.upper())[:10],
                suffix="",
                number_padding=4,
                number_increment=1,
                last_number=0,
                reset="never",
                is_active=True,
            )
            self.session.add(seq)
            await self.session.flush()
        elif prefix and not seq.prefix:
            seq.prefix = prefix
        return seq

