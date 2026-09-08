"""
Utilitaires partagés.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Retourne la date/heure UTC actuelle."""
    return datetime.now(tz=timezone.utc)


def generate_uuid() -> str:
    """Génère un UUID4 sous forme de chaîne."""
    return str(uuid.uuid4())


def to_snake_case(name: str) -> str:
    """Convertit un nom CamelCase en snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(name: str) -> str:
    """Convertit un nom snake_case en camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def format_phone(phone: str) -> str:
    """Normalise un numéro de téléphone."""
    return re.sub(r"[^\d\+\#]", "", phone)
