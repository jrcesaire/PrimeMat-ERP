"""Routeurs API du module Facturation."""
from app.modules.invoicing.api import invoices

routers = [invoices.router]

__all__ = ["invoices", "routers"]
