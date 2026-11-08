"""API Paramétrage de paie : structures, catégories, règles, organismes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.schemas import (
    CategoryCreate,
    CategoryRead,
    ContributionRegisterCreate,
    ContributionRegisterRead,
    RuleCreate,
    RuleRead,
    RuleUpdate,
    StructureCreate,
    StructureRead,
)
from app.modules.payroll.services.structure_service import StructureService

router = APIRouter()


@router.get("/structures", response_model=list[StructureRead])
async def list_structures(
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "view")),
):
    """Structures de paie de l'entreprise (liste déroulante des salariés).

    La structure par défaut est créée à la demande si elle manque — le socle
    n'est semé qu'au bootstrap (base vide).
    """
    service = StructureService(session)
    await service.ensure_default(user.company_id)
    return await service.list_structures()


@router.post(
    "/structures", response_model=StructureRead, status_code=status.HTTP_201_CREATED
)
async def create_structure(
    body: StructureCreate,
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "edit")),
):
    try:
        return await StructureService(session).create_structure(body, user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/structures/{structure_id}/categories", response_model=list[CategoryRead])
async def list_categories(
    structure_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "view")),
):
    return await StructureService(session).list_categories(structure_id)


@router.post(
    "/structures/{structure_id}/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_category(
    structure_id: int,
    body: CategoryCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "edit")),
):
    try:
        return await StructureService(session).add_category(structure_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/structures/{structure_id}/rules", response_model=list[RuleRead])
async def list_rules(
    structure_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "view")),
):
    return await StructureService(session).list_rules(structure_id)


@router.post(
    "/rules", response_model=RuleRead, status_code=status.HTTP_201_CREATED
)
async def create_rule(
    body: RuleCreate,
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "edit")),
):
    """Crée une règle de paie (formule/condition validées au plus tôt)."""
    try:
        return await StructureService(session).add_rule(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/rules/{rule_id}", response_model=RuleRead)
async def update_rule(
    rule_id: int,
    body: RuleUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "edit")),
):
    try:
        return await StructureService(session).update_rule(rule_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/contribution-registers", response_model=list[ContributionRegisterRead])
async def list_registers(
    session: SessionDep,
    _: User = Depends(require_permission("payroll_structure", "view")),
):
    return await StructureService(session).list_registers()


@router.post(
    "/contribution-registers",
    response_model=ContributionRegisterRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_register(
    body: ContributionRegisterCreate,
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "edit")),
):
    try:
        return await StructureService(session).create_register(body, user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
