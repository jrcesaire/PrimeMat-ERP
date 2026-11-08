"""API Employés du module Paie."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.modules.payroll.services.employee_service import EmployeeService

router = APIRouter()


@router.get("/employees", response_model=list[EmployeeRead])
async def list_employees(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    _: User = Depends(require_permission("employee", "view")),
):
    """Registre du personnel (filtrable par nom / matricule)."""
    return await EmployeeService(session).list(skip=skip, limit=limit, search=search)


@router.post(
    "/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED
)
async def create_employee(
    body: EmployeeCreate,
    session: SessionDep,
    user: User = Depends(require_permission("employee", "create")),
):
    try:
        return await EmployeeService(session).create(body, user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("employee", "view")),
):
    employee = await EmployeeService(session).get(employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employé introuvable")
    return employee


@router.put("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("employee", "edit")),
):
    try:
        return await EmployeeService(session).update(employee_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("employee", "delete")),
):
    try:
        await EmployeeService(session).delete(employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
