"""enforce unique indexes and sale_mode varchar type

Revision ID: fix_unique_indexes_20261020
Revises: add_purchase_indexes_20261020
Create Date: 2026-10-20 10:15:00.000000

Deux derives entre les migrations et les modeles SQLAlchemy :

1. Unicite des index du module Achats
   Les modeles declarent ``unique=True, index=True`` sur les numeros de
   demande/commande/reception et sur la reference de facture fournisseur,
   mais les migrations n'ont cree que des index simples (non uniques).
   La base n'imposait donc pas l'unicite attendue par le modele.

2. Type de ``sale_mode``
   ``products.sale_mode`` et ``product_categories.sale_mode`` sont
   ``VARCHAR(10)`` dans les modeles mais ``TEXT`` en base (crees sans
   longueur par la migration catalogue).

La migration est idempotente : chaque correction n'est appliquee que si
elle est necessaire (index deja unique, colonne deja VARCHAR(10)).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_unique_indexes_20261020"
down_revision: Union[str, None] = "add_purchase_indexes_20261020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nom_index, table, colonne)
UNIQUE_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_purchase_requests_number", "purchase_requests", "number"),
    ("ix_purchase_orders_number", "purchase_orders", "number"),
    ("ix_purchase_receptions_number", "purchase_receptions", "number"),
    ("ix_supplier_invoices_reference", "supplier_invoices", "reference"),
)

# (table, colonne)
SALE_MODE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("products", "sale_mode"),
    ("product_categories", "sale_mode"),
)


def _indexes() -> dict[str, dict]:
    """Index existants, indexes par nom."""
    inspector = sa.inspect(op.get_bind())
    result: dict[str, dict] = {}
    for table in inspector.get_table_names():
        for idx in inspector.get_indexes(table):
            if idx.get("name"):
                result[idx["name"]] = idx
    return result


def _column_info(table: str, column: str):
    """(type, nullable) de la colonne, ou None si la colonne n'existe pas."""
    inspector = sa.inspect(op.get_bind())
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return col["type"], col.get("nullable", True)
    return None


def upgrade() -> None:
    indexes = _indexes()

    # 1. Unicite des index du module Achats
    for name, table, column in UNIQUE_INDEXES:
        idx = indexes.get(name)
        if idx is None:
            # Index absent : on le cree directement en unique
            op.create_index(name, table, [column], unique=True)
            continue
        if idx.get("unique"):
            continue
        # Index existant non unique : on le recree en unique.
        # Utilise batch_alter_table pour rester compatible SQLite.
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(name)
            batch_op.create_index(name, [column], unique=True)

    # 2. Type VARCHAR(10) pour sale_mode
    for table, column in SALE_MODE_COLUMNS:
        info = _column_info(table, column)
        if info is None:
            continue
        current, nullable = info
        length = getattr(current, "length", None)
        if isinstance(current, sa.String) and length == 10:
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=current,
                type_=sa.String(length=10),
                existing_nullable=nullable,
            )


def downgrade() -> None:
    indexes = _indexes()

    for name, table, column in UNIQUE_INDEXES:
        idx = indexes.get(name)
        if idx is None or not idx.get("unique"):
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(name)
            batch_op.create_index(name, [column], unique=False)

    for table, column in SALE_MODE_COLUMNS:
        info = _column_info(table, column)
        if info is None:
            continue
        current, nullable = info
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=current,
                type_=sa.Text(),
                existing_nullable=nullable,
            )
