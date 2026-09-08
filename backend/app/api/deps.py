"""
Dépendances partagées par les routeurs API.

Centralise l'accès à la session de base de données, l'authentification,
les permissions, ainsi que le contexte multi-entreprise.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.database import AsyncSession, get_session

# Session DB injectée dans les routes
SessionDep = Annotated[AsyncSession, Depends(get_session)]
