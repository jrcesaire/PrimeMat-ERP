"""API Contrats de travail et avantages en nature."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.schemas import (
    AdvantageCreate,
    AdvantageRead,
    ContractCreate,
    ContractRead,
    ContractUpdate,
)
from app.modules.payroll.services.contract_service import ContractService

router = APIRouter()


@router.get("/contracts", response_model=list[ContractRead])
async def list_contracts(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    employee_id: int | None = None,
    _: User = Depends(require_permission("contract", "view")),
):
    return await ContractService(session).list(
        skip=skip, limit=limit, employee_id=employee_id
    )


@router.post(
    "/contracts", response_model=ContractRead, status_code=status.HTTP_201_CREATED
)
async def create_contract(
    body: ContractCreate,
    session: SessionDep,
    _: User = Depends(require_permission("contract", "create")),
):
    try:
        return await ContractService(session).create(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/contracts/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("contract", "view")),
):
    contract = await ContractService(session).get(contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    return contract


@router.put("/contracts/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: int,
    body: ContractUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("contract", "edit")),
):
    try:
        return await ContractService(session).update(contract_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/contracts/{contract_id}/open", response_model=ContractRead)
async def open_contract(
    contract_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("contract", "edit")),
):
    """Ouvre un contrat (draft → open) : il devient payable."""
    try:
        return await ContractService(session).open(contract_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/contracts/{contract_id}/advantages",
    response_model=AdvantageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_advantage(
    contract_id: int,
    body: AdvantageCreate,
    session: SessionDep,
    _: User = Depends(require_permission("contract", "edit")),
):
    try:
        return await ContractService(session).add_advantage(contract_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
