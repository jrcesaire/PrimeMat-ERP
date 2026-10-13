"""Health check HTTP des 3 serveurs."""
import urllib.request

for port, name in ((3000, "Frontend"), (8001, "Backend 1"), (8002, "Backend 2")):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/", timeout=15) as r:
            print(f"{name} (port {port}) : HTTP {r.status}")
    except Exception as e:
        print(f"{name} (port {port}) : ERREUR {e}")
