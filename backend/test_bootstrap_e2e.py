"""
Test end-to-end du bootstrap : login du premier admin via l'API réelle.

Surcharge DATABASE_URL → SQLite avant tout import, puis :
1. crée les tables (comme init_db en dev)
2. exécute le bootstrap (comme run_bootstrap_if_needed au démarrage)
3. teste POST /api/v1/core/auth/login + GET /me
"""
import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_bootstrap.db"
os.environ["BOOTSTRAP_ON_STARTUP"] = "true"
os.environ["FIRST_COMPANY_CODE"] = "ABC"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@abc.com"
os.environ["FIRST_ADMIN_PASSWORD"] = "Admin@12345"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

import logging

logging.disable(logging.INFO)  # réduit le bruit des logs SQL pendant le test


async def main() -> int:
    from httpx import ASGITransport, AsyncClient

    # Imports du canal : engine créé avec l'URL sqlite définie ci-dessus
    from app.core.database import Base, engine
    from app.core.services.seed_service import run_bootstrap_if_needed
    from app.main import app as fastapi_app

    import app.core.models  # noqa: F401  (enregistre les tables)
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    # 1. Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Bootstrap
    result = await run_bootstrap_if_needed()
    print("Bootstrap:", result)

    # 3. Login via l'API (sans lifespan — ASGITransport ne l'exécute pas)
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        print("Health:", health.status_code, health.json())

        login = await client.post(
            "/api/v1/core/auth/login",
            json={"email": "admin@abc.com", "password": "Admin@12345"},
        )
        print("Login status:", login.status_code)
        if login.status_code != 200:
            print("Login body:", login.json())
            return 1
        token = login.json().get("access_token")
        print("Token reçu:", bool(token))

        me = await client.get(
            "/api/v1/core/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        print("Me status:", me.status_code)
        me_body = me.json()
        print(
            "Me:", me_body.get("email"),
            "| roles:", [r["code"] for r in me_body.get("roles", [])],
        )

    await engine.dispose()
    p = os.path.join(BACKEND, "test_bootstrap.db")
    if os.path.exists(p):
        os.remove(p)

    print("E2E bootstrap+login OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))