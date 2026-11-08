"""
Modèles de paramétrage de la paie : structures, catégories de rubriques et
règles de calcul.

Adaptation PrimeMAT du modèle OCA/payroll (``hr.payroll.structure``,
``hr.salary.rule.category``, ``hr.salary.rule``) : la paie est décrite par la
**donnée** (un jeu de règles ordonnées) et non par du code applicatif. Le
moteur (``services/rule_engine.py``) évalue ces règles séquentiellement.
"""
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import RuleAmountType


class PayrollStructure(Base, TenantMixin):
    """Structure de paie : ensemble de règles appliquées à un contrat."""

    name: Mapped[str] = MappedColumn(String(120), nullable=False)
    code: Mapped[str] = MappedColumn(String(30), index=True)
    country: Mapped[str] = MappedColumn(String(2), default="CI")
    is_default: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    notes: Mapped[str | None] = MappedColumn(String(500))

    categories: Mapped[list["PayrollRuleCategory"]] = relationship(
        "PayrollRuleCategory", back_populates="structure",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="PayrollRuleCategory.sequence",
    )
    rules: Mapped[list["PayrollRule"]] = relationship(
        "PayrollRule", back_populates="structure",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="PayrollRule.sequence",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_structure_company_code"),
    )

    def __repr__(self) -> str:
        return f"<PayrollStructure {self.code}>"


class PayrollRuleCategory(Base, TenantMixin):
    """Catégorie de rubrique (BASE, BRUT, COTIS, NET…).

    Le ``code`` sert de variable au moteur : le total cumulé d'une catégorie
    est exposé aux règles suivantes sous ``ctx["categories"][code]``.
    """

    structure_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_structures.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = MappedColumn(String(120), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), index=True)  # BASE, BRUT, COTIS, NET
    sequence: Mapped[int] = MappedColumn(Integer, default=10)

    structure: Mapped["PayrollStructure"] = relationship(
        "PayrollStructure", back_populates="categories"
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "structure_id", "code", name="uq_rule_category"
        ),
    )

    def __repr__(self) -> str:
        return f"<PayrollRuleCategory {self.code}>"


class PayrollRule(Base, TenantMixin):
    """Règle de paie évaluée par le moteur (data-driven)."""

    structure_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_structures.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    category_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_rule_categories.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    contribution_register_id: Mapped[int | None] = MappedColumn(
        ForeignKey("contribution_registers.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = MappedColumn(String(160), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), index=True)
    sequence: Mapped[int] = MappedColumn(Integer, default=10)

    amount_type: Mapped[str] = MappedColumn(
        String(20), default=RuleAmountType.FIXED.value
    )
    amount_fixed: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    #: Code d'une ligne ou d'une catégorie servant de base au pourcentage.
    percentage_of: Mapped[str | None] = MappedColumn(String(20))
    percentage: Mapped[float] = MappedColumn(Numeric(7, 4), default=0)
    #: Expression arithmétique restreinte (DSL sûr, cf. rule_engine).
    formula: Mapped[str | None] = MappedColumn(Text)
    #: Paliers d'un barème progressif (amount_type ``scale``) :
    #: ``[{"up_to": 75000, "rate": 0}, {"up_to": 240000, "rate": 16}, ...]``.
    #: Le dernier palier porte ``up_to = null`` (tranche ouverte supérieure).
    scale_brackets: Mapped[list | None] = MappedColumn(JSON)
    #: Condition booléenne restreinte (DSL sûr) — vide = toujours applicable.
    condition: Mapped[str | None] = MappedColumn(Text)
    appears_on_payslip: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Comptabilisation : comptes du plan désignés par code (résolus à l'usage)
    account_debit: Mapped[str | None] = MappedColumn(String(10))
    account_credit: Mapped[str | None] = MappedColumn(String(10))

    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    structure: Mapped["PayrollStructure"] = relationship(
        "PayrollStructure", back_populates="rules"
    )
    category: Mapped["PayrollRuleCategory"] = relationship(
        "PayrollRuleCategory", lazy="selectin"
    )
    contribution_register: Mapped["ContributionRegister | None"] = relationship(
        "ContributionRegister", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "structure_id", "code", name="uq_rule_structure_code"
        ),
    )

    def __repr__(self) -> str:
        return f"<PayrollRule {self.code} [{self.amount_type}]>"
