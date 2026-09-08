"""Routeurs API du module CRM."""
from app.modules.crm.api import partners

routers = [partners.router]

__all__ = ["partners", "routers"]
