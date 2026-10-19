import os
import sys

BACKEND = "D:/Travail/Projets/JR/ERP Matériaux de construction/backend"
os.chdir(BACKEND)

# S'assurer que l'URL SQLite par défaut du .env est valide (surtout en mode
# "alembic" / "uvicorn" lancé depuis un répertoire différent.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./erp_dev.db")

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )