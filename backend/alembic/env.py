"""
Script d'environnement Alembic — migration async.

Ce script est exécuté par ``alembic upgrade head`` / ``alembic downgrade``.
Il configure le moteur async SQLAlchemy et génère les migrations.
"""
from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Sous Windows, asyncio utilise l'event loop "Proactor" par defaut, que psycopg
# refuse en mode async ("cannot use the 'ProactorEventLoop' to run in async mode").
# On impose le "Selector" event loop, compatible avec psycopg, uniquement sur
# Windows : sans cela, `alembic upgrade head` echoue sur PostgreSQL.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Importe tous les modèles pour qu'ils soient inclus dans metadata
from app.core.models import *  # noqa: F401,F403
from app.modules.catalogue import models as catalogue_models  # noqa: F401
from app.modules.crm import models as crm_models  # noqa: F401
from app.modules.sales import models as sales_models  # noqa: F401
from app.modules.stock import models as stock_models  # noqa: F401
from app.modules.invoicing import models as invoicing_models  # noqa: F401
from app.modules.payments import models as payments_models  # noqa: F401
from app.modules.delivery import models as delivery_models  # noqa: F401
from app.modules.finance import models as finance_models  # noqa: F401
from app.modules.accounting import models as accounting_models  # noqa: F401
from app.modules.purchases import models as purchases_models  # noqa: F401

# Métadonnées pour autogénération
target_metadata = Base.metadata

# Configuration du logging
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


def get_url() -> str:
    """Retourne l'URL de la base de données."""
    return str(settings.database_url)


async def run_migrations_online() -> None:
    """Exécute les migrations en mode online (connexion réelle)."""
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_url()},
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection: Connection) -> None:
    """Configure le contexte de migration."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Les modeles de l'application vivent tous dans le schema "public".
        # On ne compare donc QUE le schema courant ("public") : sans cela,
        # Alembic voit aussi les schemas gérés par Supabase (auth, storage,
        # realtime...) et signale des suppressions de tables/index qui
        # n'ont rien a voir avec l'ERP. Pire, un "revision --autogenerate"
        # genererait un DROP de toutes ces tables Supabase.
        include_schemas=False,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_migrations_online())
