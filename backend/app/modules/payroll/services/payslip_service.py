"""Service de paie — bulletins, lots, moteur de calcul et workflow.

Le calcul (``compute_sheet``) reprend la logique d'``hr.payslip.compute_sheet``
d'OCA/payroll : les règles de la structure sont évaluées séquentiellement par
``sequence``, chaque résultat alimentant les variables des règles suivantes.
La comptabilisation est déléguée à ``PostingService.post_payslip`` (module
comptabilité), de façon **idempotente** (``source_type="payslip"``).
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.services.sequence_service import SequenceService
from app.modules.payroll.models.contract import PayrollContract
from app.modules.payroll.models.period import PayrollPeriod, PayrollRun
from app.modules.payroll.models.payslip import (
    Payslip,
    PayslipInput,
    PayslipLine,
    PayslipWorkedDay,
)
from app.modules.payroll.models.structure import PayrollRule
from app.modules.payroll.services.rule_engine import (
    build_context,
    compute_amount,
    rule_applies,
)
from app.modules.payroll.services.settings_service import PayrollSettingsService
from app.shared.enums import ContractState, PayrollRunState, PayslipState

logger = logging.getLogger(__name__)

#: Codes de catégories qui composent le BRUT (gains).
EARNING_CODES = frozenset({"BASE", "PRIME", "GAIN", "GAINS"})
#: Codes de catégories de retenues sur le net (cotisations, impôts).
DEDUCTION_CODES = frozenset({"COTIS", "IMPOT"})
#: Codes de catégories de charges patronales (ajoutées au coût employeur).
PATRONAL_CODES = frozenset({"PATRONAL", "PATRON"})


class PayslipService:
    """Orchestration du traitement de paie."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    # ------------------------------------------------------------------ #
    # Consultation
    # ------------------------------------------------------------------ #
    async def list_payslips(
        self,
        skip: int = 0,
        limit: int = 100,
        run_id: int | None = None,
        employee_id: int | None = None,
        with_relations: bool = False,
    ) -> list[Payslip]:
        """Bulletins (plus récents d'abord).

        ``with_relations=False`` (défaut) évite de charger lignes, éléments
        variables, jours et tiers : inutile pour une liste (schéma de lecture),
        coûteux sur un lot de plusieurs centaines de bulletins.
        """
        relations = (
            Payslip.lines, Payslip.inputs, Payslip.worked_days,
            Payslip.contract, Payslip.employee, Payslip.structure,
        )
        stmt = select(Payslip).options(
            *(selectinload(r) for r in relations)
            if with_relations
            else (*(noload(r) for r in relations),)
        )
        if run_id is not None:
            stmt = stmt.where(Payslip.run_id == run_id)
        if employee_id is not None:
            stmt = stmt.where(Payslip.employee_id == employee_id)
        result = await self.session.execute(
            stmt.order_by(Payslip.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, payslip_id: int) -> Payslip | None:
        return await self.session.get(Payslip, payslip_id)

    async def _load_rich(self, payslip_id: int) -> Payslip | None:
        """Charge un bulletin **avec ses relations**.

        Indispensable en async : ``session.get`` ne rejoue pas les chargeurs
        ``selectin`` lorsque l'objet est déjà dans la session (cas d'un bulletin
        tout juste créé) — y accéder ensuite lèverait ``MissingGreenlet``.
        """
        result = await self.session.execute(
            select(Payslip)
            .options(
                selectinload(Payslip.lines),
                selectinload(Payslip.inputs),
                selectinload(Payslip.worked_days),
                selectinload(Payslip.contract),
                selectinload(Payslip.employee),
                selectinload(Payslip.structure),
            )
            .where(Payslip.id == payslip_id)
            # ``populate_existing`` force le rafraîchissement des collections
            # déjà chargées : sans lui, un élément variable ajouté puis un
            # recalcul dans la même session ne seraient pas repris (la
            # collection ``inputs`` resterait celle chargée avant l'ajout).
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Création d'un bulletin / d'un lot
    # ------------------------------------------------------------------ #
    async def create_payslip(
        self,
        contract_id: int,
        date_from: date,
        date_to: date,
        run_id: int | None = None,
        period_id: int | None = None,
        payment_date: date | None = None,
    ) -> Payslip:
        contract = await self.session.get(PayrollContract, contract_id)
        if contract is None:
            raise ValueError(f"Contrat {contract_id} introuvable")
        if contract.state == ContractState.CANCELLED.value:
            raise ValueError("Impossible de payer un contrat annulé")

        number = await self.sequences.next_value("payslip", "PAIE")
        payslip = Payslip(
            run_id=run_id,
            period_id=period_id,
            number=number,
            employee_id=contract.employee_id,
            contract_id=contract.id,
            structure_id=contract.structure_id,
            date_from=date_from,
            date_to=date_to,
            payment_date=payment_date,
            state=PayslipState.DRAFT.value,
            company_id=contract.company_id,
        )
        self.session.add(payslip)
        await self.session.flush()
        return payslip

    async def generate_run(self, period_id: int) -> PayrollRun:
        """Génère un lot : un bulletin par contrat actif sur la période."""
        period = await self.session.get(PayrollPeriod, period_id)
        if period is None:
            raise ValueError(f"Période {period_id} introuvable")

        reference = await self.sequences.next_value("payroll_run", "LPAIE")
        run = PayrollRun(
            period_id=period_id,
            reference=reference,
            state=PayrollRunState.DRAFT.value,
            company_id=period.company_id,
        )
        self.session.add(run)
        await self.session.flush()

        result = await self.session.execute(
            select(PayrollContract).where(
                PayrollContract.state == ContractState.OPEN.value,
                PayrollContract.date_start <= period.date_end,
                (PayrollContract.date_end.is_(None))
                | (PayrollContract.date_end >= period.date_start),
            )
        )
        contracts = list(result.scalars().all())
        for contract in contracts:
            payslip = await self.create_payslip(
                contract_id=contract.id,
                date_from=period.date_start,
                date_to=period.date_end,
                run_id=run.id,
                period_id=period.id,
                payment_date=period.payment_date,
            )
            await self.compute_sheet(payslip.id)

        await self.session.commit()
        await self.session.refresh(run)
        logger.info("Lot %s généré : %d bulletin(s)", run.reference, len(contracts))
        return run

    # ------------------------------------------------------------------ #
    # Éléments variables / jours travaillés
    # ------------------------------------------------------------------ #
    async def add_input(
        self, payslip_id: int, input_code: str, name: str,
        amount: float, quantity: float = 1,
    ) -> PayslipInput:
        payslip = await self.get(payslip_id)
        if payslip is None:
            raise ValueError(f"Bulletin {payslip_id} introuvable")
        if payslip.state not in (PayslipState.DRAFT.value, PayslipState.VERIFY.value):
            raise ValueError("Bulletin non modifiable dans cet état")
        line = PayslipInput(
            payslip_id=payslip_id, input_code=input_code, name=name,
            quantity=quantity, amount=amount, company_id=payslip.company_id,
        )
        self.session.add(line)
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def add_worked_day(
        self, payslip_id: int, work_entry_type: str, number_of_days: float,
        number_of_hours: float = 0, name: str | None = None,
    ) -> PayslipWorkedDay:
        payslip = await self.get(payslip_id)
        if payslip is None:
            raise ValueError(f"Bulletin {payslip_id} introuvable")
        day = PayslipWorkedDay(
            payslip_id=payslip_id, work_entry_type=work_entry_type, name=name,
            number_of_days=number_of_days, number_of_hours=number_of_hours,
            company_id=payslip.company_id,
        )
        self.session.add(day)
        await self.session.commit()
        await self.session.refresh(day)
        return day


    # ------------------------------------------------------------------ #
    # Moteur de calcul
    # ------------------------------------------------------------------ #
    async def compute_sheet(self, payslip_id: int) -> Payslip:
        """Calcule les lignes du bulletin à partir des règles de la structure."""
        payslip = await self._load_rich(payslip_id)
        if payslip is None:
            raise ValueError(f"Bulletin {payslip_id} introuvable")
        if payslip.state in (PayslipState.DONE.value, PayslipState.PAID.value):
            raise ValueError("Bulletin validé : recalcul impossible")

        structure_id = payslip.structure_id or getattr(
            payslip.contract, "structure_id", None
        )
        if not structure_id:
            raise ValueError("Aucune structure de paie associée au bulletin")

        # Recalcul -> purge des lignes précédentes
        await self.session.execute(
            delete(PayslipLine).where(PayslipLine.payslip_id == payslip_id)
        )

        rules = list(
            (
                await self.session.execute(
                    select(PayrollRule)
                    .where(
                        PayrollRule.structure_id == structure_id,
                        PayrollRule.is_active.is_(True),
                    )
                    .order_by(PayrollRule.sequence, PayrollRule.id)
                )
            ).scalars().all()
        )

        ctx = build_context(
            payslip,
            params=PayrollSettingsService.context_params(
                await PayrollSettingsService(self.session).get(payslip.company_id)
            ),
        )
        ctx["BRUT"] = 0.0
        totals = {"earn": 0.0, "deduct": 0.0, "patronal": 0.0}

        for rule in rules:
            if not rule_applies(rule, ctx):
                continue
            amount = compute_amount(rule, ctx)
            code = rule.code
            cat_code = rule.category.code if rule.category else None

            ctx["lines"][code] = amount
            # La ligne est aussi exposée comme variable (ex. ``ITS_BRUT``),
            # pour être lue par les conditions/formules des règles suivantes.
            ctx[code] = amount
            if cat_code:
                ctx["categories"][cat_code] = (
                    ctx["categories"].get(cat_code, 0.0) + amount
                )
            if cat_code in EARNING_CODES:
                ctx["BRUT"] = ctx["BRUT"] + amount
                totals["earn"] += amount
            elif cat_code in DEDUCTION_CODES:
                totals["deduct"] += amount
            elif cat_code in PATRONAL_CODES:
                totals["patronal"] += amount

            self.session.add(
                PayslipLine(
                    payslip_id=payslip.id,
                    rule_id=rule.id,
                    category_id=rule.category_id,
                    code=code,
                    name=rule.name,
                    category_code=cat_code,
                    sequence=rule.sequence,
                    quantity=1,
                    rate=amount,
                    amount=amount,
                    total=amount,
                    account_debit=rule.account_debit,
                    account_credit=rule.account_credit,
                    company_id=payslip.company_id,
                )
            )

        payslip.gross = round(totals["earn"], 2)
        payslip.total_deductions = round(totals["deduct"], 2)
        payslip.net_wage = round(totals["earn"] - totals["deduct"], 2)
        payslip.employer_cost = round(totals["earn"] + totals["patronal"], 2)
        payslip.state = PayslipState.VERIFY.value

        await self.session.commit()
        await self.session.refresh(payslip)
        logger.info(
            "Bulletin %s calculé : brut=%.2f net=%.2f",
            payslip.number, float(payslip.gross), float(payslip.net_wage),
        )
        return payslip


    # ------------------------------------------------------------------ #
    # Workflow
    # ------------------------------------------------------------------ #
    async def validate(self, payslip_id: int, user_id: int | None = None) -> Payslip:
        """Valide un bulletin (verify → done) et le comptabilise."""
        payslip = await self._load_rich(payslip_id)
        if payslip is None:
            raise ValueError(f"Bulletin {payslip_id} introuvable")
        if payslip.state not in (PayslipState.DRAFT.value, PayslipState.VERIFY.value):
            raise ValueError(f"Bulletin non validable (état : {payslip.state})")

        if not payslip.lines:
            await self.compute_sheet(payslip_id)

        payslip.state = PayslipState.DONE.value
        await self.session.commit()
        await self.session.refresh(payslip)

        # Comptabilisation défensive (ne bloque pas la validation)
        try:
            from app.modules.accounting.services.posting_service import PostingService

            entry, created = await PostingService(self.session).post_payslip(payslip)
            if created and entry is not None:
                payslip.entry_id = entry.id
                await self.session.commit()
                await self.session.refresh(payslip)
        except Exception:  # pragma: no cover - défensif
            logger.exception(
                "Comptabilisation impossible pour le bulletin %s", payslip.number
            )
            await self.session.rollback()

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "payslip.validated", "payslip", payslip.id,
            company_id=payslip.company_id, user_id=user_id,
            new_values={"state": payslip.state, "net_wage": float(payslip.net_wage)},
        )
        return payslip

    async def validate_run(
        self, run_id: int, user_id: int | None = None
    ) -> PayrollRun:
        """Valide tous les bulletins d'un lot puis marque le lot validé."""
        run = await self.session.get(PayrollRun, run_id)
        if run is None:
            raise ValueError(f"Lot {run_id} introuvable")
        payslips = await self.list_payslips(run_id=run_id, limit=10_000)
        for payslip in payslips:
            if payslip.state in (PayslipState.DRAFT.value, PayslipState.VERIFY.value):
                await self.validate(payslip.id, user_id=user_id)
        run.state = PayrollRunState.VALIDATED.value
        await self.session.commit()
        await self.session.refresh(run)
        return run


    async def pay(self, run_id: int, user_id: int | None = None) -> PayrollRun:
        """Marque un lot validé comme payé."""
        run = await self.session.get(PayrollRun, run_id)
        if run is None:
            raise ValueError(f"Lot {run_id} introuvable")
        if run.state != PayrollRunState.VALIDATED.value:
            raise ValueError("Le lot doit être validé avant d'être payé")
        payslips = await self.list_payslips(run_id=run_id, limit=10_000)
        for payslip in payslips:
            payslip.state = PayslipState.PAID.value
        run.state = PayrollRunState.PAID.value
        await self.session.commit()
        await self.session.refresh(run)

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "payroll_run.paid", "payroll_run", run.id,
            company_id=run.company_id, user_id=user_id,
            new_values={"state": run.state, "total_net": run.total_net},
        )
        return run

    async def back_to_draft(
        self, payslip_id: int, user_id: int | None = None
    ) -> Payslip:
        """Remet un bulletin en brouillon et annule l'écriture comptable."""
        payslip = await self.get(payslip_id)
        if payslip is None:
            raise ValueError(f"Bulletin {payslip_id} introuvable")
        if payslip.state == PayslipState.PAID.value:
            raise ValueError("Un bulletin payé ne peut pas être remis en brouillon")

        from app.modules.accounting.services.posting_service import PostingService

        entry = await PostingService(self.session).find_by_source(
            payslip.company_id, "payslip", payslip.id
        )
        if entry is not None:
            await self.session.delete(entry)
            payslip.entry_id = None

        payslip.state = PayslipState.DRAFT.value
        await self.session.commit()
        await self.session.refresh(payslip)
        return payslip


__all__ = ["PayslipService"]

