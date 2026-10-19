"""
API Comptabilité — configuration fiscale et régimes d'imposition (Côte d'Ivoire).

Endpoints :
- GET  /api/v1/accounting/fiscal-regime      → lecture du régime actuel + alerte dépassement
- PUT  /api/v1/accounting/fiscal-regime      → mise à jour manuelle du régime
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.schemas import TaxRegimeRead, TaxRegimeUpdate
from app.modules.accounting.services.fiscal_regime import TaxRegimeService

router = APIRouter()


@router.get(
    "/fiscal-regime",
    response_model=TaxRegimeRead,
    summary="Lecture du régime fiscal de l'entreprise",
)
async def get_fiscal_regime(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("company", "view")),
):
    """Retourne le régime fiscal actuel, la suggestion de changement et
    si la TVA est bloquée pour ce régime."""
    service = TaxRegimeService(session)
    result = await service.get_tax_regime(company_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    return result


@router.put(
    "/fiscal-regime",
    response_model=TaxRegimeRead,
    summary="Mise à jour manuelle du régime fiscal",
)
async def update_fiscal_regime(
    body: TaxRegimeUpdate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("company", "edit")),
):
    """Définit manuellement le régime fiscal de l'entreprise.

    Aucun basculement automatique n'est appliqué ici.
    """
    service = TaxRegimeService(session)
    try:
        result = await service.update_tax_regime(company_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    # Persistance effective du changement manuel (le service ne fait qu'un flush)
    await session.commit()
    return result


@router.post(
    "/fiscal-regime/detect-ca",
    response_model=TaxRegimeRead,
    summary="Détection de dépassement de seuil CA (alerte uniquement)",
)
async def detect_ca_threshold(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("company", "view")),
    ca_annual_ttc: Decimal = Query(
        ...,
        description="Chiffre d'affaires annuel TTC en FCFA",
        gt=0,
    ),
):
    """Détecte si le CA annuel dépasse le seuil du régime actuel.

    - Ne bascule JAMAIS automatiquement
    - Définit `suggested_tax_regime` si dépassement
    - L'utilisateur doit valider manuellement le changement
    """
    service = TaxRegimeService(session)
    result = await service.detect_ca_threshold(company_id, ca_annual_ttc)
    if result is None:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")
    # Persistance de la suggestion (sans basculement automatique)
    await session.commit()
    return result


__all__ = ["router"]