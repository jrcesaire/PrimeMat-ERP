"""Health check HTTP des serveurs + état du rechargement automatique."""
import json
import subprocess
import urllib.request
from pathlib import Path

PORTS = ((3000, "Frontend"), (8001, "Backend 1"), (8002, "Backend 2"))
LOGS = Path(__file__).resolve().parents[1] / "logs"
STATE_FILE = LOGS / "dev_state.json"

# Processus serveurs de l'ERP (repli si logs/dev_state.json est absent).
# Le nom du binaire dépend de l'installation Python : « python.exe »,
# « python3.11.exe » (Microsoft Store)... d'où le motif `python*`.
UVIICORN_QUERY = (
    "Get-CimInstance Win32_Process | "
    "Where-Object { $_.Name -like 'python*' -and ( "
    "$_.CommandLine -like '*dev_server.py*' -or ( "
    "$_.CommandLine -like '*uvicorn*' -and "
    "$_.CommandLine -like '*app.main:app*' ) ) } | "
    "ForEach-Object { $_.CommandLine }"
)


def uvicorn_cmdlines() -> list[str]:
    """Lignes de commande des processus uvicorn (vide si non détectables)."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             UVIICORN_QUERY],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in res.stdout.splitlines() if "uvicorn" in line]


def reload_status() -> str:
    """État du rechargement automatique du backend."""
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        if state:
            if state.get("reload"):
                return ("ACTIF (rechargement a chaud) - demarre le "
                        f"{state.get('started_at', '?')} : toute modification de "
                        "code est prise en compte sans redemarrage")
            return "INACTIF (serveurs lances sans rechargement)"
    lines = uvicorn_cmdlines()
    if not lines:
        return "inconnu (processus non detectes)"
    reloading = sum(1 for line in lines if "--reload" in line)
    if reloading == len(lines):
        return f"ACTIF (--reload) sur {reloading}/{len(lines)} processus"
    if reloading:
        return f"PARTIEL ({reloading}/{len(lines)} processus)"
    return "INACTIF - relancez Lancer-ERP.bat"


def main() -> None:
    for port, name in PORTS:
        try:
            with urllib.request.urlopen(
                f"http://localhost:{port}/", timeout=15
            ) as r:
                print(f"{name} (port {port}) : HTTP {r.status}")
        except Exception as e:
            print(f"{name} (port {port}) : ERREUR {e}")

    print(f"Backend  - rechargement automatique : {reload_status()}")
    print("Frontend - rechargement automatique : ACTIF (Next.js dev)")

    # Le code backend chargé contient-il bien les dernières routes ?
    try:
        with urllib.request.urlopen(
            "http://localhost:8001/api/v1/openapi.json", timeout=15
        ) as r:
            paths = json.load(r).get("paths", {})
        cle = "/api/v1/core/settings/sequences"
        etat = "present" if cle in paths else "ABSENT (backend non recharge)"
        print(f"Route {cle} : {etat}")
    except Exception as e:
        print(f"Verification du schema OpenAPI : ERREUR {e}")


if __name__ == "__main__":
    main()


