"""add change_amount to payments (monnaie rendue en caisse)

Revision ID: d7a1c2e3f4b5
Revises: b7e4f1a2c9d3
Create Date: 2026-10-08

Vente comptoir : quand le client remet un montant supérieur au total,
la monnaie rendue est mémorisée sur le reçu (colonne ``change_amount``),
affichée à l'écran et imprimée sur le ticket de caisse.

- ``change_amount`` : Numeric(14,4) NOT NULL DEFAULT 0 — 0 pour tous les
  paiements classiques (aucune monnaie rendue hors caisse).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a1c2e3f4b5'
down_revision: Union[str, None] = 'b7e4f1a2c9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # Garde d'idempotence : la migration peut être rejouée après un échec.
    if "change_amount" in _columns("payments"):
        return
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "change_amount",
                sa.Numeric(14, 4),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    if "change_amount" not in _columns("payments"):
        return
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("change_amount")
