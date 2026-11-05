"""immobilisations et amortissements (Phase 2 PRD comptable)

Revision ID: fixed_assets_20261104
Revises: pos_module_20261026
Create Date: 2026-11-04 16:00:00.000000

Domaine 4 du plan Phase 2 (SYSCOHADA) :

1. ``fixed_assets`` — immobilisation amortissable, rattachée à un compte
   d'immobilisation (ex. 245) et à son compte d'amortissement cumulé
   (ex. 284), avec méthode linéaire ou dégressive SYSCOHADA.
2. ``depreciations`` — échéances du plan d'amortissement (une ligne par
   période) : dotation, cumul et valeur nette comptable après la période,
   plus le lien vers l'écriture comptable générée (``D 681 / C 28x``).

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
revision: str = "fixed_assets_20261104"
down_revision: Union[str, None] = "pos_module_20261026"
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
    # 1. Immobilisations --------------------------------------------------
    if not _has_table("fixed_assets"):
        op.create_table(
            "fixed_assets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=30), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column(
                "category",
                sa.String(length=20),
                nullable=False,
                server_default="equipment",
            ),
            sa.Column("asset_account", sa.String(length=10), nullable=False),
            sa.Column("depreciation_account", sa.String(length=10), nullable=False),
            sa.Column(
                "expense_account",
                sa.String(length=10),
                nullable=False,
                server_default="681",
            ),
            sa.Column(
                "journal_code",
                sa.String(length=10),
                nullable=False,
                server_default="OD",
            ),
            sa.Column("acquisition_date", sa.Date(), nullable=False),
            sa.Column("in_service_date", sa.Date(), nullable=False),
            sa.Column(
                "acquisition_cost",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "residual_value",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "useful_life_years", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "method", sa.String(length=10), nullable=False, server_default="linear"
            ),
            sa.Column(
                "periodicity",
                sa.String(length=10),
                nullable=False,
                server_default="annual",
            ),
            sa.Column(
                "status", sa.String(length=10), nullable=False, server_default="draft"
            ),
            sa.Column("disposal_date", sa.Date(), nullable=True),
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
                name="fk_fixed_assets_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_fixed_assets_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "code", name="uq_fixed_asset_company_code"
            ),
            sa.CheckConstraint(
                "acquisition_cost >= 0", name="ck_fixed_asset_cost_nonnegative"
            ),
            sa.CheckConstraint(
                "residual_value >= 0", name="ck_fixed_asset_residual_nonnegative"
            ),
            sa.CheckConstraint(
                "useful_life_years > 0", name="ck_fixed_asset_life_positive"
            ),
            sa.CheckConstraint(
                "method IN ('linear', 'declining')", name="ck_fixed_asset_method_valid"
            ),
            sa.CheckConstraint(
                "periodicity IN ('annual', 'monthly')",
                name="ck_fixed_asset_periodicity_valid",
            ),
            sa.CheckConstraint(
                "status IN ('draft', 'active', 'disposed')",
                name="ck_fixed_asset_status_valid",
            ),
        )

    for name, columns in (
        ("ix_fixed_assets_company_id", ["company_id"]),
        ("ix_fixed_assets_code", ["code"]),
        ("ix_fixed_assets_category", ["category"]),
        ("ix_fixed_assets_asset_account", ["asset_account"]),
        ("ix_fixed_assets_acquisition_date", ["acquisition_date"]),
        ("ix_fixed_assets_status", ["status"]),
    ):
        _create_index("fixed_assets", name, columns)

    # 2. Amortissements ---------------------------------------------------
    if not _has_table("depreciations"):
        op.create_table(
            "depreciations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("period_index", sa.Integer(), nullable=False),
            sa.Column("period_date", sa.Date(), nullable=False),
            sa.Column(
                "opening_value",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "amount",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "accumulated",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "net_value",
                sa.Numeric(precision=16, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "status",
                sa.String(length=10),
                nullable=False,
                server_default="planned",
            ),
            sa.Column("journal_entry_id", sa.Integer(), nullable=True),
            sa.Column("posted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["company_id"], ["companies.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["asset_id"], ["fixed_assets.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_depreciations_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_depreciations_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "asset_id", "period_index", name="uq_depreciation_asset_period"
            ),
            sa.CheckConstraint(
                "status IN ('planned', 'posted')", name="ck_depreciation_status_valid"
            ),
        )

    for name, columns in (
        ("ix_depreciations_company_id", ["company_id"]),
        ("ix_depreciations_asset_id", ["asset_id"]),
        ("ix_depreciations_period_date", ["period_date"]),
        ("ix_depreciations_status", ["status"]),
        ("ix_depreciations_journal_entry_id", ["journal_entry_id"]),
    ):
        _create_index("depreciations", name, columns)


def downgrade() -> None:
    if _has_table("depreciations"):
        op.drop_table("depreciations")
    if _has_table("fixed_assets"):
        op.drop_table("fixed_assets")
