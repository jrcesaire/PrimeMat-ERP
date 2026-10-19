"""Routeurs API du module Comptabilite."""
from app.modules.accounting.api import (
    accounts,
    allocations,
    credit_notes,
    fiscal_regime,
    financial_reports,
    ohada,
    posting,
)

routers = [
    accounts.router,
    allocations.router,
    credit_notes.router,
    fiscal_regime.router,
    financial_reports.router,
    ohada.router,
    posting.router,
]

__all__ = [
    "accounts",
    "allocations",
    "credit_notes",
    "fiscal_regime",
    "financial_reports",
    "ohada",
    "posting",
    "routers",
]
