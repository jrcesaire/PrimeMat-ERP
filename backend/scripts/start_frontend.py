"""Démarre le serveur Next.js (port 3000) de façon détachée."""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if not (FRONTEND / "package.json").exists():
    # Fallback : résout le dossier frontend voisin du backend
    FRONTEND = Path(__file__).resolve().parents[1].parent / "frontend"
print("Frontend :", FRONTEND)
print("Existe   :", (FRONTEND / "package.json").exists())


def kill_port_listener(port: int) -> None:
    """Tue le processus qui écoute déjà sur le port (sinon le bind échoue)."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True).stdout
    out = out.decode("utf-8", errors="replace")
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}"):
            pid = parts[-1]
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
            print(f"Processus {pid} arrêté (port {port})")
    time.sleep(2)


kill_port_listener(3000)

npm = "npm.cmd" if sys.platform == "win32" else "npm"
flags = 0
if sys.platform == "win32":
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

LOGS = Path(__file__).resolve().parents[1] / "logs"
LOGS.mkdir(exist_ok=True)

proc = subprocess.Popen(
    [npm, "run", "dev"],
    cwd=str(FRONTEND),
    stdout=open(LOGS / "next_3000.out.log", "w", encoding="utf-8"),
    stderr=open(LOGS / "next_3000.err.log", "w", encoding="utf-8"),
    creationflags=flags,
    close_fds=True,
)
print(f"Frontend : PID {proc.pid}")

for _ in range(45):
    time.sleep(2)
    try:
        with urllib.request.urlopen("http://localhost:3000", timeout=3) as r:
            print(f"Port 3000 : HTTP {r.status}")
            break
    except urllib.error.HTTPError as e:
        print(f"Port 3000 : HTTP {e.code}")
        break
    except Exception:
        pass
else:
    print("Port 3000 : pas prêt après 90 s — voir backend/logs/next_3000.err.log")
    err = (LOGS / "next_3000.err.log").read_text(encoding="utf-8",
                                                 errors="replace")
    print(err[-2000:])
