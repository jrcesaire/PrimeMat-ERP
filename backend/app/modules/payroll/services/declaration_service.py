"""Service Déclarations de paie — bordereau CNPS et état ITS.

Agrège les bulletins d'une **période de paie** :
- bordereau CNPS : parts salariale et patronale, par organisme de cotisation ;
- état ITS : impôt retenu par salarié (net de la RICF).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payroll.models.contribution import ContributionRegister
from app.modules.payroll.models.period import PayrollPeriod
from app.modules.payroll.models.payslip import Payslip
from app.modules.payroll.models.structure import PayrollRule


class PayrollDeclarationService:
    """Déclarations sociales et fiscales d'une période."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _period(self, period_id: int) -> PayrollPeriod:
        period = await self.session.get(PayrollPeriod, period_id)
        if period is None:
            raise ValueError(f"Période {period_id} introuvable")
        return period

    async def _payslips(self, period_id: int) -> list[Payslip]:
        result = await self.session.execute(
            select(Payslip).where(Payslip.period_id == period_id)
        )
        return list(result.scalars().all())

    async def _register_map(self, company_id: int) -> dict[str, ContributionRegister]:
        result = await self.session.execute(
            select(PayrollRule).where(PayrollRule.company_id == company_id)
        )
        mapping: dict[str, ContributionRegister] = {}
        for rule in result.scalars().all():
            if rule.contribution_register is not None:
                mapping[rule.code] = rule.contribution_register
        return mapping

    @staticmethod
    def _period_dict(period: PayrollPeriod) -> dict:
        return {
            "id": period.id,
            "name": period.name,
            "date_start": str(period.date_start),
            "date_end": str(period.date_end),
            "payment_date": str(period.payment_date) if period.payment_date else None,
        }

    async def cnps_bordereau(self, company_id: int, period_id: int) -> dict:
        """Bordereau CNPS : base, part salariale, part patronale, par organisme."""
        period = await self._period(period_id)
        payslips = await self._payslips(period_id)
        reg_map = await self._register_map(company_id)

        base = sum(float(p.gross or 0) for p in payslips)
        employee_total = 0.0
        employer_total = 0.0
        registers: dict[str, dict] = {}

        for payslip in payslips:
            for line in payslip.lines:
                category = (line.category_code or "").upper()
                if category not in ("COTIS", "PATRONAL"):
                    continue
                amount = float(line.total or 0)
                register = reg_map.get(line.code)
                key = register.code if register else "AUTRES"
                entry = registers.setdefault(
                    key,
                    {
                        "code": key,
                        "name": register.name if register else "Autres organismes",
                        "employee": 0.0,
                        "employer": 0.0,
                    },
                )
                if category == "COTIS":
                    employee_total += amount
                    entry["employee"] += amount
                else:
                    employer_total += amount
                    entry["employer"] += amount

        register_lines = [
            {
                "code": v["code"],
                "name": v["name"],
                "employee": round(v["employee"], 2),
                "employer": round(v["employer"], 2),
                "total": round(v["employee"] + v["employer"], 2),
            }
            for v in registers.values()
        ]

        return {
            "period": self._period_dict(period),
            "employee_count": len(payslips),
            "base": round(base, 2),
            "employee_total": round(employee_total, 2),
            "employer_total": round(employer_total, 2),
            "grand_total": round(employee_total + employer_total, 2),
            "registers": register_lines,
        }

    async def its_declaration(self, company_id: int, period_id: int) -> dict:
        """État ITS : impôt retenu par salarié (net de la RICF)."""
        period = await self._period(period_id)
        payslips = await self._payslips(period_id)
        lines: list[dict] = []
        total = 0.0

        for payslip in sorted(payslips, key=lambda p: p.employee_id):
            its = sum(
                float(line.total or 0)
                for line in payslip.lines
                if (line.category_code or "").upper() == "IMPOT"
            )
            total += its
            employee = payslip.employee
            lines.append(
                {
                    "employee_id": payslip.employee_id,
                    "employee": (
                        employee.full_name if employee else payslip.number
                    ),
                    "cnps_number": getattr(employee, "cnps_number", None),
                    "parts": float(getattr(employee, "tax_parts", 1) or 1),
                    "gross": round(float(payslip.gross or 0), 2),
                    "its": round(its, 2),
                }
            )

        return {
            "period": self._period_dict(period),
            "employee_count": len(payslips),
            "total_its": round(total, 2),
            "lines": lines,
        }
