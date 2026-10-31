"""
API Routes Session de Caisse (PosSession) — Point de Vente.

    GET    /pos/sessions
    GET    /pos/sessions/{session_id}
    POST   /pos/sessions
    POST   /pos/sessions/{session_id}/close
    PUT    /pos/sessions/{session_id}
    GET    /pos/sessions/{session_id}/close-report
    POST   /pos/sessions/auto-close (cron / admin)

Chemins relatifs : le routeur est monté par le module Ventes sous le
préfixe ``/sales`` → URL finales ``/api/v1/sales/pos/sessions…``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.modules.sales.schemas import (
    PosSessionClose,
    PosSessionCloseReport,
    PosSessionCreate,
    PosSessionRead,
    PosSessionUpdate,
)
from app.modules.sales.services.pos_session_service import (
    PosSessionService,
    SETTING_POS_ACCOUNTING_WRITEUP_HOUR,
    SETTING_POS_CLOSING_HOUR,
)

router = APIRouter()

# Permissions
require_view = require_permission("pos", "view")
require_create = require_permission("pos", "create")
require_edit = require_permission("pos", "edit")
require_close = require_permission("pos", "close")


# ------------------------------------------------------------------ #
# Listing / consultation
# ------------------------------------------------------------------ #


@router.get("/pos/sessions")
async def list_pos_sessions(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    _: None = Depends(require_view),
):
    """Liste paginée des sessions de caisse de l'entreprise courante."""
    service = PosSessionService(session)
    sessions = await service.list_sessions(
        company_id=current_user.company_id, skip=skip, limit=limit
    )
    total = await service.count_sessions(current_user.company_id)
    items = [PosSessionRead.model_validate(s) for s in sessions]
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total,
    }


@router.get("/pos/sessions/{session_id}", response_model=PosSessionRead)
async def get_pos_session(
    session_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = PosSessionService(session)
    pos_session = await service.get_session(session_id)
    if pos_session is None:
        raise HTTPException(status_code=404, detail="Session de caisse introuvable.")
    return pos_session


# ------------------------------------------------------------------ #
# Création / mise à jour
# ------------------------------------------------------------------ #


@router.post(
    "/pos/sessions",
    response_model=PosSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_pos_session(
    body: PosSessionCreate,
    session: SessionDep,
    current_user = Depends(get_current_active_user),
    _: None = Depends(require_create),
):
    service = PosSessionService(session)
    try:
        pos_session = await service.open_session(
            company_id=current_user.company_id,
            user_id=current_user.id,
            data=body,
        )
    except ValueError as exc:
        # Erreur métier (ex. session déjà ouverte) → 400, pas un 500.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return pos_session


@router.put("/pos/sessions/{session_id}", response_model=PosSessionRead)
async def update_pos_session(
    session_id: int,
    body: PosSessionUpdate,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = PosSessionService(session)
    try:
        pos_session = await service.update_session(session_id, body)
    except ValueError as exc:
        # Seule une session ouverte peut être modifiée → 400.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if pos_session is None:
        raise HTTPException(status_code=404, detail="Session de caisse introuvable.")
    return pos_session


# ------------------------------------------------------------------ #
# Clôture
# ------------------------------------------------------------------ #


@router.post(
    "/pos/sessions/{session_id}/close", response_model=PosSessionRead
)
async def close_pos_session(
    session_id: int,
    body: PosSessionClose,
    session: SessionDep,
    current_user = Depends(get_current_active_user),
    _: None = Depends(require_close),
):
    service = PosSessionService(session)
    try:
        pos_session = await service.close_session(session_id, current_user.id, body)
    except ValueError as exc:
        # Session introuvable ou déjà clôturée → 400, pas un 500.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return pos_session


# ------------------------------------------------------------------ #
# Rapport de clôture
# ------------------------------------------------------------------ #


@router.get(
    "/pos/sessions/{session_id}/close-report",
    response_model=PosSessionCloseReport,
)
async def get_pos_session_close_report(
    session_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = PosSessionService(session)
    report = await service.get_close_report(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Session de caisse introuvable.")
    return report


# ------------------------------------------------------------------ #
# Clôture automatique (cron admin)
# ------------------------------------------------------------------ #


@router.post("/pos/sessions/auto-close")
async def auto_close_pos_sessions(
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = PosSessionService(session)
    closed_refs = await service.auto_close_sessions()
    if not closed_refs:
        return {"message": "Aucune session n'a été fermée (aucune session ouverte)."}
    return {"closed": closed_refs}

