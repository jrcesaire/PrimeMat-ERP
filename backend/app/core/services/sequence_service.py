"""
Service de numérotation — génère les numéros de documents uniques.

Exemple : pour les factures, génère ``FA-2024-0001``, ``FA-2024-0002``, ...

Le service gère le reset annuel/mensuel et la sécurité concurrente.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.core.models.sequence import Sequence

logger = logging.getLogger(__name__)


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
        """
        Simplified API — retourne le prochain numéro pour un type de document.

        ``next_value("quote", "DEV")`` → ``DEV-2024-0001``
        """
        seq = await self._get_or_create(model, company_id, prefix)
        current = seq.last_number + 1
        seq.last_number = current
        await self.session.flush()
        return f"{seq.prefix}-{current:04d}"

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

    async def next_number(
        self,
        model: str,
        company_id: int,
    ) -> str:
        """
        Retourne le prochain numéro pour le modèle donné.

        - ``model`` : type d'entité (``invoice``, ``quote``, ``order``, ...)
        - ``company_id`` : entreprise propriétaire
        """
        result = await self.session.execute(
            select(Sequence)
            .where(
                Sequence.model == model,
                Sequence.company_id == company_id,
                Sequence.is_active.is_(True),
            )
            .with_for_update()  # verrou pour éviter les doublons concurrents
        )
        seq: Sequence | None = result.scalar_one_or_none()

        if seq is None:
            # Crée une séquence par défaut si elle n'existe pas
            seq = await self._create_default_sequence(model, company_id)

        # Reset annuel si configuré
        current_number = seq.last_number
        if seq.reset == "year":
            today = date.today()
            # Vérifie si le reset annuel est nécessaire
            year_key = today.strftime("%Y")
            last_reset = seq.date_ranges.get("last_reset_year", None) if seq.date_ranges else None
            if last_reset != year_key:
                current_number = 0
                if seq.date_ranges is None:
                    seq.date_ranges = {}
                seq.date_ranges["last_reset_year"] = year_key
        elif seq.reset == "month":
            today = date.today()
            month_key = today.strftime("%Y-%m")
            last_reset = seq.date_ranges.get("last_reset_month", None) if seq.date_ranges else None
            if last_reset != month_key:
                current_number = 0
                if seq.date_ranges is None:
                    seq.date_ranges = {}
                seq.date_ranges["last_reset_month"] = month_key

        current_number += seq.number_increment
        seq.last_number = current_number

        await self.session.flush()

        number_str = str(current_number).rjust(seq.number_padding, "0")
        return f"{seq.prefix}{number_str}{seq.suffix}"

    async def _create_default_sequence(
        self,
        model: str,
        company_id: int,
    ) -> Sequence:
        """Crée une séquence par défaut pour le modèle donné."""
        prefix_map = {
            "invoice": "FA-",
            "quote": "DEV-",
            "order": "COM-",
            "delivery": "BL-",
            "purchase_order": "PC-",
            "credit_note": "AC-",
        }
        prefix = prefix_map.get(model, f"{model.upper()}-")
        suffix = f"-{date.today().year}"

        seq = Sequence(
            company_id=company_id,
            model=model,
            name=f"Séquence {model}",
            prefix=prefix,
            suffix=suffix,
            number_padding=4,
            number_increment=1,
            last_number=0,
            reset="year",
            is_active=True,
        )
        self.session.add(seq)
        await self.session.flush()
        return seq
