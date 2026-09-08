"""company establishment slogan tax info

Revision ID: b943cb3e0b29
Revises: 6797c65bde81
Create Date: 2026-08-28 09:00:08.324966

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b943cb3e0b29'
down_revision: Union[str, None] = '6797c65bde81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Établissement, slogan et informations fiscales/légales de l'entreprise
    op.add_column('companies', sa.Column('establishment', sa.String(length=120), nullable=True))
    op.add_column('companies', sa.Column('slogan', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('ncc', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('rccm', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('share_capital', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'share_capital')
    op.drop_column('companies', 'rccm')
    op.drop_column('companies', 'ncc')
    op.drop_column('companies', 'slogan')
    op.drop_column('companies', 'establishment')
