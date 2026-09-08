"""add company logo

Revision ID: 6797c65bde81
Revises: c4f027e68914
Create Date: 2026-08-27 21:38:07.830356

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6797c65bde81'
down_revision: Union[str, None] = 'c4f027e68914'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajout du logo (data URL base64) sur les entreprises
    op.add_column('companies', sa.Column('logo', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'logo')
