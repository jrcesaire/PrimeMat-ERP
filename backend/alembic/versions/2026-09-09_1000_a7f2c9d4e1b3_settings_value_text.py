"""settings.value -> Text (CGV longues)

Revision ID: a7f2c9d4e1b3
Revises: e9cc6491a27b
Create Date: 2026-09-09 10:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a7f2c9d4e1b3"
down_revision = "e9cc6491a27b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.alter_column("value", existing_type=sa.String(5000), type_=sa.Text())


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.alter_column("value", existing_type=sa.Text(), type_=sa.String(5000))
