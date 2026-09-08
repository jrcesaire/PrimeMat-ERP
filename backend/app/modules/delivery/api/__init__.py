"""Routeurs API du module Livraison."""
from app.modules.delivery.api import deliveries

routers = [deliveries.router]

__all__ = ["deliveries", "routers"]
