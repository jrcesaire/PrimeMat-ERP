"""add missing purchases indexes

Revision ID: add_purchase_indexes_20261020
Revises: add_tax_regime_20261018
Create Date: 2026-10-20 09:30:00.000000

Ces index sont declares dans les modeles SQLAlchemy (``index=True``) mais
n'ont jamais ete crees par les migrations : le module Achats (demandes,
commandes, receptions, factures fournisseur) n'etait pas indexe sur
``company_id``, ce qui degrade les requetes multi-tenant (filtre tenant
sur chaque liste du module).

La migration est idempotente : un index deja present (base initialisee
directement depuis les modeles) n'est pas recree, ce qui permet de
l'appliquer sur une base deja alinee.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_purchase_indexes_20261020"
down_revision: Union[str, None] = "add_tax_regime_20261018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nom_index, table, colonnes)
INDEXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ix_products_sale_mode", "products", ("sale_mode",)),
    ("ix_purchase_requests_company_id", "purchase_requests", ("company_id",)),
    ("ix_purchase_requests_requester_id", "purchase_requests", ("requester_id",)),
    ("ix_purchase_orders_company_id", "purchase_orders", ("company_id",)),
    ("ix_purchase_request_lines_company_id", "purchase_request_lines", ("company_id",)),
    ("ix_purchase_order_lines_company_id", "purchase_order_lines", ("company_id",)),
    ("ix_purchase_receptions_company_id", "purchase_receptions", ("company_id",)),
    ("ix_purchase_receptions_status", "purchase_receptions", ("status",)),
    ("ix_purchase_reception_lines_company_id", "purchase_reception_lines", ("company_id",)),
    ("ix_supplier_invoices_company_id", "supplier_invoices", ("company_id",)),
    ("ix_supplier_invoice_lines_company_id", "supplier_invoice_lines", ("company_id",)),
)


def _existing_indexes() -> set[str]:
    """Noms des index deja presents sur la base cible."""
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for table in inspector.get_table_names():
        for idx in inspector.get_indexes(table):
            if idx.get("name"):
                names.add(idx["name"])
    return names


def upgrade() -> None:
    existing = _existing_indexes()
    for name, table, columns in INDEXES:
        if name in existing:
            continue
        op.create_index(name, table, list(columns), unique=False)


def downgrade() -> None:
    existing = _existing_indexes()
    for name, _table, _columns in INDEXES:
        if name not in existing:
            continue
        op.drop_index(name)