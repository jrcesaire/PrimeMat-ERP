"""
Contexte de location (tenant).

Fournit le contexte d'entreprise/agence courante.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.core.dependencies.auth import (
    get_current_active_user,
    get_current_company_id,
)
from app.core.models.user import User


class TenantContext:
    """
    Contexte multi-entreprise pour une requête.

    Contient :
    - ``company_id`` : entreprise courante
    - ``agency_id``  : agence courante (optionnel)
    - ``user``       : utilisateur authentifié
    """

    def __init__(
        self,
        company_id: int,
        user: User,
    ):
        self.company_id = company_id
        self.agency_id: int | None = user.agency_id
        self.user = user

    def __repr__(self) -> str:
        return (
            f"<TenantContext company={self.company_id} "
            f"agency={self.agency_id} user={self.user.email}>"
        )


async def get_tenant_context(
    current_user: User = Depends(get_current_active_user),
    company_id: int = Depends(get_current_company_id),
) -> TenantContext:
    """Dépendance FastAPI fournissant le contexte multi-entreprise."""
    return TenantContext(company_id=company_id, user=current_user)


TenantDep = Any  # type: ignore[type-arg]
