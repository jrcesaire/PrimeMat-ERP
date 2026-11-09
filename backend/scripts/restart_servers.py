"""Redémarre les serveurs uvicorn (8001/8002) de façon détachée.

Le rechargement automatique est **désactivé par défaut** : une modification de
code Python nécessite donc un redémarrage explicite des backends. Cela évite
qu'une écriture de fichier interrompe une requête longue (génération PDF,
import, calcul de paie) et garantit que les serveurs exécutent une version
stable du code.

Les PIDs lancés sont enregistrés dans ``logs/dev_state.json``.

Activer temporairement : ``set ERP_RELOAD=1`` ou option ``--reload``.
Désactiver explicitement : option ``--no-reload``.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
LOGS = BACKEND / "logs"
LOGS.mkdir(exist_ok=True)
PORTS = (8001, 8002)
STATE_FILE = LOGS / "dev_state.json"

# Dossiers surveillés par le rechargement automatique (relatifs au backend).
# Limiter la surveillance à `app` évite de recharger sur les écritures de la
# base SQLite, des logs ou des caches : uvicorn ne surveille que « *.py ».
RELOAD_DIRS = ("app",)


def reload_enabled() -> bool:
    """Le rechargement automatique est-il explicitement demandé ?"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--no-reload", action="store_true")
    args, _ = parser.parse_known_args()
    if args.no_reload:
        return False
    if args.reload:
        return True
    return os.getenv("ERP_RELOAD", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def uvicorn_command(port: int, reload: bool) -> list[str]:
    """Commande de démarrage d'un serveur uvicorn.

    En mode rechargement, on passe par ``scripts/dev_server.py`` : il applique
    le correctif Windows « détaché » (voir la docstring de ce fichier) et
    n'utilise aucun motif glob en ligne de commande — un motif comme ``*.py``
    serait développé par Windows en liste de fichiers et casserait le CLI.
    """
    if reload:
        return [
            sys.executable,
            str(Path(__file__).resolve().parent / "dev_server.py"),
        ]
    return [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", str(port),
    ]


def kill_listeners(ports: tuple[int, ...]) -> None:
    """Tue les processus qui écoutent déjà sur les ports donnés."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True).stdout
    out = out.decode("utf-8", errors="replace")
    pids: set[int] = set()
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) >= 5 and any(parts[1].endswith(f":{p}") for p in ports):
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                pass
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        print(f"Processus {pid} arrêté")
    if pids:
        time.sleep(2)  # laisse le temps au port de se libérer


CREATE_FLAGS = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
)


def run_migrations() -> None:
    """Aligne le schéma SQLite sur les modèles ORM avant de démarrer l'API.

    `Base.metadata.create_all()` (utilisé au démarrage en mode debug) ne crée
    que les tables *manquantes* : il n'ajoute jamais une colonne à une table
    existante. Sans cette étape, une nouvelle révision de modèle produit des
    500 « no such column: ... » sur toutes les lignes concernées. Le
    Dockerfile fait de même (`alembic upgrade head` dans son CMD).
    """
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND), capture_output=True,
    )
    if res.returncode == 0:
        print("Migrations Alembic appliquees (upgrade head)")
    else:
        out = res.stderr.decode("utf-8", errors="replace")
        print("!! echec des migrations Alembic :")
        print(out[-1500:])


kill_listeners(PORTS)
run_migrations()

RELOAD = reload_enabled()
print("Rechargement automatique :",
      "ACTIF (rechargement a chaud du code)" if RELOAD else "inactif")

pids: dict[str, int] = {}
for port in PORTS:
    out = open(LOGS / f"uvicorn_{port}.out.log", "w", encoding="utf-8")
    err = open(LOGS / f"uvicorn_{port}.err.log", "w", encoding="utf-8")
    # Le lanceur de rechargement lit sa configuration dans l'environnement.
    # ERP_LOG_FILE : l'ouvrier n'herite pas des descripteurs du superviseur
    # detache, on lui donne donc son propre fichier de logs.
    env = {
        **os.environ,
        "ERP_PORT": str(port),
        "ERP_HOST": "0.0.0.0",
        "ERP_RELOAD_DIRS": ",".join(RELOAD_DIRS),
        "ERP_LOG_FILE": str(LOGS / f"uvicorn_{port}.log"),
    }
    proc = subprocess.Popen(
        uvicorn_command(port, RELOAD),
        cwd=str(BACKEND),
        env=env,
        stdout=out, stderr=err,
        creationflags=CREATE_FLAGS,
        close_fds=True,
    )
    pids[str(port)] = proc.pid
    print(f"Port {port} : PID {proc.pid}")

# Trace des PIDs : permet à stop_servers.py d'arrêter aussi le superviseur
# du rechargement automatique (sinon il relance ses ouvriers).
STATE_FILE.write_text(
    json.dumps(
        {
            "reload": RELOAD,
            "reload_dirs": [str(BACKEND / d) for d in RELOAD_DIRS],
            "pids": pids,
            "started_at": datetime.now().isoformat(timespec="seconds"),
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"PIDs enregistres dans {STATE_FILE}")

# Attente / health check
for _ in range(30):
    time.sleep(2)
    alive = []
    for port in (8001, 8002):
        try:
            with urllib.request.urlopen(
                f"http://localhost:{port}/docs", timeout=3
            ) as r:
                alive.append(f"Port {port}: HTTP {r.status}")
        except Exception:
            alive.append(f"Port {port}: pas encore prêt")
    if all("HTTP" in a for a in alive):
        print("\n".join(alive))
        break
else:
    print("\n".join(alive))
    print("--- stderr 8001 ---")
    print((LOGS / "uvicorn_8001.err.log").read_text(encoding="utf-8",
                                                   errors="replace")[-2000:])
