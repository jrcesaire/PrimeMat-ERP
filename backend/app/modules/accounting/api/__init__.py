"""Routeurs API du module Comptabilite."""
from app.modules.accounting.api import accounts, allocations, financial_reports, ohada, posting

routers = [
    accounts.router,
    allocations.router,
    financial_reports.router,
    ohada.router,
    posting.router,
]

__all__ = [
    "accounts",
    "allocations",
    "financial_reports",
    "ohada",
    "posting",
    "routers",
]
