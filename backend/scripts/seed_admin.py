"""
Script CLI — crée les données de démarrage manuellement.

Usage :
    cd backend
    python -m scripts.seed_admin            # utilise la config .env
    python -m scripts.seed_admin --reset-password admin@abc.com NouveauMdp123

Idempotent : ne crée rien si les données existent déjà.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Console Windows : force l'UTF-8 pour les caractères spéciaux
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Permet l'exécution directe depuis backend/
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)


async def reset_password(email: str, new_password: str) -> int:
    """Réinitialise le mot de passe d'un utilisateur."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.models.user import User
    from app.core.security import hash_password

    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.email == email.lower())
        )).scalar_one_or_none()
        if user is None:
            print(f"✗ Utilisateur introuvable : {email}")
            return 1
        user.password_hash = hash_password(new_password)
        await session.commit()
        print(f"✓ Mot de passe réinitialisé pour {email}")
        return 0


async def run_seed() -> int:
    """Exécute le bootstrap des données de démarrage."""
    # Importe TOUS les modèles pour résoudre les relations inter-modules
    import app.core.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    from app.core.services.seed_service import bootstrap_defaults
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        created = await bootstrap_defaults(session)

        if not any(created.values()):
            print("ℹ Rien à créer — les données de démarrage existent déjà.")
            return 0

        print("✓ Données créées :")
        if created["currencies"]:
            print(f"  Devises      : {', '.join(created['currencies'])}")
        if created["companies"]:
            print(f"  Entreprises  : {', '.join(created['companies'])}")
        if created["agencies"]:
            print(f"  Agences      : {', '.join(created['agencies'])}")
        if created["perms"]:
            print(f"  Permissions  : {len(created['perms'])} créées")
        if created["roles"]:
            print(f"  Rôles        : {', '.join(created['roles'])}")
        if created["users"]:
            print(f"  Admin        : {', '.join(created['users'])}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed / administration du ERP")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("seed", help="Crée les données de démarrage (défaut)")

    rp = sub.add_parser("reset-password", help="Réinitialise un mot de passe")
    rp.add_argument("email", help="Email de l'utilisateur")
    rp.add_argument("password", help="Nouveau mot de passe (min. 8 caractères)")

    args = parser.parse_args()

    if args.command == "reset-password":
        if len(args.password) < 8:
            print("✗ Le mot de passe doit contenir au moins 8 caractères.")
            return 1
        return asyncio.run(reset_password(args.email, args.password))

    # Défaut : seed
    return asyncio.run(run_seed())


if __name__ == "__main__":
    sys.exit(main())