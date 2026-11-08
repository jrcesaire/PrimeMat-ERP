"""Paramétrage de paie par défaut (structure + règles) — Côte d'Ivoire.

Barème conforme au **système 2026** : impôt unique progressif sur les
traitements et salaires (ITS, tranches 0 / 16 / 21 / 24 / 28 / 32 %) après
déduction de la **RICF** (réduction pour charges de famille), et cotisations
CNPS (retraite salarié 6,3 %, charges patronales 15,45 %) plafonnées à
45 × SMIG (SMIG 2026 = 75 000 FCFA).

⚠️ Jeu de règles **de départ, à valider par un expert paie** : barème et taux
évoluent par décret. Le moteur de calcul les rend entièrement modifiables
sans toucher au code.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payroll.models.contribution import ContributionRegister
from app.modules.payroll.models.structure import (
    PayrollRule,
    PayrollRuleCategory,
    PayrollStructure,
)

STRUCTURE_CODE = "PAIE_CI"
STRUCTURE_NAME = "Paie Côte d'Ivoire"

CATEGORIES: tuple[tuple[str, str, int], ...] = (
    ("BASE", "Salaire de base", 10),
    ("PRIME", "Primes et gains", 20),
    ("COTIS", "Cotisations sociales salariales", 30),
    ("IMPOT", "Impôt sur salaires (ITS)", 40),
    ("PATRONAL", "Charges patronales", 50),
    ("NET", "Net à payer (informatif)", 90),
)

#: Taux et barème par défaut — repris depuis les Paramètres de paie.
from app.modules.payroll.services.settings_service import (
    DEFAULT_PAYROLL_SETTINGS,
    ITS_2026_BRACKETS,
)


def rule_specs(settings: dict) -> tuple[dict, ...]:
    """Règles de paie dérivées des paramètres (barème ITS, taux CNPS, plafond).

    Les formules référencent des **variables** (``CNPS_CEILING``,
    ``CNPS_SAL_RATE``, ``RICF_HALF``…) fournies par le moteur à partir des
    Paramètres de paie : modifier un taux ne demande aucun code.
    """
    brackets = settings.get("its_brackets") or ITS_2026_BRACKETS
    return (
        dict(code="SALAIRE_BASE", name="Salaire de base", category="BASE",
             sequence=10, amount_type="formula", formula="SALAIRE_BASE"),
        dict(code="PRIMES",
             name="Primes et indemnités imposables (éléments variables)",
             category="PRIME", sequence=20, amount_type="formula",
             formula="INPUTS_TOTAL"),
        dict(code="CNPS_SAL", name="CNPS salarié — retraite (plafonnée)",
             category="COTIS", sequence=30, amount_type="formula",
             formula="min(BRUT, CNPS_CEILING) * CNPS_SAL_RATE / 100",
             register="CNPS", credit_account="431000"),
        dict(code="ITS_BRUT", name="Impôt sur salaires (ITS) — barème",
             category="IMPOT", sequence=40, amount_type="scale",
             percentage_of="BRUT", condition="BRUT > 0",
             scale_brackets=brackets, credit_account="447000"),
        dict(code="RICF", name="Réduction d'impôt pour charges de famille (RICF)",
             category="IMPOT", sequence=45, amount_type="formula",
             formula="-min(ITS_BRUT, max(0, PARTS - 1) * (2 * RICF_HALF))",
             condition="ITS_BRUT > 0"),
        dict(code="CNPS_PAT", name="CNPS patronal (retraite + PF + AT)",
             category="PATRONAL", sequence=50, amount_type="formula",
             formula="min(BRUT, CNPS_CEILING) * CNPS_PAT_RATE / 100",
             register="CNPS", credit_account="431000"),
    )


async def build_default_structure(
    session: AsyncSession, company_id: int, settings: dict | None = None
) -> dict[str, int]:
    """Crée/actualise structure, catégories, organisme et règles de paie.

    Idempotent : une règle existante (même ``code``) est **mise à jour** à
    partir des paramètres courants — c'est ce qui applique un nouveau barème
    d'ITS ou un nouveau taux CNPS sans recréer la structure.
    """
    settings = settings or DEFAULT_PAYROLL_SETTINGS
    created = {"categories": 0, "registers": 0, "rules": 0, "rules_updated": 0}

    structure = (
        await session.execute(
            select(PayrollStructure).where(
                PayrollStructure.company_id == company_id,
                PayrollStructure.code == STRUCTURE_CODE,
            )
        )
    ).scalars().first()
    if structure is None:
        structure = PayrollStructure(
            name=STRUCTURE_NAME, code=STRUCTURE_CODE, country="CI",
            is_default=True, company_id=company_id,
        )
        session.add(structure)
        await session.flush()

    # Catégories
    cat_map: dict[str, PayrollRuleCategory] = {
        c.code: c
        for c in (
            await session.execute(
                select(PayrollRuleCategory).where(
                    PayrollRuleCategory.structure_id == structure.id
                )
            )
        ).scalars().all()
    }
    for code, name, sequence in CATEGORIES:
        if code in cat_map:
            continue
        category = PayrollRuleCategory(
            structure_id=structure.id, name=name, code=code,
            sequence=sequence, company_id=company_id,
        )
        session.add(category)
        await session.flush()
        cat_map[code] = category
        created["categories"] += 1

    # Organismes de cotisation
    reg_map: dict[str, ContributionRegister] = {
        r.code: r
        for r in (
            await session.execute(
                select(ContributionRegister).where(
                    ContributionRegister.company_id == company_id
                )
            )
        ).scalars().all()
    }
    if "CNPS" not in reg_map:
        register = ContributionRegister(
            name="Caisse Nationale de Prévoyance Sociale",
            code="CNPS", account_code="431000", company_id=company_id,
        )
        session.add(register)
        await session.flush()
        reg_map["CNPS"] = register
        created["registers"] += 1

    # Règles — upsert (création ou mise à jour depuis les paramètres)
    existing_rules = {
        r.code: r
        for r in (
            await session.execute(
                select(PayrollRule).where(PayrollRule.structure_id == structure.id)
            )
        ).scalars().all()
    }
    for spec in rule_specs(settings):
        register = reg_map.get(spec.get("register")) if spec.get("register") else None
        values = dict(
            category_id=cat_map[spec["category"]].id,
            contribution_register_id=register.id if register else None,
            name=spec["name"],
            sequence=spec["sequence"],
            amount_type=spec["amount_type"],
            amount_fixed=spec.get("fixed", 0),
            percentage_of=spec.get("percentage_of"),
            percentage=spec.get("percentage", 0),
            formula=spec.get("formula"),
            scale_brackets=spec.get("scale_brackets"),
            condition=spec.get("condition"),
            account_credit=spec.get("credit_account"),
        )
        rule = existing_rules.get(spec["code"])
        if rule is None:
            session.add(
                PayrollRule(
                    structure_id=structure.id,
                    code=spec["code"],
                    is_active=True,
                    company_id=company_id,
                    **values,
                )
            )
            created["rules"] += 1
        else:
            for field, value in values.items():
                setattr(rule, field, value)
            created["rules_updated"] += 1

    await session.flush()
    return created


async def seed_payroll_ci(session: AsyncSession, company_id: int) -> dict[str, int]:
    """Peuplement initial (défauts) de la structure de paie d'une entreprise."""
    return await build_default_structure(session, company_id, DEFAULT_PAYROLL_SETTINGS)
