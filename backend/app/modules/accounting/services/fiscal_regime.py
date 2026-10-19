"""
Service de configuration fiscale — régimes d'imposition Côte d'Ivoire (TEE / RME / RSI / RNI).

Règle métier : pas de basculement automatique, pas de blocage des processus commerciaux.
Seule une alerte de dépassement de seuil est levée, avec suggestion de changement.
Le changement de régime reste une décision manuelle de l'utilisateur.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.company import Company
from app.modules.accounting.schemas import TaxRegimeRead, TaxRegimeUpdate
from app.shared.enums import TaxRegime, TAX_REGIME_THRESHOLDS


class TaxRegimeService:
    """Lecture, mise à jour et détection de dépassement de seuil du régime fiscal."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _regime_value(value: TaxRegime | str | None) -> str | None:
        """Normalise un régime en chaîne ('TEE'…), que la valeur soit un enum
        (objet encore en mémoire après assignment) ou une string lue en DB.

        `str(TaxRegime.TEE)` renverrait 'TaxRegime.TEE' — d'où ce helper.
        """
        if value is None:
            return None
        if isinstance(value, TaxRegime):
            return value.value
        return str(value)

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def get_tax_regime(self, company_id: int) -> TaxRegimeRead | None:
        """Retourne le régime fiscal de l'entreprise avec indication de dépassement."""
        company = await self.session.get(Company, company_id)
        if company is None:
            return None

        current_regime = company.tax_regime
        suggested = company.suggested_tax_regime

        threshold = None
        if current_regime is not None:
            try:
                regime_enum = TaxRegime(current_regime)
                threshold = TAX_REGIME_THRESHOLDS.get(regime_enum)
            except ValueError:
                pass

        ca_exceeds = False
        if suggested is not None and suggested != current_regime:
            ca_exceeds = True

        tva_blocked = current_regime in (TaxRegime.TEE, TaxRegime.RME)

        return TaxRegimeRead(
            company_id=company.id,
            tax_regime=self._regime_value(current_regime),
            suggested_tax_regime=self._regime_value(suggested),
            ca_threshold=threshold,
            ca_exceeds_threshold=ca_exceeds,
            tva_blocked=tva_blocked,
        )

    # ------------------------------------------------------------------ #
    # Mise à jour manuelle (jamais automatique)
    # ------------------------------------------------------------------ #
    async def update_tax_regime(
        self, company_id: int, payload: TaxRegimeUpdate
    ) -> TaxRegimeRead | None:
        """Définit manuellement le régime fiscal de l'entreprise."""
        company = await self.session.get(Company, company_id)
        if company is None:
            return None

        try:
            regime_enum = TaxRegime(payload.tax_regime)
        except ValueError:
            raise ValueError(f"Régime fiscal invalide : {payload.tax_regime}")

        company.tax_regime = regime_enum
        company.suggested_tax_regime = None

        await self.session.flush()
        return await self.get_tax_regime(company_id)

    # ------------------------------------------------------------------ #
    # Détection de dépassement de seuil (appelée depuis le service métier)
    # ------------------------------------------------------------------ #
    async def detect_ca_threshold(
        self, company_id: int, ca_annual_ttc: Decimal
    ) -> TaxRegimeRead | None:
        """Détecte si le CA annuel TTC dépasse le seuil du régime actuel.

        - Ne bascule JAMAIS automatiquement
        - Définit `suggested_tax_regime` si dépassement
        - Retourne la lecture mise à jour avec `ca_exceeds_threshold = True`
        """
        company = await self.session.get(Company, company_id)
        if company is None:
            return None

        current = company.tax_regime
        if current is None:
            return await self.get_tax_regime(company_id)

        try:
            regime_enum = TaxRegime(current)
        except ValueError:
            return await self.get_tax_regime(company_id)

        threshold = TAX_REGIME_THRESHOLDS.get(regime_enum)
        if threshold is None or threshold == 0:
            return await self.get_tax_regime(company_id)

        ca_exceeds = ca_annual_ttc > threshold

        suggested = company.suggested_tax_regime
        if ca_exceeds:
            suggested = self._next_regime(regime_enum)
            company.suggested_tax_regime = suggested

        await self.session.flush()
        return await self.get_tax_regime(company_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _next_regime(current: TaxRegime) -> TaxRegime:
        order = [TaxRegime.TEE, TaxRegime.RME, TaxRegime.RSI, TaxRegime.RNI]
        try:
            idx = order.index(current)
        except ValueError:
            return current
        if idx + 1 < len(order):
            return order[idx + 1]
        return current

    @staticmethod
    def is_tva_blocked(tax_regime: str | TaxRegime | None) -> bool:
        if tax_regime is None:
            return False
        if isinstance(tax_regime, TaxRegime):
            return tax_regime in (TaxRegime.TEE, TaxRegime.RME)
        try:
            return TaxRegime(tax_regime) in (TaxRegime.TEE, TaxRegime.RME)
        except ValueError:
            return False


__all__ = ["TaxRegimeService"]