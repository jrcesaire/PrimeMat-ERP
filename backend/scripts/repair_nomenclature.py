"""Répare ``doc_nomenclature`` sans perdre les règles encore valides.

Usage (depuis n'importe quel répertoire)::

    python backend/scripts/repair_nomenclature.py
    python backend/scripts/repair_nomenclature.py --db /chemin/erp_dev.db

Une sauvegarde SQLite cohérente est créée avant toute écriture. La configuration
réparée fusionne, dans cet ordre : les défauts, les règles déduites des compteurs
existants pour les modèles absents, puis les surcharges stockées valides.
"""

from __future__ import annotations

import argparse
import copy
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.services.setting_service import DEFAULT_SETTINGS, as_mapping  # noqa: E402

SequenceRow = Iterable[tuple[str, str | None, int | None, str | None, str | None]]


def build_effective_config(raw: object, sequence_rows: SequenceRow) -> dict:
    """Construit une nomenclature complète, sérialisable une seule fois."""
    defaults = DEFAULT_SETTINGS["doc_nomenclature"]["value"]
    config = copy.deepcopy(defaults)

    # Certains compteurs historiques (achats, écritures…) n'existent pas dans
    # les défauts. Leur règle effective est conservée au lieu d'être perdue.
    for model, prefix, padding, reset, suffix in sequence_rows:
        if model in config:
            continue
        config[model] = {
            "prefix": prefix or model.upper(),
            "padding": padding or 6,
            "reset": reset or "never",
            "suffix_type": "custom" if suffix else "none",
            "suffix_custom": suffix or "",
        }

    # `as_mapping` accepte l'objet, la chaîne JSON et le double encodage ; il
    # rejette une map index→caractère. Seules les règles dict sont reprises.
    stored = as_mapping(raw)
    for model, rule in stored.items():
        if not isinstance(rule, dict):
            continue
        base = config.get(model, {})
        config[model] = {**(base if isinstance(base, dict) else {}), **rule}
    return config


def _sequence_rows(connection: sqlite3.Connection, company_id: int | None) -> list:
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "sequences" not in tables:
        return []
    sql = "SELECT model, prefix, number_padding, reset, suffix FROM sequences"
    params: tuple = ()
    if company_id is not None:
        sql += " WHERE company_id = ?"
        params = (company_id,)
    sql += " ORDER BY company_id, id"
    return list(connection.execute(sql, params))


def repair(database_path: Path) -> tuple[Path, int, int, int]:
    """Sauvegarde puis répare ; retourne sauvegarde, lignes, tailles avant/après."""
    if not database_path.is_file():
        raise FileNotFoundError(f"Base introuvable : {database_path}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = database_path.with_name(f"{database_path.name}.bak-nomenclature-{timestamp}")
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        backup = sqlite3.connect(backup_path)
        try:
            connection.backup(backup)
        finally:
            backup.close()

        rows = list(
            connection.execute(
                "SELECT id, company_id, value FROM settings "
                "WHERE key = 'doc_nomenclature' ORDER BY id"
            )
        )
        before_size = sum(len(row[2] or "") for row in rows)
        after_size = 0
        with connection:
            for setting_id, company_id, raw in rows:
                effective = build_effective_config(raw, _sequence_rows(connection, company_id))
                serialized = json.dumps(effective, ensure_ascii=False)
                after_size += len(serialized)
                connection.execute(
                    "UPDATE settings SET value = ?, type = 'json', "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (serialized, setting_id),
                )
        return backup_path, len(rows), before_size, after_size
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=BACKEND / "erp_dev.db")
    args = parser.parse_args()
    backup, count, before, after = repair(args.db.resolve())
    print(f"Sauvegarde : {backup}")
    print(f"Nomenclatures réparées : {count}")
    print(f"Taille JSON : {before} -> {after} caractères")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
