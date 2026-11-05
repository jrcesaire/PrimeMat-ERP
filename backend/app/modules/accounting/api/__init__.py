"""Routeurs API du module Comptabilite."""
from app.modules.accounting.api import (
    accounts,
    allocations,
    audit_logs,
    credit_notes,
    fiscal_regime,
    financial_reports,
    fixed_assets,
    ohada,
    posting,
    vat_returns,
)

routers = [
    accounts.router,
    allocations.router,
    audit_logs.router,
    credit_notes.router,
    fiscal_regime.router,
    financial_reports.router,
    fixed_assets.router,
    ohada.router,
    posting.router,
    vat_returns.router,
]

__all__ = [
    "accounts",
    "allocations",
    "audit_logs",
    "credit_notes",
    "fiscal_regime",
    "financial_reports",
    "fixed_assets",
    "ohada",
    "posting",
    "vat_returns",
    "routers",
]
