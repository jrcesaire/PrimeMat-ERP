"""Redémarre les serveurs uvicorn (8001/8002) de façon détachée."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
LOGS = BACKEND / "logs"
LOGS.mkdir(exist_ok=True)
PORTS = (8001, 8002)


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

for port in PORTS:
    out = open(LOGS / f"uvicorn_{port}.out.log", "w", encoding="utf-8")
    err = open(LOGS / f"uvicorn_{port}.err.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=str(BACKEND),
        stdout=out, stderr=err,
        creationflags=CREATE_FLAGS,
        close_fds=True,
    )
    print(f"Port {port} : PID {proc.pid}")

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
