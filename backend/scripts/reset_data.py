"""
Réinitialisation des données métier — environnement vierge.

Supprime TOUTES les données métier (devis, commandes, factures, paiements,
produits, clients, mouvements de stock, écritures, dépenses, audit...)
en conservant les référentiels :
- utilisateurs, rôles, permissions
- entreprises, agences
- devises, taxes, paramètres, modules
- catégories et unités de produits, plan comptable OHADA + journaux

Les séquences de numérotation sont remises à zéro (prochain document = 0001)
et `cgv_content` est réinitialisé.

Usage :
    python scripts/reset_data.py [--db CHEMIN] [--yes]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Tables conservées (référentiels)
KEEP: set[str] = {
    # Socle
    "alembic_version",
    "users", "companies", "agencies",
    "roles", "permissions", "roles_permissions", "users_roles",
    "currencies", "company_currencies", "taxes",
    "settings", "sequences", "module_info",
    # Référentiels catalogue
    "product_categories", "product_units", "unit_conversions",
    # Comptabilité : plan OHADA + journaux (référentiels)
    "accounts", "journals", "fiscal_years",
}

# Colonnes de séquence remises à zéro
RESET_SETTINGS = {"cgv_content": ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(BACKEND_DIR / "erp_dev.db"))
    parser.add_argument("--yes", action="store_true", help="Sans confirmation")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Base introuvable : {db_path}")
        return 1

    # Import des modèles pour connaître toutes les tables du projet
    import app.core.models  # noqa: F401  (référentiels du core)
    from app.core.database import Base

    try:  # modules métier — import tolerant
        import app.core.modules  # noqa: F401  (registre des modules)
        from app.main import app  # noqa: F401  (charge tous les routeurs/modèles)
    except Exception as exc:  # noqa: BLE001
        print(f"(Import partiel : {exc!r} — on continue avec les modèles chargés)")

    all_tables = {t for t in Base.metadata.tables}
    # Vérifie que les tables du KEEP existent bien
    to_delete = sorted(all_tables - KEEP)

    conn = sqlite3.connect(str(db_path))
    existing = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    targets = [t for t in to_delete if t in existing]

    if not args.yes:
        print(f"Base : {db_path}")
        print(f"Tables conservées : {len(KEEP & existing)}")
        print(f"Tables à vider    : {len(targets)}")
        for t in targets:
            n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            if n:
                print(f"  - {t}: {n} ligne(s)")
        if input("Confirmer la purge ? [oui/N] ").strip().lower() not in (
            "oui", "o", "y",
        ):
            print("Annulé.")
            return 1

    conn.execute("PRAGMA foreign_keys = OFF")
    total = 0
    for t in targets:
        n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        if n:
            conn.execute(f"DELETE FROM [{t}]")
            total += n
    # Séquences → prochaine numérotation à 1
    if "sequences" in existing:
        conn.execute("UPDATE sequences SET last_number = 0")
    # Paramètres de test réinitialisés
    if "settings" in existing:
        for key, value in RESET_SETTINGS.items():
            conn.execute(
                "UPDATE settings SET value = ? WHERE key = ?", (value, key)
            )
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    print(f"✅ Purge terminée : {total} ligne(s) supprimée(s).")
    print("Les comptes utilisateurs, rôles, devises, taxes et le plan "
          "comptable sont conservés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
