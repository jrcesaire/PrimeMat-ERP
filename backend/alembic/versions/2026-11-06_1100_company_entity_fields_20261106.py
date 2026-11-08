"""Renseignements d'entité de l'entreprise

Revision ID: company_entity_fields_20261106
Revises: chart_of_accounts_20261106
Create Date: 2026-11-06 11:00:00.000000

Ajoute les mentions d'entité exigées par l'assistant de configuration fiscale
et reprises sur les documents officiels :

- ``greffe``              — tribunal de commerce dont dépend l'entreprise ;
- ``importer_code``       — numéro de code importateur ;
- ``social_security_code``— numéro de caisse sociale ;
- ``activity_code``       — code d'activité principale ;
- ``closing_date``        — date d'arrêté des comptes (« 31/12 ») ;
- ``fiscal_year_months``  — durée de l'exercice en mois (12 = année civile).

Toutes sont facultatives : l'utilisateur peut reporter la configuration, la
création d'un devis ou d'une facture n'exigeant que le nom, le téléphone, la
devise, l'adresse, la ville et le pays (``app.core.services.company_profile``).

``fiscal_year_months`` est non nulle avec ``server_default=12`` : les
entreprises existantes tiennent une année civile, la valeur est donc juste.

Migration idempotente (rejouable après un échec partiel) : chaque colonne
n'est ajoutée que si elle est absente — elle s'applique donc aussi aux bases
de développement où ``Base.metadata.create_all`` les a déjà créées.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "company_entity_fields_20261106"
down_revision: Union[str, None] = "chart_of_accounts_20261106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Colonnes ajoutées : ``(nom, type, nullabilité, valeur par défaut serveur)``.
COLUMNS: tuple[tuple[str, sa.types.TypeEngine, bool, str | None], ...] = (
    ("greffe", sa.String(length=120), True, None),
    ("importer_code", sa.String(length=60), True, None),
    ("social_security_code", sa.String(length=60), True, None),
    ("activity_code", sa.String(length=60), True, None),
    ("closing_date", sa.String(length=32), True, None),
    ("fiscal_year_months", sa.Integer(), False, "12"),
)


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return False
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    for name, column_type, nullable, server_default in COLUMNS:
        if _has_column("companies", name):
            continue
        op.add_column(
            "companies",
            sa.Column(
                name,
                column_type,
                nullable=nullable,
                server_default=server_default,
            ),
        )


def downgrade() -> None:
    for name, *_ in COLUMNS:
        if _has_column("companies", name):
            op.drop_column("companies", name)
