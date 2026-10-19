"""treasury bank reconciliation

Revision ID: 8cb6f09925c3
Revises: bceb6262bd19
Create Date: 2026-10-17 07:49:26.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cb6f09925c3'
down_revision: Union[str, None] = 'bceb6262bd19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'treasury_accounts',
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('account_code', sa.String(length=10), nullable=False),
        sa.Column('bank_name', sa.String(length=120), nullable=True),
        sa.Column('account_number', sa.String(length=64), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
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
        sa.UniqueConstraint('company_id', 'code', name='uq_treasury_account_company_code'),
    )
    op.create_index(op.f('ix_treasury_accounts_account_code'), 'treasury_accounts', ['account_code'], unique=False)
    op.create_index(op.f('ix_treasury_accounts_code'), 'treasury_accounts', ['code'], unique=False)
    op.create_index(op.f('ix_treasury_accounts_company_id'), 'treasury_accounts', ['company_id'], unique=False)

    op.create_table(
        'bank_statements',
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=False),
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('closing_balance', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['treasury_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bank_statements_account_id'), 'bank_statements', ['account_id'], unique=False)
    op.create_index(op.f('ix_bank_statements_company_id'), 'bank_statements', ['company_id'], unique=False)
    op.create_index(op.f('ix_bank_statements_status'), 'bank_statements', ['status'], unique=False)

    op.create_table(
        'bank_statement_lines',
        sa.Column('statement_id', sa.Integer(), nullable=False),
        sa.Column('line_date', sa.Date(), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('entry_line_id', sa.Integer(), nullable=True),
        sa.Column('reconciled_at', sa.DateTime(), nullable=True),
        sa.Column('reconciled_by', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entry_line_id'], ['journal_entry_lines.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reconciled_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['statement_id'], ['bank_statements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bank_statement_lines_company_id'), 'bank_statement_lines', ['company_id'], unique=False)
    op.create_index(op.f('ix_bank_statement_lines_entry_line_id'), 'bank_statement_lines', ['entry_line_id'], unique=False)
    op.create_index(op.f('ix_bank_statement_lines_statement_id'), 'bank_statement_lines', ['statement_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bank_statement_lines_statement_id'), table_name='bank_statement_lines')
    op.drop_index(op.f('ix_bank_statement_lines_entry_line_id'), table_name='bank_statement_lines')
    op.drop_index(op.f('ix_bank_statement_lines_company_id'), table_name='bank_statement_lines')
    op.drop_table('bank_statement_lines')
    op.drop_index(op.f('ix_bank_statements_status'), table_name='bank_statements')
    op.drop_index(op.f('ix_bank_statements_company_id'), table_name='bank_statements')
    op.drop_index(op.f('ix_bank_statements_account_id'), table_name='bank_statements')
    op.drop_table('bank_statements')
    op.drop_index(op.f('ix_treasury_accounts_company_id'), table_name='treasury_accounts')
    op.drop_index(op.f('ix_treasury_accounts_code'), table_name='treasury_accounts')
    op.drop_index(op.f('ix_treasury_accounts_account_code'), table_name='treasury_accounts')
    op.drop_table('treasury_accounts')
