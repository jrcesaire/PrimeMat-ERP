"""Routeurs API du module Ventes."""
from app.modules.sales.api import (
    routes_pos_fund_movement,
    routes_pos_session,
    routes_pos_settings,
    sales,
)

routers = [
    sales.router,
    routes_pos_session.router,
    routes_pos_fund_movement.router,
    routes_pos_settings.router,
]

__all__ = [
    "sales",
    "routes_pos_fund_movement",
    "routes_pos_session",
    "routes_pos_settings",
    "routers",
]