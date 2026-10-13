"""add archived flag to sales orders (masquage historique caisse)

Revision ID: e8a3c5d1f2b6
Revises: d7a1c2e3f4b5
Create Date: 2026-10-10

Ventes comptoir : l'archivage masque une vente de l'historique du Point de
Vente sans toucher à la comptabilité (facture + paiement conservés).
- ``archived`` : Boolean NOT NULL DEFAULT 0.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8a3c5d1f2b6'
down_revision: Union[str, None] = 'd7a1c2e3f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # Garde d'idempotence : la migration peut être rejouée après un échec.
    if "archived" in _columns("sales_orders"):
        return
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.add_column(
            sa.Column(
                "archived",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    if "archived" not in _columns("sales_orders"):
        return
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_column("archived")
