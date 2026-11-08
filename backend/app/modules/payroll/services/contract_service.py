"""Service Contrats — cycle de vie des contrats de travail."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.services.sequence_service import SequenceService
from app.modules.payroll.models.contract import ContractAdvantage, PayrollContract
from app.modules.payroll.schemas import (
    AdvantageCreate,
    ContractCreate,
    ContractUpdate,
)
from app.shared.enums import ContractState


class ContractService:
    """Gestion des contrats de travail."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def list(
        self, skip: int = 0, limit: int = 100, employee_id: int | None = None
    ) -> list[PayrollContract]:
        stmt = select(PayrollContract).options(
            # Liste : relations non nécessaires au schéma de lecture.
            noload(PayrollContract.structure),
            noload(PayrollContract.advantages),
            noload(PayrollContract.employee),
        )
        if employee_id is not None:
            stmt = stmt.where(PayrollContract.employee_id == employee_id)
        result = await self.session.execute(
            stmt.order_by(PayrollContract.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, contract_id: int) -> PayrollContract | None:
        return await self.session.get(PayrollContract, contract_id)

    async def create(self, data: ContractCreate) -> PayrollContract:
        from app.modules.payroll.models.employee import Employee
        from app.modules.payroll.models.structure import PayrollStructure

        employee = await self.session.get(Employee, data.employee_id)
        if employee is None:
            raise ValueError(f"Employé {data.employee_id} introuvable")
        structure = await self.session.get(PayrollStructure, data.structure_id)
        if structure is None:
            raise ValueError(f"Structure de paie {data.structure_id} introuvable")
        if float(data.wage) < 0:
            raise ValueError("Le salaire de base ne peut pas être négatif")

        reference = data.reference or await self.sequences.next_value(
            "payroll_contract", "CTR"
        )
        contract = PayrollContract(
            reference=reference,
            employee_id=data.employee_id,
            structure_id=data.structure_id,
            date_start=data.date_start or date.today(),
            date_end=data.date_end,
            job_title=data.job_title,
            wage=data.wage,
            wage_type=data.wage_type,
            work_rate=data.work_rate,
            currency_code=data.currency_code,
            state=ContractState.DRAFT.value,
            company_id=employee.company_id,
        )
        self.session.add(contract)
        await self.session.commit()
        await self.session.refresh(contract)
        return contract

    async def update(
        self, contract_id: int, data: ContractUpdate
    ) -> PayrollContract:
        contract = await self.get(contract_id)
        if contract is None:
            raise ValueError(f"Contrat {contract_id} introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "wage" and value is not None and float(value) < 0:
                raise ValueError("Le salaire de base ne peut pas être négatif")
            setattr(contract, field, value)
        await self.session.commit()
        await self.session.refresh(contract)
        return contract

    async def open(self, contract_id: int) -> PayrollContract:
        """Ouvre un contrat (draft → open)."""
        contract = await self.get(contract_id)
        if contract is None:
            raise ValueError(f"Contrat {contract_id} introuvable")
        contract.state = ContractState.OPEN.value
        await self.session.commit()
        await self.session.refresh(contract)
        return contract

    async def add_advantage(
        self, contract_id: int, data: AdvantageCreate
    ) -> ContractAdvantage:
        contract = await self.get(contract_id)
        if contract is None:
            raise ValueError(f"Contrat {contract_id} introuvable")
        advantage = ContractAdvantage(
            contract_id=contract_id,
            name=data.name,
            rule_code=data.rule_code,
            amount=data.amount,
            is_taxable=data.is_taxable,
            company_id=contract.company_id,
        )
        self.session.add(advantage)
        await self.session.commit()
        await self.session.refresh(advantage)
        return advantage
