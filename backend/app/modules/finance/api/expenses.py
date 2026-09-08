"""API Finance — dépenses."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.finance.schemas import ExpenseCreate, ExpenseRead
from app.modules.finance.services.expense_service import ExpenseService

router = APIRouter()


@router.get("/expenses", response_model=list[ExpenseRead])
async def list_expenses(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("expense", "view")),
):
    service = ExpenseService(session)
    return await service.list_expenses(skip=skip, limit=limit)


@router.post("/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate,
    session: SessionDep,
    _: User = Depends(require_permission("expense", "create")),
):
    service = ExpenseService(session)
    return await service.create_expense(body)