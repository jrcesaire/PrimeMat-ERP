"""ohada configuration

Revision ID: bceb6262bd19
Revises: f3b7c9d2a1e4
Create Date: 2026-10-17 04:09:26.723569

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bceb6262bd19'
down_revision: Union[str, None] = 'f3b7c9d2a1e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exchange_rates',
        sa.Column('base_currency', sa.String(length=3), nullable=False),
        sa.Column('quote_currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'company_id', 'base_currency', 'quote_currency',
            name='uq_exchange_rate_company_currency_pair',
        ),
    )
    op.create_index(op.f('ix_exchange_rates_base_currency'), 'exchange_rates', ['base_currency'], unique=False)
    op.create_index(op.f('ix_exchange_rates_company_id'), 'exchange_rates', ['company_id'], unique=False)
    op.create_index(op.f('ix_exchange_rates_quote_currency'), 'exchange_rates', ['quote_currency'], unique=False)

    op.create_table(
        'ohada_parameters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.Column('rate_to_fx', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('fiscal_year_start', sa.Date(), nullable=True),
        sa.Column('fiscal_year_end', sa.Date(), nullable=True),
        sa.Column('tax_rate_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ohada_parameters_company_id'), 'ohada_parameters', ['company_id'], unique=False)
    op.create_index(op.f('ix_ohada_parameters_country_code'), 'ohada_parameters', ['country_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ohada_parameters_country_code'), table_name='ohada_parameters')
    op.drop_index(op.f('ix_ohada_parameters_company_id'), table_name='ohada_parameters')
    op.drop_table('ohada_parameters')
    op.drop_index(op.f('ix_exchange_rates_quote_currency'), table_name='exchange_rates')
    op.drop_index(op.f('ix_exchange_rates_company_id'), table_name='exchange_rates')
    op.drop_index(op.f('ix_exchange_rates_base_currency'), table_name='exchange_rates')
    op.drop_table('exchange_rates')
