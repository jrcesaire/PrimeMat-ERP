"""
Isolation multi-tenant — contexte « entreprise courante ».

Le contexte est défini par la dépendance d'authentification
(``get_current_user``) à partir de l'utilisateur authentifié :

- superadmin         → ``None``  (aucun filtre, voit tout)
- utilisateur simple → son ``company_id`` (source de vérité : la base)

Le listener SQLAlchemy (``database.py``) applique ensuite automatiquement
``WHERE company_id = ?`` sur toutes les requêtes SELECT des modèles métier,
empêchant toute fuite de données entre entreprises (y compris via
``session.get()``).
"""
from __future__ import annotations

from contextvars import ContextVar

_current_company_id: ContextVar[int | None] = ContextVar(
    "current_company_id", default=None
)

# Modèles exclus du filtrage automatique :
# - Role / Permission : partagés entre entreprises (rôles système, catalogues
#   de permissions) — les filtrer casserait le RBAC des autres tenants.
TENANT_EXCLUDED_MODELS: frozenset[str] = frozenset({"Permission", "Role"})


def set_current_company(company_id: int | None) -> None:
    """Définit l'entreprise du contexte d'exécution courant."""
    _current_company_id.set(company_id)


def get_current_company() -> int | None:
    """Retourne l'entreprise courante (``None`` = pas de filtrage)."""
    return _current_company_id.get()
