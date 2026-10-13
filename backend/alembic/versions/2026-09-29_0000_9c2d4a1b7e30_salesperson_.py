"""add salesperson to quotes, orders, invoices

Revision ID: 9c2d4a1b7e30
Revises: a7f2c9d4e1b3
Create Date: 2026-09-29

Contact commercial (vendeur) : utilisateur affiché sur devis/facture.
- quotes.salesperson_id, sales_orders.salesperson_id, invoices.salesperson_id
- FK users.id ON DELETE SET NULL, NULL autorisé (documents historiques)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2d4a1b7e30'
down_revision: Union[str, None] = 'a7f2c9d4e1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # batch_alter_table : obligatoire sur SQLite (pas d'ALTER de contrainte
    # en direct — copy-and-move). Les gardes rendent la migration idempotente
    # (ré-exécution possible après un échec partiel).
    for table in ("quotes", "sales_orders", "invoices"):
        cols = _table_columns(table)
        inspector = sa.inspect(op.get_bind())
        fks = {fk.get("name") for fk in inspector.get_foreign_keys(table)}
        idxs = {ix.get("name") for ix in inspector.get_indexes(table)}
        with op.batch_alter_table(table) as batch_op:
            if "salesperson_id" not in cols:
                batch_op.add_column(
                    sa.Column("salesperson_id", sa.Integer(), nullable=True)
                )
            if f"fk_{table}_salesperson" not in fks:
                batch_op.create_foreign_key(
                    f"fk_{table}_salesperson",
                    "users",
                    ["salesperson_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if f"ix_{table}_salesperson_id" not in idxs:
                batch_op.create_index(
                    f"ix_{table}_salesperson_id", ["salesperson_id"]
                )


def downgrade() -> None:
    for table in ("invoices", "sales_orders", "quotes"):
        index_name = f"ix_{table}_salesperson_id"
        inspector = sa.inspect(op.get_bind())
        idxs = {ix.get("name") for ix in inspector.get_indexes(table)}
        if index_name in idxs:
            op.drop_index(index_name, table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(
                f"fk_{table}_salesperson", type_="foreignkey"
            )
            batch_op.drop_column("salesperson_id")
