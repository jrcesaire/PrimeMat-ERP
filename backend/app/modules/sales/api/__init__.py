"""Routeurs API du module Ventes."""
from app.modules.sales.api import sales

routers = [sales.router]

__all__ = ["sales", "routers"]