"""Module Paie : employés, contrats, structures/règles, bulletins

Revision ID: payroll_module_20261107
Revises: company_entity_fields_20261106
Create Date: 2026-11-07 09:00:00.000000

Crée le socle du module Paie (adaptation du modèle OCA/payroll) :
``employees``, ``payroll_structures``, ``payroll_rule_categories``,
``payroll_rules``, ``contribution_registers``, ``payroll_contracts``,
``contract_advantages``, ``payroll_periods``, ``payroll_runs``,
``payslips``, ``payslip_lines``, ``payslip_inputs``,
``payslip_worked_days``.

Migration idempotente (rejouable après un échec partiel) : chaque table n'est
créée que si elle est absente — elle s'applique donc aussi aux bases de
développement où ``Base.metadata.create_all`` les a déjà créées.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "payroll_module_20261107"
down_revision: Union[str, None] = "company_entity_fields_20261106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _tenant_columns() -> list[sa.Column]:
    """Colonnes communes de ``TenantMixin`` (hors clés étrangères)."""
    return [
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
    ]


def _tenant_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    """Contraintes de clés étrangères communes (company / users)."""
    return [
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=f"fk_{table}_company", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name=f"fk_{table}_created_by", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name=f"fk_{table}_updated_by", ondelete="SET NULL",
        ),
    ]


def upgrade() -> None:
    # 1. Employés --------------------------------------------------------- #
    if not _has_table("employees"):
        op.create_table(
            "employees",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("reference", sa.String(length=30), nullable=False),
            sa.Column("last_name", sa.String(length=100), nullable=False),
            sa.Column("first_name", sa.String(length=100), nullable=False),
            sa.Column("gender", sa.String(length=10), nullable=False, server_default="unset"),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("marital_status", sa.String(length=20), nullable=False, server_default="single"),
            sa.Column("dependents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tax_parts", sa.Numeric(precision=3, scale=1), nullable=False, server_default="1"),
            sa.Column("job_title", sa.String(length=120), nullable=True),
            sa.Column("department", sa.String(length=120), nullable=True),
            sa.Column("hire_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("email", sa.String(length=200), nullable=True),
            sa.Column("address", sa.String(length=300), nullable=True),
            sa.Column("cnps_number", sa.String(length=50), nullable=True),
            sa.Column("tax_id", sa.String(length=50), nullable=True),
            sa.Column("id_number", sa.String(length=50), nullable=True),
            sa.Column("bank_name", sa.String(length=120), nullable=True),
            sa.Column("bank_account", sa.String(length=60), nullable=True),
            sa.Column("payment_method", sa.String(length=20), nullable=True),
            sa.Column("partner_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("notes", sa.String(length=500), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="SET NULL"),
            *_tenant_fks("employees"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "reference", name="uq_employee_company_reference"),
        )
        op.create_index("ix_employees_reference", "employees", ["reference"])
        op.create_index("ix_employees_status", "employees", ["status"])

    # 2. Structures de paie ---------------------------------------------- #
    if not _has_table("payroll_structures"):
        op.create_table(
            "payroll_structures",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("code", sa.String(length=30), nullable=False),
            sa.Column("country", sa.String(length=2), nullable=False, server_default="CI"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notes", sa.String(length=500), nullable=True),
            *_tenant_columns(),
            *_tenant_fks("payroll_structures"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "code", name="uq_structure_company_code"),
        )
        op.create_index("ix_payroll_structures_code", "payroll_structures", ["code"])

    # 3. Catégories de rubriques ----------------------------------------- #
    if not _has_table("payroll_rule_categories"):
        op.create_table(
            "payroll_rule_categories",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("structure_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="10"),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["structure_id"], ["payroll_structures.id"],
                name="fk_rule_category_structure", ondelete="CASCADE",
            ),
            *_tenant_fks("payroll_rule_categories"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "structure_id", "code", name="uq_rule_category"
            ),
        )
        op.create_index(
            "ix_payroll_rule_categories_code", "payroll_rule_categories", ["code"]
        )

    # 4. Organismes de cotisation ---------------------------------------- #
    if not _has_table("contribution_registers"):
        op.create_table(
            "contribution_registers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("account_code", sa.String(length=10), nullable=True),
            sa.Column("partner_id", sa.Integer(), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="SET NULL"),
            *_tenant_fks("contribution_registers"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "code", name="uq_contribution_company_code"),
        )
        op.create_index(
            "ix_contribution_registers_code", "contribution_registers", ["code"]
        )

    # 5. Règles de paie -------------------------------------------------- #
    if not _has_table("payroll_rules"):
        op.create_table(
            "payroll_rules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("structure_id", sa.Integer(), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=False),
            sa.Column("contribution_register_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("amount_type", sa.String(length=20), nullable=False, server_default="fixed"),
            sa.Column("amount_fixed", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("percentage_of", sa.String(length=20), nullable=True),
            sa.Column("percentage", sa.Numeric(precision=7, scale=4), nullable=False, server_default="0"),
            sa.Column("formula", sa.Text(), nullable=True),
            sa.Column("scale_brackets", sa.JSON(), nullable=True),
            sa.Column("condition", sa.Text(), nullable=True),
            sa.Column("appears_on_payslip", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("account_debit", sa.String(length=10), nullable=True),
            sa.Column("account_credit", sa.String(length=10), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["structure_id"], ["payroll_structures.id"],
                name="fk_rule_structure", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["category_id"], ["payroll_rule_categories.id"],
                name="fk_rule_category", ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["contribution_register_id"], ["contribution_registers.id"],
                name="fk_rule_register", ondelete="SET NULL",
            ),
            *_tenant_fks("payroll_rules"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "structure_id", "code", name="uq_rule_structure_code"
            ),
        )
        op.create_index("ix_payroll_rules_code", "payroll_rules", ["code"])


    # 6. Contrats de travail --------------------------------------------- #
    if not _has_table("payroll_contracts"):
        op.create_table(
            "payroll_contracts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("reference", sa.String(length=40), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("structure_id", sa.Integer(), nullable=False),
            sa.Column("date_start", sa.Date(), nullable=False),
            sa.Column("date_end", sa.Date(), nullable=True),
            sa.Column("job_title", sa.String(length=120), nullable=True),
            sa.Column("wage", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("wage_type", sa.String(length=20), nullable=False, server_default="monthly"),
            sa.Column("work_rate", sa.Numeric(precision=6, scale=2), nullable=False, server_default="100"),
            sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="XOF"),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["employee_id"], ["employees.id"],
                name="fk_contract_employee", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["structure_id"], ["payroll_structures.id"],
                name="fk_contract_structure", ondelete="RESTRICT",
            ),
            *_tenant_fks("payroll_contracts"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "reference", name="uq_contract_company_reference"),
        )
        op.create_index("ix_payroll_contracts_reference", "payroll_contracts", ["reference"])
        op.create_index("ix_payroll_contracts_employee_id", "payroll_contracts", ["employee_id"])
        op.create_index("ix_payroll_contracts_state", "payroll_contracts", ["state"])

    # 7. Avantages en nature --------------------------------------------- #
    if not _has_table("contract_advantages"):
        op.create_table(
            "contract_advantages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("rule_code", sa.String(length=20), nullable=True),
            sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("is_taxable", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["contract_id"], ["payroll_contracts.id"],
                name="fk_advantage_contract", ondelete="CASCADE",
            ),
            *_tenant_fks("contract_advantages"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_contract_advantages_contract_id", "contract_advantages", ["contract_id"])

    # 8. Périodes de paie ------------------------------------------------ #
    if not _has_table("payroll_periods"):
        op.create_table(
            "payroll_periods",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("date_start", sa.Date(), nullable=False),
            sa.Column("date_end", sa.Date(), nullable=False),
            sa.Column("payment_date", sa.Date(), nullable=True),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("fiscal_year_id", sa.Integer(), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["fiscal_year_id"], ["fiscal_years.id"],
                name="fk_period_fiscal_year", ondelete="SET NULL",
            ),
            *_tenant_fks("payroll_periods"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payroll_periods_state", "payroll_periods", ["state"])


    # 9. Lots de bulletins ----------------------------------------------- #
    if not _has_table("payroll_runs"):
        op.create_table(
            "payroll_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("period_id", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(length=40), nullable=False),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("entry_id", sa.Integer(), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(
                ["period_id"], ["payroll_periods.id"],
                name="fk_run_period", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["entry_id"], ["journal_entries.id"],
                name="fk_run_entry", ondelete="SET NULL",
            ),
            *_tenant_fks("payroll_runs"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "reference", name="uq_run_company_reference"),
        )
        op.create_index("ix_payroll_runs_reference", "payroll_runs", ["reference"])
        op.create_index("ix_payroll_runs_state", "payroll_runs", ["state"])

    # 10. Bulletins de paie ---------------------------------------------- #
    if not _has_table("payslips"):
        op.create_table(
            "payslips",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("period_id", sa.Integer(), nullable=True),
            sa.Column("number", sa.String(length=40), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=True),
            sa.Column("structure_id", sa.Integer(), nullable=True),
            sa.Column("date_from", sa.Date(), nullable=False),
            sa.Column("date_to", sa.Date(), nullable=False),
            sa.Column("payment_date", sa.Date(), nullable=True),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("gross", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("total_deductions", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("net_wage", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("employer_cost", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("entry_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.String(length=500), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["run_id"], ["payroll_runs.id"], name="fk_payslip_run", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["period_id"], ["payroll_periods.id"], name="fk_payslip_period", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_payslip_employee", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["contract_id"], ["payroll_contracts.id"], name="fk_payslip_contract", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["structure_id"], ["payroll_structures.id"], name="fk_payslip_structure", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["entry_id"], ["journal_entries.id"], name="fk_payslip_entry", ondelete="SET NULL"),
            *_tenant_fks("payslips"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "number", name="uq_payslip_company_number"),
        )
        op.create_index("ix_payslips_number", "payslips", ["number"])
        op.create_index("ix_payslips_employee_id", "payslips", ["employee_id"])
        op.create_index("ix_payslips_period_id", "payslips", ["period_id"])
        op.create_index("ix_payslips_state", "payslips", ["state"])


    # 11. Lignes de bulletin --------------------------------------------- #
    if not _has_table("payslip_lines"):
        op.create_table(
            "payslip_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("payslip_id", sa.Integer(), nullable=False),
            sa.Column("rule_id", sa.Integer(), nullable=True),
            sa.Column("category_id", sa.Integer(), nullable=True),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("category_code", sa.String(length=20), nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False, server_default="1"),
            sa.Column("rate", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
            sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            sa.Column("account_debit", sa.String(length=10), nullable=True),
            sa.Column("account_credit", sa.String(length=10), nullable=True),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"], name="fk_line_payslip", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["rule_id"], ["payroll_rules.id"], name="fk_line_rule", ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["category_id"], ["payroll_rule_categories.id"], name="fk_line_category", ondelete="SET NULL"),
            *_tenant_fks("payslip_lines"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payslip_lines_payslip_id", "payslip_lines", ["payslip_id"])
        op.create_index("ix_payslip_lines_code", "payslip_lines", ["code"])

    # 12. Éléments variables --------------------------------------------- #
    if not _has_table("payslip_inputs"):
        op.create_table(
            "payslip_inputs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("payslip_id", sa.Integer(), nullable=False),
            sa.Column("input_code", sa.String(length=20), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False, server_default="1"),
            sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0"),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"], name="fk_input_payslip", ondelete="CASCADE"),
            *_tenant_fks("payslip_inputs"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payslip_inputs_payslip_id", "payslip_inputs", ["payslip_id"])

    # 13. Jours travaillés ----------------------------------------------- #
    if not _has_table("payslip_worked_days"):
        op.create_table(
            "payslip_worked_days",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("payslip_id", sa.Integer(), nullable=False),
            sa.Column("work_entry_type", sa.String(length=30), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=True),
            sa.Column("number_of_days", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
            sa.Column("number_of_hours", sa.Numeric(precision=7, scale=2), nullable=False, server_default="0"),
            *_tenant_columns(),
            sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"], name="fk_worked_day_payslip", ondelete="CASCADE"),
            *_tenant_fks("payslip_worked_days"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payslip_worked_days_payslip_id", "payslip_worked_days", ["payslip_id"])


def downgrade() -> None:
    for table in (
        "payslip_worked_days",
        "payslip_inputs",
        "payslip_lines",
        "payslips",
        "payroll_runs",
        "payroll_periods",
        "contract_advantages",
        "payroll_contracts",
        "payroll_rules",
        "contribution_registers",
        "payroll_rule_categories",
        "payroll_structures",
        "employees",
    ):
        if _has_table(table):
            op.drop_table(table)

