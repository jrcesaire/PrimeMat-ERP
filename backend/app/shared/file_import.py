"""
Lecture de fichiers Excel / CSV pour les imports en masse.

- ``.xlsx`` / ``.xlsm`` : lu avec openpyxl (première feuille, valeurs
  calculées), sans dépendance à pandas.
- ``.csv`` : encodage détecté (utf-8-sig, puis cp1252), séparateur
  détecté parmi ``;  ,  tab``.

Les en-têtes sont normalisés (minuscules, accents retirés, espaces et
tirets remplacés par ``_``) pour tolerer « Prix d'achat », « prix_achat »...
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from typing import Any

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}


def normalize_header(raw: Any) -> str:
    """« Prix d'achat HT » → ``prix_d_achat_ht``."""
    text = str(raw or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text.strip("_")


def read_rows_from_bytes(filename: str, content: bytes) -> list[dict[str, Any]]:
    """Retourne les lignes du fichier sous forme de dictionnaires
    (clé = en-tête normalisé, valeur = cellule brute)."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in {"xlsx", "xlsm", "csv"}:
        raise HTTPException(
            400, "Format non supporté — utilisez un fichier .xlsx ou .csv"
        )

    if suffix == "csv":
        rows = _read_csv(content)
    else:
        rows = _read_xlsx(content)

    if not rows:
        raise HTTPException(400, "Fichier vide (aucune ligne d'en-tête trouvée).")

    headers = [normalize_header(h) for h in rows[0]]
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(rows[1:], start=2):
        if all(v is None or str(v).strip() == "" for v in raw):
            continue  # ligne vide
        rec: dict[str, Any] = {"__line__": line_no}
        for i, key in enumerate(headers):
            if key:
                rec[key] = raw[i] if i < len(raw) else None
        records.append(rec)
    return records


def _read_csv(content: bytes) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("latin-1", errors="replace")

    sample = text[:4096]
    delimiter = max(
        (";", ",", "\t", "|"), key=lambda d: sample.count(d)
    ) if sample else ";"
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [row for row in reader]


def _read_xlsx(content: bytes) -> list[list[Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            500, "Lecture Excel indisponible (openpyxl manquant sur le serveur)"
        ) from exc

    try:
        wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Fichier Excel illisible : {exc}") from exc

    ws = wb.worksheets[0]
    rows: list[list[Any]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append(list(row))
        if len(rows) > 5000:
            break  # garde-fou anti-fichier géant
    wb.close()
    return rows


# ------------------------------------------------------------------ #
# Convertisseurs tolérants
# ------------------------------------------------------------------ #
def to_float(value: Any, default: float | None = None) -> float | None:
    if value is None or str(value).strip() == "":
        return default
    try:
        text = str(value).strip().replace(" ", "").replace(",", ".")
        return float(text)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int | None = None) -> int | None:
    f = to_float(value)
    return int(f) if f is not None else default


def to_date(value: Any):
    """Accepte ISO (2024-05-31), JJ/MM/AAAA et datetime Excel (openpyxl)."""
    if value is None or str(value).strip() == "":
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        from datetime import date as _date

        if hasattr(value, "date"):
            return value.date()
        return _date(value.year, value.month, value.day)
    text = str(value).strip()
    from datetime import date, datetime

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "oui", "yes", "vrai", "o", "y")


def clean_str(value: Any, max_len: int | None = None) -> str | None:
    text = str(value).strip() if value is not None else None
    if text == "":
        return None
    if max_len and text and len(text) > max_len:
        text = text[:max_len]
    return text
