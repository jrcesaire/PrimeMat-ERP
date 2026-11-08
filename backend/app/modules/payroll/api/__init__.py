"""Routeurs API du module Paie."""
from app.modules.payroll.api import (
    contracts,
    declarations,
    employees,
    periods,
    payslips,
    settings,
    structures,
)

routers = [
    employees.router,
    contracts.router,
    structures.router,
    periods.router,
    payslips.router,
    settings.router,
    declarations.router,
]

__all__ = [
    "contracts",
    "declarations",
    "employees",
    "periods",
    "payslips",
    "settings",
    "structures",
    "routers",
]
