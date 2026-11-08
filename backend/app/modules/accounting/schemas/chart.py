"""Schémas du référentiel comptable — plan commercial ou non lucratif."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChartOptionRead(BaseModel):
    """Référentiel sélectionnable, avec le nombre de comptes qu'il apporte."""

    value: str
    label: str
    account_count: int


class ChartSettingsRead(BaseModel):
    """État du référentiel comptable de l'entreprise."""

    chart_of_accounts: str
    label: str
    account_count: int
    #: Faux tant que la comptabilité n'est pas vierge (cf. ``blockers``).
    can_change: bool
    #: Ce qui empêche la bascule — « 12 écritures », « 3 immobilisations »…
    blockers: list[str] = Field(default_factory=list)
    available: list[ChartOptionRead] = Field(default_factory=list)


class ChartSettingsUpdate(BaseModel):
    """Bascule vers un autre référentiel comptable."""

    chart_of_accounts: str = Field(..., min_length=1, max_length=20)


__all__ = ["ChartOptionRead", "ChartSettingsRead", "ChartSettingsUpdate"]
