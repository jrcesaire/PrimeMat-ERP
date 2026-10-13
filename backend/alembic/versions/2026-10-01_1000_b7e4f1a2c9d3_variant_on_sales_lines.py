"""add variant reference to sales document lines

Revision ID: b7e4f1a2c9d3
Revises: c3f8b1d4e609
Create Date: 2026-10-01

Vente par variante : les lignes de devis, commande, facture et bon de
livraison mémorisent la variante de produit choisie.

- ``variant_id``   : FK product_variants.id ON DELETE SET NULL, NULL autorisé
  (lignes sans variante et documents historiques).
- ``variant_name`` : instantané du libellé (name_suffix) au moment de la
  vente — garantit une réimpression fidèle même si la variante est renommée
  ou supprimée, à l'image de ``description`` et ``unit_price`` déjà
  dénormalisés sur les lignes.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4f1a2c9d3'
down_revision: Union[str, None] = 'c3f8b1d4e609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("quote_lines", "sales_order_lines", "invoice_lines", "delivery_lines")


def _table_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table)}


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    # batch_alter_table : obligatoire sur SQLite (copy-and-move). Gardes
    # d'idempotence : la migration peut etre rejouee apres un echec partiel.
    variants_ready = _table_exists("product_variants")
    for table in _TABLES:
        cols = _table_columns(table)
        inspector = sa.inspect(op.get_bind())
        fks = {fk.get("name") for fk in inspector.get_foreign_keys(table)}
        idxs = {ix.get("name") for ix in inspector.get_indexes(table)}
        with op.batch_alter_table(table) as batch_op:
            if "variant_id" not in cols:
                batch_op.add_column(
                    sa.Column("variant_id", sa.Integer(), nullable=True)
                )
            if "variant_name" not in cols:
                batch_op.add_column(
                    sa.Column("variant_name", sa.String(300), nullable=True)
                )
            if variants_ready and f"fk_{table}_variant" not in fks:
                batch_op.create_foreign_key(
                    f"fk_{table}_variant",
                    "product_variants",
                    ["variant_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if f"ix_{table}_variant_id" not in idxs:
                batch_op.create_index(
                    f"ix_{table}_variant_id", ["variant_id"]
                )


def downgrade() -> None:
    for table in reversed(_TABLES):
        inspector = sa.inspect(op.get_bind())
        idxs = {ix.get("name") for ix in inspector.get_indexes(table)}
        fks = {fk.get("name") for fk in inspector.get_foreign_keys(table)}
        cols = _table_columns(table)
        with op.batch_alter_table(table) as batch_op:
            if f"ix_{table}_variant_id" in idxs:
                batch_op.drop_index(f"ix_{table}_variant_id")
            if f"fk_{table}_variant" in fks:
                batch_op.drop_constraint(
                    f"fk_{table}_variant", type_="foreignkey"
                )
            if "variant_name" in cols:
                batch_op.drop_column("variant_name")
            if "variant_id" in cols:
                batch_op.drop_column("variant_id")
