"""TVA déclarative (Phase 2 PRD comptable)

Revision ID: vat_returns_20261104
Revises: fixed_assets_20261104
Create Date: 2026-11-04 17:00:00.000000

Domaine 6 du plan Phase 2 (SYSCOHADA) :

1. ``vat_returns`` — déclaration de TVA d'une période (TVA collectée,
   déductible, à payer ou crédit reportable) avec son cycle de vie
   ``draft`` → ``submitted`` → ``paid``, les comptes de contrepartie et de
   règlement, et les références des écritures générées.
2. ``vat_lines`` — détail par compte du plan OHADA (``443x`` TVA facturée,
   ``442x``/``445x`` TVA récupérable).

Migration idempotente (rejouable après un échec partiel) : chaque objet n'est
créé que s'il est absent — elle s'applique donc aussi aux bases de
développement où les tables ont déjà été créées par
``Base.metadata.create_all``.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "vat_returns_20261104"
down_revision: Union[str, None] = "fixed_assets_20261104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_index(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == name for i in _inspector().get_indexes(table))


def _create_index(table: str, name: str, columns: list[str]) -> None:
    if not _has_index(table, name):
        op.create_index(name, table, columns)


def upgrade() -> None:
    # 1. Déclarations -----------------------------------------------------
    if not _has_table("vat_returns"):
        op.create_table(
            "vat_returns",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(length=40), nullable=False),
            sa.Column("label", sa.String(length=60), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column(
                "status", sa.String(length=10), nullable=False, server_default="draft"
            ),
            sa.Column(
                "collected_amount",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "deductible_amount",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "net_due",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "credit_carry",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "counterpart_account",
                sa.String(length=10),
                nullable=False,
                server_default="441",
            ),
            sa.Column(
                "payment_account",
                sa.String(length=10),
                nullable=False,
                server_default="521",
            ),
            sa.Column(
                "journal_code",
                sa.String(length=10),
                nullable=False,
                server_default="OD",
            ),
            sa.Column("journal_entry_id", sa.Integer(), nullable=True),
            sa.Column("payment_entry_id", sa.Integer(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("paid_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["company_id"], ["companies.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_vat_returns_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_vat_returns_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "reference", name="uq_vat_return_company_reference"
            ),
            sa.CheckConstraint(
                "status IN ('draft', 'submitted', 'paid')",
                name="ck_vat_return_status_valid",
            ),
            sa.CheckConstraint(
                "period_end >= period_start", name="ck_vat_return_period_valid"
            ),
        )

    for name, columns in (
        ("ix_vat_returns_company_id", ["company_id"]),
        ("ix_vat_returns_reference", ["reference"]),
        ("ix_vat_returns_period_start", ["period_start"]),
        ("ix_vat_returns_period_end", ["period_end"]),
        ("ix_vat_returns_status", ["status"]),
        ("ix_vat_returns_journal_entry_id", ["journal_entry_id"]),
        ("ix_vat_returns_payment_entry_id", ["payment_entry_id"]),
    ):
        _create_index("vat_returns", name, columns)

    # 2. Détail par compte ------------------------------------------------
    if not _has_table("vat_lines"):
        op.create_table(
            "vat_lines",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("vat_return_id", sa.Integer(), nullable=False),
            sa.Column("account_code", sa.String(length=10), nullable=False),
            sa.Column("account_name", sa.String(length=250), nullable=False),
            sa.Column("kind", sa.String(length=12), nullable=False),
            sa.Column(
                "amount",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "entry_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["company_id"], ["companies.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["vat_return_id"], ["vat_returns.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_vat_lines_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_vat_lines_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "vat_return_id", "account_code", name="uq_vat_line_return_account"
            ),
            sa.CheckConstraint(
                "kind IN ('collected', 'deductible')", name="ck_vat_line_kind_valid"
            ),
        )

    for name, columns in (
        ("ix_vat_lines_company_id", ["company_id"]),
        ("ix_vat_lines_vat_return_id", ["vat_return_id"]),
        ("ix_vat_lines_account_code", ["account_code"]),
        ("ix_vat_lines_kind", ["kind"]),
    ):
        _create_index("vat_lines", name, columns)


def downgrade() -> None:
    if _has_table("vat_lines"):
        op.drop_table("vat_lines")
    if _has_table("vat_returns"):
        op.drop_table("vat_returns")