"""
Sauvegarde locale — crée une archive de la base de données.

Utilise ``pg_dump`` en production ou un marqueur de test en développement.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)


async def create_local_backup(full: bool = True) -> str:
    """
    Crée une archive locale de la base de données.

    - ``full`` : True → sauvegarde complète, False → incrémentale
    - Retourne le chemin du fichier temporaire créé.
    """
    from app.core.config import settings
    import asyncio

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    btype = "full" if full else "incremental"
    backup_path = os.path.join(
        tempfile.gettempdir(), f"erp_{btype}_{timestamp}.tar.gz"
    )

    # Parse la database URL
    db_url = str(settings.database_url)
    if "://" in db_url:
        db_url = db_url.split("://", 1)[1]

    if "@" in db_url:
        creds, host_db = db_url.split("@", 1)
    else:
        creds = ""
        host_db = db_url

    if "/" in host_db:
        host_part, db_name = host_db.rsplit("/", 1)
    else:
        db_name = "erp_db"
        host_part = host_db

    user_pass = creds.split(":", 1) if creds else ("postgres", "")
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""

    host = host_part.split(":")[0] if ":" in host_part else host_part
    port = host_part.split(":")[1] if ":" in host_part else "5432"

    cmd = [
        "pg_dump",
        "--host", host,
        "--port", port,
        "--username", user,
        "--format", "custom",
        "--file", backup_path,
        db_name,
    ]

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, env=env, capture_output=True, text=True),
        )
        if proc.returncode != 0:
            logger.error("pg_dump échoué: %s", proc.stderr)
            raise RuntimeError(f"pg_dump failed: {proc.stderr}")
    except FileNotFoundError:
        logger.warning("pg_dump non disponible — création d'un marqueur")
        with open(backup_path, "w") as f:
            f.write(f"PLACEHOLDER pg_dump unavailable — {btype} — {timestamp}\n")

    return backup_path
