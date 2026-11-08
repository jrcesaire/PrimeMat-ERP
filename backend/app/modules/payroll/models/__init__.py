"""Modèles du module Paie.

L'import garantit l'enregistrement des tables dans la metadata SQLAlchemy et
résout les relationships inter-modules (``Partner`` du CRM, ``JournalEntry``
et ``FiscalYear`` de la comptabilité).
"""
from app.modules.payroll.models.contribution import ContributionRegister
from app.modules.payroll.models.contract import ContractAdvantage, PayrollContract
from app.modules.payroll.models.employee import Employee
from app.modules.payroll.models.period import PayrollPeriod, PayrollRun
from app.modules.payroll.models.payslip import (
    Payslip,
    PayslipInput,
    PayslipLine,
    PayslipWorkedDay,
)
from app.modules.payroll.models.structure import (
    PayrollRule,
    PayrollRuleCategory,
    PayrollStructure,
)

# Modèles liés — résolution des relationships inter-modules
from app.modules.crm.models.partner import Partner  # noqa: F401
from app.modules.accounting.models.journal_entry import JournalEntry  # noqa: F401
from app.modules.accounting.models.fiscal_year import FiscalYear  # noqa: F401

__all__ = [
    "Employee",
    "PayrollContract",
    "ContractAdvantage",
    "PayrollStructure",
    "PayrollRuleCategory",
    "PayrollRule",
    "ContributionRegister",
    "PayrollPeriod",
    "PayrollRun",
    "Payslip",
    "PayslipLine",
    "PayslipInput",
    "PayslipWorkedDay",
]
