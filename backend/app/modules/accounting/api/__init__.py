"""Routeurs API du module Comptabilité."""
from app.modules.accounting.api import accounts, financial_reports, posting

routers = [accounts.router, financial_reports.router, posting.router]

__all__ = ["accounts", "financial_reports", "posting", "routers"]
