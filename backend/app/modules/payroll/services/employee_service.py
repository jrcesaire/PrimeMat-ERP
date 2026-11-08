"""Service du personnel — CRUD des employés."""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.services.sequence_service import SequenceService
from app.modules.payroll.models.employee import Employee
from app.modules.payroll.schemas import EmployeeCreate, EmployeeUpdate
from app.shared.enums import EmployeeStatus


def derive_tax_parts(marital_status: str | None, dependents: int | None) -> float:
    """Parts fiscales (barème ITS/IGR) — tableau officiel ivoirien.

    - célibataire / divorcé / veuf **sans** enfant : 1 part ;
    - célibataire / divorcé **avec** enfant(s) : 1,5 part (pour lui-même) ;
    - marié / veuf (chef de famille) : 2 parts ;
    - **+ 0,5 part par enfant à charge** — plafonné à 5 parts.
    """
    status = (marital_status or "single").lower()
    children = int(dependents or 0)
    if status in ("married", "widowed"):
        base = 2.0
    elif children > 0:
        base = 1.5
    else:
        base = 1.0
    return min(base + 0.5 * children, 5.0)


class EmployeeService:
    """Gestion du registre du personnel."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self, skip: int = 0, limit: int = 100, search: str | None = None
    ) -> list[Employee]:
        stmt = select(Employee).options(
            # Liste : les relations ne sont pas nécessaires (schéma de lecture).
            noload(Employee.contracts),
            noload(Employee.partner),
        )
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Employee.last_name.ilike(like),
                    Employee.first_name.ilike(like),
                    Employee.reference.ilike(like),
                )
            )
        result = await self.session.execute(
            stmt.order_by(Employee.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, employee_id: int) -> Employee | None:
        return await self.session.get(Employee, employee_id)

    async def create(self, data: EmployeeCreate, company_id: int) -> Employee:
        payload = data.model_dump()
        contract_payload = payload.pop("contract", None) or {}
        if payload.get("tax_parts") is None:
            payload["tax_parts"] = derive_tax_parts(
                payload.get("marital_status"), payload.get("dependents")
            )
        employee = Employee(
            **payload,
            company_id=company_id,
            status=EmployeeStatus.ACTIVE.value,
        )
        self.session.add(employee)
        await self.session.flush()

        # Contrat créé dans la foulée (paramètres de paie du salarié).
        if contract_payload.get("structure_id"):
            from app.modules.payroll.models.contract import PayrollContract

            reference = contract_payload.get("reference") or await SequenceService(
                self.session
            ).next_value("payroll_contract", "CTR")
            start = (
                contract_payload.get("date_start")
                or payload.get("hire_date")
                or date.today()
            )
            self.session.add(
                PayrollContract(
                    reference=reference,
                    employee_id=employee.id,
                    structure_id=contract_payload["structure_id"],
                    date_start=start,
                    job_title=contract_payload.get("job_title")
                    or payload.get("job_title"),
                    wage=contract_payload.get("wage", 0),
                    wage_type=contract_payload.get("wage_type", "monthly"),
                    work_rate=contract_payload.get("work_rate", 100),
                    state="open",
                    company_id=company_id,
                )
            )

        await self.session.commit()
        await self.session.refresh(employee)
        return employee

    async def update(self, employee_id: int, data: EmployeeUpdate) -> Employee:
        employee = await self.get(employee_id)
        if employee is None:
            raise ValueError(f"Employé {employee_id} introuvable")
        changes = data.model_dump(exclude_unset=True)
        # Recale les parts fiscales si la situation familiale change et que
        # l'utilisateur n'a pas fixé explicitement tax_parts.
        if "tax_parts" not in changes and (
            "marital_status" in changes or "dependents" in changes
        ):
            changes["tax_parts"] = derive_tax_parts(
                changes.get("marital_status", employee.marital_status),
                changes.get("dependents", employee.dependents),
            )
        for field, value in changes.items():
            setattr(employee, field, value)
        await self.session.commit()
        await self.session.refresh(employee)
        return employee

    async def delete(self, employee_id: int) -> None:
        employee = await self.get(employee_id)
        if employee is None:
            raise ValueError(f"Employé {employee_id} introuvable")
        await self.session.delete(employee)
        await self.session.commit()
