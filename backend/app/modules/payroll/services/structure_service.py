"""Service Paramétrage de paie — structures, catégories, règles, organismes."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.payroll.models.contribution import ContributionRegister
from app.modules.payroll.models.structure import (
    PayrollRule,
    PayrollRuleCategory,
    PayrollStructure,
)
from app.modules.payroll.schemas import (
    CategoryCreate,
    ContributionRegisterCreate,
    RuleCreate,
    RuleUpdate,
    StructureCreate,
)


class StructureService:
    """CRUD du paramétrage de paie (réservé aux gestionnaires paie)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Structures ------------------------------------------------- #
    async def list_structures(self) -> list[PayrollStructure]:
        result = await self.session.execute(
            select(PayrollStructure)
            # Liste : ni catégories ni règles (chargées à la demande).
            .options(noload(PayrollStructure.categories), noload(PayrollStructure.rules))
            .order_by(PayrollStructure.id)
        )
        return list(result.scalars().all())

    async def ensure_default(self, company_id: int) -> PayrollStructure | None:
        """Garantit l'existence de la structure de paie par défaut.

        Le socle (structure + catégories + règles + organisme) est semé au
        bootstrap, qui ne s'exécute que sur une base vide. Sur une base
        existante où le module Paie est activé plus tard, la table serait vide
        et la **liste déroulante des salariés sans option**. On la crée donc à
        la demande, à partir des Paramètres de paie courants (idempotent).
        """
        existing = (
            await self.session.execute(
                select(PayrollStructure).where(
                    PayrollStructure.company_id == company_id
                )
            )
        ).scalars().first()
        if existing is not None:
            return existing

        from app.modules.payroll.seed.payroll_ci import build_default_structure
        from app.modules.payroll.services.settings_service import (
            PayrollSettingsService,
        )

        settings = await PayrollSettingsService(self.session).get(company_id)
        await build_default_structure(self.session, company_id, settings)
        await self.session.commit()
        return (
            await self.session.execute(
                select(PayrollStructure).where(
                    PayrollStructure.company_id == company_id
                )
            )
        ).scalars().first()

    async def get_structure(self, structure_id: int) -> PayrollStructure | None:
        return await self.session.get(PayrollStructure, structure_id)

    async def create_structure(
        self, data: StructureCreate, company_id: int
    ) -> PayrollStructure:
        structure = PayrollStructure(
            name=data.name,
            code=data.code,
            country=data.country,
            is_default=data.is_default,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(structure)
        await self.session.commit()
        await self.session.refresh(structure)
        return structure

    # --- Catégories ------------------------------------------------- #
    async def list_categories(self, structure_id: int) -> list[PayrollRuleCategory]:
        result = await self.session.execute(
            select(PayrollRuleCategory)
            .where(PayrollRuleCategory.structure_id == structure_id)
            .order_by(PayrollRuleCategory.sequence)
        )
        return list(result.scalars().all())

    async def add_category(
        self, structure_id: int, data: CategoryCreate
    ) -> PayrollRuleCategory:
        structure = await self.get_structure(structure_id)
        if structure is None:
            raise ValueError(f"Structure {structure_id} introuvable")
        category = PayrollRuleCategory(
            structure_id=structure_id,
            name=data.name,
            code=data.code,
            sequence=data.sequence,
            company_id=structure.company_id,
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    # --- Règles ----------------------------------------------------- #
    async def list_rules(self, structure_id: int) -> list[PayrollRule]:
        result = await self.session.execute(
            select(PayrollRule)
            .options(
                noload(PayrollRule.category),
                noload(PayrollRule.contribution_register),
            )
            .where(PayrollRule.structure_id == structure_id)
            .order_by(PayrollRule.sequence)
        )
        return list(result.scalars().all())

    async def add_rule(self, data: RuleCreate) -> PayrollRule:
        structure = await self.get_structure(data.structure_id)
        if structure is None:
            raise ValueError(f"Structure {data.structure_id} introuvable")
        category = await self.session.get(PayrollRuleCategory, data.category_id)
        if category is None or category.structure_id != data.structure_id:
            raise ValueError("Catégorie introuvable pour cette structure")
        from app.modules.payroll.services.rule_engine import safe_eval

        # Validation au plus tôt : l'expression doit être analysable.
        if data.formula:
            safe_eval(data.formula, {"SALAIRE_BASE": 1, "BRUT": 1})
        if data.condition:
            safe_eval(data.condition, {"SALAIRE_BASE": 1, "BRUT": 1})

        rule = PayrollRule(company_id=structure.company_id, **data.model_dump())
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, data: RuleUpdate) -> PayrollRule:
        rule = await self.session.get(PayrollRule, rule_id)
        if rule is None:
            raise ValueError(f"Règle {rule_id} introuvable")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    # --- Organismes de cotisation ----------------------------------- #
    async def list_registers(self) -> list[ContributionRegister]:
        result = await self.session.execute(select(ContributionRegister))
        return list(result.scalars().all())

    async def create_register(
        self, data: ContributionRegisterCreate, company_id: int
    ) -> ContributionRegister:
        register = ContributionRegister(company_id=company_id, **data.model_dump())
        self.session.add(register)
        await self.session.commit()
        await self.session.refresh(register)
        return register
