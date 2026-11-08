"""Arrête les serveurs ERP (frontend 3000 + backends 8001/8002).

Le rechargement automatique (``uvicorn --reload``) fait tourner **deux**
processus par port : un superviseur qui surveille les fichiers et l'ouvrier
qui sert les requêtes. Tuer seulement celui qui écoute le port laisserait
l'autre vivant (le superviseur relancerait l'ouvrier, ou l'ouvrier garderait
le port). Les deux sont donc arrêtés : par ligne de commande, puis par port.
"""
import json
import subprocess
import time
from pathlib import Path

PORTS = (3000, 8001, 8002)
LOGS = Path(__file__).resolve().parents[1] / "logs"
STATE_FILE = LOGS / "dev_state.json"

# Processus serveurs de l'ERP : superviseur du rechargement (dev_server.py)
# ou uvicorn lancé directement, plus les ouvriers.
# Le nom du binaire dépend de l'installation Python : « python.exe »,
# « python3.11.exe » (Microsoft Store)... d'où le motif `python*`.
UVIICORN_QUERY = (
    "Get-CimInstance Win32_Process | "
    "Where-Object { $_.Name -like 'python*' -and ( "
    "$_.CommandLine -like '*dev_server.py*' -or ( "
    "$_.CommandLine -like '*uvicorn*' -and "
    "$_.CommandLine -like '*app.main:app*' ) ) } | "
    "ForEach-Object { \"$($_.ProcessId)\" }"
)


def kill_script_processes() -> None:
    """Arrête les serveurs enregistrés par restart_servers.py (logs/dev_state.json)."""
    if not STATE_FILE.exists():
        print("Aucun PID enregistre (logs/dev_state.json absent).")
        return
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"logs/dev_state.json illisible : {exc}")
        return
    pids = sorted({int(pid) for pid in (state.get("pids") or {}).values()})
    if not pids:
        print("Aucun PID dans logs/dev_state.json.")
        return
    for pid in pids:
        # /T : arrête aussi l'ouvrier du rechargement automatique.
        out = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True
        )
        status = "arrêté" if out.returncode == 0 else "déjà arrêté"
        print(f"Processus uvicorn {pid} : {status}")


def kill_uvicorn_processes() -> None:
    """Arrête tous les processus uvicorn de l'ERP (superviseur --reload inclus)."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             UVIICORN_QUERY],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Recherche des processus uvicorn impossible : {exc}")
        return
    pids = sorted({int(part) for part in res.stdout.split() if part.isdigit()})
    if not pids:
        print("Aucun processus uvicorn en cours.")
        return
    for pid in pids:
        out = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True
        )
        status = "arrêté" if out.returncode == 0 else "déjà arrêté"
        print(f"Processus uvicorn {pid} : {status}")


def listening_pids(ports: tuple[int, ...]) -> dict[str, str]:
    """Associe l'adresse écoutée (``:8001``) au PID qui l'écoute."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True).stdout
    out = out.decode("utf-8", errors="replace")
    found: dict[str, str] = {}
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        for port in ports:
            if parts[1].endswith(f":{port}"):
                found[parts[1]] = parts[-1]
    return found


def kill_listeners(ports: tuple[int, ...]) -> None:
    found = listening_pids(ports)
    if not found:
        print("Aucun serveur en cours.")
        return
    for address, pid in sorted(found.items(), key=lambda item: item[1]):
        # /T : arrête aussi les enfants (ouvrier du rechargement, node de Next).
        res = subprocess.run(
            ["taskkill", "/PID", pid, "/T", "/F"], capture_output=True
        )
        status = "arrêté" if res.returncode == 0 else "échec d'arrêt"
        print(f"Processus {pid} ({address}) : {status}")
    time.sleep(2)


def wait_ports_free(ports: tuple[int, ...], timeout: float = 10.0) -> None:
    """Attend que tous les ports soient réellement libérés."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = listening_pids(ports)
        if not remaining:
            print("Ports libérés : " + ", ".join(str(p) for p in ports))
            return
        time.sleep(0.5)
    remaining = listening_pids(ports)
    print("!! ports encore occupés : " + ", ".join(sorted(remaining)))


if __name__ == "__main__":
    kill_script_processes()
    kill_uvicorn_processes()
    kill_listeners(PORTS)
    wait_ports_free(PORTS)
    if STATE_FILE.exists():
        STATE_FILE.unlink(missing_ok=True)
        print("Etat des PID efface (logs/dev_state.json).")

