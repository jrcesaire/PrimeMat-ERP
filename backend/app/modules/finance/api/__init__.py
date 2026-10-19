"""Routeurs API du module Finance."""
from app.modules.finance.api import expenses, routes_treasury

routers = [expenses.router, routes_treasury.router]

__all__ = ["expenses", "routes_treasury", "routers"]
