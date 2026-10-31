"""module Point de Vente : sessions de caisse, lien vente-session, mouvements de fonds

Revision ID: pos_module_20261026
Revises: fix_unique_indexes_20261020
Create Date: 2026-10-26 17:00:00.000000

Implémentation du module PoS (PRD « Improvements module PoS ») :

1. ``pos_sessions`` — cycle de caisse journalier (ouverture / clôture, solde
   reporté, heures de clôture et d'écriture comptable configurables).
2. ``sales_orders.pos_session_id`` — chaque vente comptoir est rattachée à la
   session de caisse active (§4.1.3).
3. ``pos_fund_movements`` — journal des mouvements de fonds manuels
   (dépôts / retraits) rattachés à une session (§4.1.2 §5).

Migration idempotente (rejouable après un échec partiel) : chaque objet n'est
créé que s'il est absent — elle s'applique donc aussi aux bases de
développement où les tables ont déjà été créées par
``Base.metadata.create_all`` (qui n'ajoute jamais de colonne à une table
existante : c'est précisément l'origine du ``pos_session_id`` manquant).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "pos_module_20261026"
down_revision: Union[str, None] = "fix_unique_indexes_20261020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _columns(table: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # 1. Sessions de caisse ------------------------------------------------
    if not _inspector().has_table("pos_sessions"):
        op.create_table(
            "pos_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(length=40), nullable=False),
            sa.Column(
                "status", sa.String(length=20), nullable=False, server_default="open"
            ),
            sa.Column("closing_hour", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "accounting_write_up_hour",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "initial_balance",
                sa.Numeric(precision=14, scale=4),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "closing_balance", sa.Numeric(precision=14, scale=4), nullable=True
            ),
            sa.Column("opened_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("opened_by_id", sa.Integer(), nullable=True),
            sa.Column("closed_by_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_pos_sessions_company",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["opened_by_id"],
                ["users.id"],
                name="fk_pos_sessions_opened_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["closed_by_id"],
                ["users.id"],
                name="fk_pos_sessions_closed_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_pos_sessions_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_pos_sessions_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_pos_sessions"),
        )
        op.create_index("ix_pos_sessions_company_id", "pos_sessions", ["company_id"])
        op.create_index(
            "ix_pos_sessions_reference", "pos_sessions", ["reference"], unique=True
        )
        op.create_index("ix_pos_sessions_status", "pos_sessions", ["status"])
        op.create_index("ix_pos_sessions_opened_by_id", "pos_sessions", ["opened_by_id"])
        op.create_index("ix_pos_sessions_closed_by_id", "pos_sessions", ["closed_by_id"])

    # 2. Lien vente ↔ session de caisse ------------------------------------
    # batch_alter_table : obligatoire sur SQLite (pas d'ALTER de contrainte en
    # direct — copy-and-move), même convention que les migrations 9c2d4a1b7e30
    # (salesperson_id) et e8a3c5d1f2b6 (archived).
    inspector = _inspector()
    cols = _columns("sales_orders")
    fks = {fk.get("name") for fk in inspector.get_foreign_keys("sales_orders")}
    idxs = {ix.get("name") for ix in inspector.get_indexes("sales_orders")}
    with op.batch_alter_table("sales_orders") as batch_op:
        if "pos_session_id" not in cols:
            batch_op.add_column(
                sa.Column("pos_session_id", sa.Integer(), nullable=True)
            )
        if "fk_sales_orders_pos_session" not in fks:
            batch_op.create_foreign_key(
                "fk_sales_orders_pos_session",
                "pos_sessions",
                ["pos_session_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "ix_sales_orders_pos_session_id" not in idxs:
            batch_op.create_index(
                "ix_sales_orders_pos_session_id", ["pos_session_id"]
            )

    # 3. Mouvements de fonds manuels ---------------------------------------
    if not _inspector().has_table("pos_fund_movements"):
        op.create_table(
            "pos_fund_movements",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("movement_type", sa.String(length=20), nullable=False),
            sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=False),
            sa.Column("reference", sa.String(length=100), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_pos_fund_movements_company",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["pos_sessions.id"],
                name="fk_pos_fund_movements_session",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name="fk_pos_fund_movements_created_by",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name="fk_pos_fund_movements_updated_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_pos_fund_movements"),
        )
        op.create_index(
            "ix_pos_fund_movements_company_id", "pos_fund_movements", ["company_id"]
        )
        op.create_index(
            "ix_pos_fund_movements_session_id", "pos_fund_movements", ["session_id"]
        )
        op.create_index(
            "ix_pos_fund_movements_movement_type",
            "pos_fund_movements",
            ["movement_type"],
        )


def downgrade() -> None:
    inspector = _inspector()
    if inspector.has_table("pos_fund_movements"):
        op.drop_table("pos_fund_movements")

    if inspector.has_table("sales_orders"):
        idxs = {ix.get("name") for ix in inspector.get_indexes("sales_orders")}
        fks = {fk.get("name") for fk in inspector.get_foreign_keys("sales_orders")}
        with op.batch_alter_table("sales_orders") as batch_op:
            if "ix_sales_orders_pos_session_id" in idxs:
                batch_op.drop_index("ix_sales_orders_pos_session_id")
            if "fk_sales_orders_pos_session" in fks:
                batch_op.drop_constraint(
                    "fk_sales_orders_pos_session", type_="foreignkey"
                )
            if "pos_session_id" in _columns("sales_orders"):
                batch_op.drop_column("pos_session_id")

    if _inspector().has_table("pos_sessions"):
        op.drop_table("pos_sessions")
