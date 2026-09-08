"""Routeurs API du module Stock."""
from app.modules.stock.api import inventory

routers = [inventory.router]

__all__ = ["inventory", "routers"]