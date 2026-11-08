"""Lanceur de développement : uvicorn + rechargement à chaud (mode détaché).

Pourquoi ce lanceur ?
---------------------
``uvicorn --reload`` redémarre son processus ouvrier avec
``os.kill(pid, signal.CTRL_C_EVENT)``. Cet appel n'est possible que si le
processus possède une **console**. Or les serveurs sont lancés détachés pour
survivre à la fermeture de la fenêtre de ``Lancer-ERP.bat``. Sans console, le
rechargement casse à la première modification :

    WARNING: WatchFiles detected changes in 'app\\....py'. Reloading...
    OSError: [WinError 6] Descripteur non valide
    SystemError: <built-in function kill> returned a result with an exception set

et le superviseur du rechargement meurt : le serveur ne répond plus.

On remplace donc ce redémarrage par ``Process.terminate()`` — la méthode
qu'uvicorn utilise déjà sur Linux/macOS — parfaitement fiable en détaché. La
socket d'écoute appartient au superviseur et est transmise au nouvel ouvrier :
la relance est donc transparente (aucune coupure, aucun « port déjà utilisé »).

Variables d'environnement :
    ERP_PORT          port d'écoute (défaut : 8001)
    ERP_HOST          interface d'écoute (défaut : 0.0.0.0)
    ERP_RELOAD_DIRS   dossiers surveillés, séparés par « , » (défaut : app)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from uvicorn._subprocess import get_subprocess  # noqa: E402
from uvicorn.supervisors import basereload  # noqa: E402


def restart_without_ctrl_c(self: basereload.BaseReload) -> None:
    """Redémarre l'ouvrier sans ``CTRL_C_EVENT`` (inutilisable sans console)."""
    self.is_restarting = True
    self.process.terminate()
    self.process.join()
    self.process = get_subprocess(
        config=self.config, target=self.target, sockets=self.sockets
    )
    self.process.start()


# Correctif appliqué au superviseur de rechargement d'uvicorn.
basereload.BaseReload.restart = restart_without_ctrl_c


def build_log_config(log_file: str | None) -> dict | None:
    """Config de logs d'uvicorn + fichier explicite pour l'ouvrier.

    L'ouvrier est un processus **enfant** : lancé en mode détaché, il n'hérite
    pas des descripteurs du superviseur, donc ses logs (démarrage, tracebacks,
    accès) partaient dans le vide. On lui donne donc un fichier de logs dédié.
    Le `logging.basicConfig` de l'application ne s'applique pas (la racine a
    déjà des gestionnaires), ce qui garantit que ses logs arrivent aussi ici.
    """
    if not log_file:
        return None
    # Les noms « default » / « access » sont ceux d'uvicorn : son
    # `configure_logging()` les modifie (couleurs) et exige leur présence.
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": False,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" '
                       "%(status_code)s",
            },
            "file": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "file",
                "filename": log_file,
                "encoding": "utf-8",
                "delay": True,
            },
        },
        "root": {"handlers": ["default", "file"], "level": "INFO"},
        "loggers": {
            "uvicorn": {
                "handlers": ["default", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access", "file"],
                "level": "INFO",
                "propagate": False,
            },
            # Le veilleur signale chaque cycle de surveillance : trop bavard
            # pour un fichier de logs applicatif.
            "watchfiles": {"level": "WARNING"},
            "watchfiles.main": {"level": "WARNING"},
        },
    }


def main() -> None:
    import uvicorn

    reload_dirs = [
        str(BACKEND / part.strip())
        for part in os.getenv("ERP_RELOAD_DIRS", "app").split(",")
        if part.strip()
    ]
    uvicorn.run(
        "app.main:app",
        host=os.getenv("ERP_HOST", "0.0.0.0"),
        port=int(os.getenv("ERP_PORT", "8001")),
        reload=True,
        reload_dirs=reload_dirs,
        log_level=os.getenv("ERP_LOG_LEVEL", "info"),
        log_config=build_log_config(os.getenv("ERP_LOG_FILE")),
    )


if __name__ == "__main__":
    main()
