"""Arrête les serveurs ERP (frontend 3000 + backends 8001/8002)."""
import subprocess
import time

PORTS = (3000, 8001, 8002)


def kill_listeners(ports: tuple[int, ...]) -> None:
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
    if not pids:
        print("Aucun serveur en cours.")
        return
    for pid in sorted(pids):
        res = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                             capture_output=True)
        status = "arrêté" if res.returncode == 0 else "échec d'arrêt"
        print(f"Processus {pid} : {status}")
    time.sleep(2)


if __name__ == "__main__":
    kill_listeners(PORTS)
