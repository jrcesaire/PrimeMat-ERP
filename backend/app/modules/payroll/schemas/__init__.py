"""Schémas Pydantic du module Paie (création / mise à jour / lecture)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------ #
# Employé
# ------------------------------------------------------------------ #
class EmployeeBase(BaseModel):
    reference: str
    last_name: str
    first_name: str
    gender: str | None = "unset"
    birth_date: date | None = None
    marital_status: str | None = "single"
    dependents: int | None = 0
    tax_parts: float | None = None
    job_title: str | None = None
    department: str | None = None
    hire_date: date | None = None
    end_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    cnps_number: str | None = None
    tax_id: str | None = None
    id_number: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    payment_method: str | None = None
    partner_id: int | None = None
    notes: str | None = None


class ContractInline(BaseModel):
    """Contrat créé en même temps que le salarié (paramètres de paie)."""

    structure_id: int | None = None
    reference: str | None = None
    date_start: date | None = None
    job_title: str | None = None
    wage: float = 0
    wage_type: str = "monthly"
    work_rate: float = 100


class EmployeeCreate(EmployeeBase):
    #: Paramètres de paie optionnels (salaire de base, structure) saisis à la création.
    contract: ContractInline | None = None


class EmployeeUpdate(BaseModel):
    reference: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    marital_status: str | None = None
    dependents: int | None = None
    tax_parts: float | None = None
    job_title: str | None = None
    department: str | None = None
    hire_date: date | None = None
    end_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    cnps_number: str | None = None
    tax_id: str | None = None
    id_number: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    payment_method: str | None = None
    partner_id: int | None = None
    status: str | None = None
    notes: str | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    full_name: str | None = None


# ------------------------------------------------------------------ #
# Contrat + avantages
# ------------------------------------------------------------------ #
class ContractCreate(BaseModel):
    employee_id: int
    structure_id: int
    date_start: date | None = None
    date_end: date | None = None
    job_title: str | None = None
    wage: float = 0
    wage_type: str = "monthly"
    work_rate: float = 100
    currency_code: str = "XOF"
    reference: str | None = None


class ContractUpdate(BaseModel):
    structure_id: int | None = None
    date_start: date | None = None
    date_end: date | None = None
    job_title: str | None = None
    wage: float | None = None
    wage_type: str | None = None
    work_rate: float | None = None
    state: str | None = None


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    employee_id: int
    structure_id: int
    date_start: date | None
    date_end: date | None
    job_title: str | None
    wage: float
    wage_type: str
    work_rate: float
    currency_code: str
    state: str


class AdvantageCreate(BaseModel):
    name: str
    rule_code: str | None = None
    amount: float = 0
    is_taxable: bool = True


class AdvantageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    name: str
    rule_code: str | None
    amount: float
    is_taxable: bool


# ------------------------------------------------------------------ #
# Structure / catégories / règles
# ------------------------------------------------------------------ #
class StructureCreate(BaseModel):
    name: str
    code: str
    country: str = "CI"
    is_default: bool = False
    notes: str | None = None


class StructureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    country: str
    is_default: bool
    is_active: bool


class CategoryCreate(BaseModel):
    name: str
    code: str
    sequence: int = 10


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    structure_id: int
    name: str
    code: str
    sequence: int


class RuleCreate(BaseModel):
    structure_id: int
    category_id: int
    name: str
    code: str
    sequence: int = 10
    amount_type: str = "fixed"
    amount_fixed: float = 0
    percentage_of: str | None = None
    percentage: float = 0
    formula: str | None = None
    scale_brackets: list[dict] | None = None
    condition: str | None = None
    appears_on_payslip: bool = True
    contribution_register_id: int | None = None
    account_debit: str | None = None
    account_credit: str | None = None


class RuleUpdate(BaseModel):
    name: str | None = None
    sequence: int | None = None
    amount_type: str | None = None
    amount_fixed: float | None = None
    percentage_of: str | None = None
    percentage: float | None = None
    formula: str | None = None
    scale_brackets: list[dict] | None = None
    condition: str | None = None
    appears_on_payslip: bool | None = None
    account_debit: str | None = None
    account_credit: str | None = None
    is_active: bool | None = None


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    structure_id: int
    category_id: int
    contribution_register_id: int | None
    name: str
    code: str
    sequence: int
    amount_type: str
    amount_fixed: float
    percentage_of: str | None
    percentage: float
    formula: str | None
    scale_brackets: list | None = None
    condition: str | None
    appears_on_payslip: bool
    account_debit: str | None
    account_credit: str | None
    is_active: bool


class ContributionRegisterCreate(BaseModel):
    name: str
    code: str
    account_code: str | None = None
    partner_id: int | None = None


class ContributionRegisterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    account_code: str | None
    partner_id: int | None


# ------------------------------------------------------------------ #
# Périodes / lots / bulletins
# ------------------------------------------------------------------ #
class PeriodCreate(BaseModel):
    name: str
    date_start: date
    date_end: date
    payment_date: date | None = None


class PeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_start: date
    date_end: date
    payment_date: date | None
    state: str


class RunCreate(BaseModel):
    period_id: int


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_id: int
    reference: str
    state: str
    total_net: float = 0


class InputCreate(BaseModel):
    input_code: str
    name: str
    quantity: float = 1
    amount: float = 0


class WorkedDayCreate(BaseModel):
    work_entry_type: str = "worked"
    name: str | None = None
    number_of_days: float = 0
    number_of_hours: float = 0


class PayslipLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category_code: str | None
    sequence: int
    quantity: float
    rate: float
    amount: float
    total: float


class PayslipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    run_id: int | None
    period_id: int | None
    employee_id: int
    contract_id: int | None
    structure_id: int | None
    date_from: date
    date_to: date
    payment_date: date | None
    state: str
    gross: float
    total_deductions: float
    net_wage: float
    employer_cost: float
    entry_id: int | None

