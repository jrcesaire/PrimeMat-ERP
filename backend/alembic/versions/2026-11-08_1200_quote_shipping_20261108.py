"""Devis : frais d'expédition forfaitaires

Revision ID: quote_shipping_20261108
Revises: payroll_module_20261107
Create Date: 2026-11-08 12:00:00.000000

Ajoute ``quotes.shipping_amount`` : coût d'expédition forfaitaire saisi sur le
devis, ajouté au total **après** la remise globale (donc jamais remisé) et
affiché juste avant le total. La commande issue du devis puis la facture
reprennent ce montant (``SalesOrder.shipping_amount`` existait déjà).

Migration idempotente : la colonne n'est ajoutée que si elle est absente.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "quote_shipping_20261108"
down_revision: Union[str, None] = "payroll_module_20261107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _quote_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("quotes"):
        return set()
    return {column["name"] for column in inspector.get_columns("quotes")}


def upgrade() -> None:
    if "shipping_amount" in _quote_columns():
        return
    op.add_column(
        "quotes",
        sa.Column(
            "shipping_amount",
            sa.Numeric(precision=14, scale=4),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    if "shipping_amount" not in _quote_columns():
        return
    with op.batch_alter_table("quotes") as batch:
        batch.drop_column("shipping_amount")
