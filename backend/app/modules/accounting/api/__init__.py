"""Routeurs API du module Comptabilite."""
from app.modules.accounting.api import accounts, financial_reports, ohada, posting

routers = [accounts.router, financial_reports.router, ohada.router, posting.router]

__all__ = ["accounts", "financial_reports", "ohada", "posting", "routers"]
