"""add journal_code to payments

Revision ID: c3f8b1d4e609
Revises: 9c2d4a1b7e30
Create Date: 2026-09-30

Journal comptable explicite du paiement (CAI, BAN, MOB, ...) :
l'encaissement peut viser un journal précis choisi par l'opérateur.
NULL conserve l'ancien comportement (journal déduit du mode d'encaissement).

- payments.journal_code VARCHAR(10) NULL
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8b1d4e609'
down_revision: Union[str, None] = '9c2d4a1b7e30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # batch_alter_table : obligatoire sur SQLite (copy-and-move). Garde
    # d'idempotence : la migration peut etre rejouee apres un echec partiel.
    if "journal_code" not in _table_columns("payments"):
        with op.batch_alter_table("payments") as batch_op:
            batch_op.add_column(
                sa.Column("journal_code", sa.String(10), nullable=True)
            )


def downgrade() -> None:
    if "journal_code" in _table_columns("payments"):
        with op.batch_alter_table("payments") as batch_op:
            batch_op.drop_column("journal_code")
