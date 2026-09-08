"""Routeurs API du module Paiements."""
from app.modules.payments.api import payments

routers = [payments.router]

__all__ = ["payments", "routers"]
