"""Référentiel de plan comptable par entreprise

Revision ID: chart_of_accounts_20261106
Revises: vat_returns_20261104
Create Date: 2026-11-06 10:00:00.000000

Ajoute ``companies.chart_of_accounts`` : le référentiel du plan comptable tenu
par l'entreprise, choisi à l'initialisation (assistant de configuration) puis
modifiable depuis les paramètres comptables.

- ``SYSCOHADA`` — plan commercial ; c'est la valeur par défaut, les entreprises
  existantes restent donc sur leur référentiel ;
- ``SYCEBNL`` — Système Comptable des Entités à But Non Lucratif.

Les deux plans tiennent sur six chiffres (code SYSCOHADA à quatre chiffres
complété de deux zéros) et partagent l'arborescence des classes 1 à 9.

Migration idempotente (rejouable après un échec partiel) : la colonne n'est
ajoutée que si elle est absente — elle s'applique donc aussi aux bases de
développement où ``Base.metadata.create_all`` l'a déjà créée.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "chart_of_accounts_20261106"
down_revision: Union[str, None] = "vat_returns_20261104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Type énuméré portant les référentiels supportés.
CHART_ENUM = sa.Enum("SYSCOHADA", "SYCEBNL", name="chartofaccounts")


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if _has_column("companies", "chart_of_accounts"):
        return
    op.add_column(
        "companies",
        sa.Column(
            "chart_of_accounts",
            CHART_ENUM,
            nullable=False,
            server_default="SYSCOHADA",
        ),
    )


def downgrade() -> None:
    if _has_column("companies", "chart_of_accounts"):
        op.drop_column("companies", "chart_of_accounts")
