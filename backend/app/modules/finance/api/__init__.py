"""Routeurs API du module Finance."""
from app.modules.finance.api import expenses

routers = [expenses.router]

__all__ = ["expenses", "routers"]
