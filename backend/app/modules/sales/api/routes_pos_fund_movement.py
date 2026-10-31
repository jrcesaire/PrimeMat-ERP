"""
API Routes Journal des mouvements de fonds manuels (PosFundMovement) — Point de Vente.

    GET    /pos/fund-movements          — liste des mouvements d'une session / entreprise
    POST   /pos/fund-movements          — créer un mouvement de fonds

Chemins relatifs : montés par le module Ventes sous le préfixe ``/sales``
→ URL finales ``/api/v1/sales/pos/fund-movements``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.modules.sales.schemas import PosFundMovementCreate, PosFundMovementRead
from app.modules.sales.services.pos_fund_movement_service import PosFundMovementService

router = APIRouter()

# Permissions
require_view = require_permission("pos", "view")
require_create = require_permission("pos", "create")


@router.get("/pos/fund-movements")
async def list_pos_fund_movements(
    session: SessionDep,
    session_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    _: None = Depends(require_view),
):
    """Liste paginée des mouvements de fonds (session donnée ou entreprise)."""
    service = PosFundMovementService(session)
    movements = await service.list_fund_movements(
        company_id=current_user.company_id,
        session_id=session_id,
        skip=skip,
        limit=limit,
    )
    total = await service.count_fund_movements(
        company_id=current_user.company_id, session_id=session_id
    )
    items = [PosFundMovementRead.model_validate(m) for m in movements]
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total,
    }


@router.post(
    "/pos/fund-movements",
    response_model=PosFundMovementRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_pos_fund_movement(
    body: PosFundMovementCreate,
    session: SessionDep,
    current_user = Depends(get_current_active_user),
    _: None = Depends(require_create),
):
    service = PosFundMovementService(session)
    try:
        movement = await service.create_fund_movement(
            company_id=current_user.company_id,
            user_id=current_user.id,
            data=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return movement
