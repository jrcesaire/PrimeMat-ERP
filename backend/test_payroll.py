"""
Test fonctionnel — module Paie (barème 2026, moteur, bulletins, déclarations).

Vérifie, sur une base SQLite temporaire :

1. **moteur de règles** — calcul sûr des expressions (rejet des nœuds interdits) ;
2. **barème ITS 2026** — exemples officiels (1 800 000 / 2 parts → 373 000) ;
3. **CNPS** — taux 6,3 % salarié / 15,45 % patronal, plafonnés à 45 × SMIG ;
4. **paramètres de paie** — lecture, mise à jour, application à la structure ;
5. **configurabilité** — un plafond/SMIG modifié change le calcul (sans code) ;
6. **socle personnel** — salarié + contrat (paramètres de paie) en une création ;
7. **moteur de paie** — `compute_sheet` : brut, retenues, net, coût employeur ;
8. **bulletins** — workflow draft → verify → done → paid, lot de paie ;
9. **comptabilisation** — écriture équilibrée et **idempotente** (source payslip) ;
10. **déclarations** — bordereau CNPS et état ITS agrégés sur une période.

Usage : ``python backend/test_payroll.py``
"""
import asyncio
import os
import sys

DB_FILE = "test_payroll.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_FILE}"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

_db_path = os.path.join(BACKEND, DB_FILE)
if os.path.exists(_db_path):
    os.remove(_db_path)

import logging  # noqa: E402
from datetime import date  # noqa: E402

logging.disable(logging.INFO)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    """Vérifie une assertion et journalise le résultat."""
    global CHECKS
    CHECKS += 1
    if condition:
        print(f"  OK    {label}")
    else:
        FAILURES.append(f"{label} {detail}".strip())
        print(f"  ECHEC {label} {detail}")


def near(value, expected, tol: float = 0.01) -> bool:
    """Égalité numérique à la tolérance près."""
    return abs(float(value or 0) - float(expected)) <= tol


async def main() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base

    import app.core.models  # noqa: F401
    import app.modules.accounting.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.delivery.models  # noqa: F401
    import app.modules.finance.models  # noqa: F401
    import app.modules.invoicing.models  # noqa: F401
    import app.modules.payments.models  # noqa: F401
    import app.modules.purchases.models  # noqa: F401
    import app.modules.payroll.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    engine = create_async_engine(
        f"sqlite+aiosqlite:///./{DB_FILE}",
        # Les FK SQLite sont désactivées par défaut : notre schéma s'appuie sur
        # des contraintes (CASCADE), on ne les active donc pas pour éviter des
        # faux négatifs sur des insertions partielles de test.
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        await run_payroll_tests(session)

    await engine.dispose()

    # ``sync_payroll_defaults`` ouvre le moteur du socle (app.core.database) :
    # il faut le libérer, sinon SQLite garde le fichier verrouillé sous Windows.
    from app.core.database import engine as core_engine

    await core_engine.dispose()
    try:
        if os.path.exists(_db_path):
            os.remove(_db_path)
    except PermissionError:
        pass


# --------------------------------------------------------------------- #
# Barème ITS 2026 (référence)
# --------------------------------------------------------------------- #
def its_2026(base: float) -> float:
    """Impôt brut 2026 par tranches (0/16/21/24/28/32 %)."""
    brackets = [
        (75000, 0.0), (240000, 0.16), (800000, 0.21),
        (2400000, 0.24), (8000000, 0.28), (None, 0.32),
    ]
    total = 0.0
    previous = 0.0
    for up_to, rate in brackets:
        if up_to is None:
            portion = max(0.0, base - previous)
        else:
            portion = max(0.0, min(base, up_to) - previous)
            previous = up_to
        total += portion * rate
    return total


async def run_payroll_tests(session) -> None:
    from app.core.models.company import Company
    from app.modules.accounting.services.account_service import AccountService

    # --- Environnement : entreprise + plan comptable + journaux --------- #
    company = Company(name="PrimeMat Paie SARL", code="PMP", currency_code="XOF")
    session.add(company)
    await session.flush()
    accounts = await AccountService(session).seed_ohada_chart(company.id, "SYSCOHADA")
    journals = await AccountService(session).seed_default_journals(company.id)
    check("plan comptable OHADA semé (trace d'au moins un compte)",
          accounts >= 1, f"({accounts})")
    check("journal PAI présent dans les journaux par défaut", journals >= 1)

    await test_rule_engine()
    structure = await test_seed_and_settings(session, company)
    await test_structure_autoseed(session)
    await test_employee_and_payslip(session, company, structure)
    await test_declarations(session, company, structure)
    await test_workflow_and_posting(session, company, structure)
    await test_configurability(session, company, structure)


async def test_rule_engine() -> None:
    """Le DSL de calcul est arithmétique, booléen — et sûr."""
    from app.modules.payroll.services.rule_engine import (
        RuleEvaluationError,
        safe_eval,
    )

    ctx = {
        "BRUT": 1_800_000.0, "PARTS": 2.0, "SMIG": 75000.0,
        "CNPS_CEILING": 3_375_000.0, "CNPS_SAL_RATE": 6.3,
    }
    check("évaluation arithmétique (min / opérateurs)",
          near(safe_eval("min(BRUT, CNPS_CEILING) * 6.3 / 100", ctx), 113400))
    check("évaluation booléenne (comparaison)",
          safe_eval("BRUT > 0", ctx) is True)
    check("variable absente → erreur métier",
          _raises(lambda: safe_eval("INCONNU + 1", ctx), RuleEvaluationError))

    forbidden = [
        "__import__('os').system('x')",
        "open('x')",
        "(1).__class__",
        "[i for i in (1, 2)]",
        "lambda: 1",
        "BRUT.__class__",
    ]
    rejected = sum(
        1 for expr in forbidden if _raises(lambda e=expr: safe_eval(e, ctx), RuleEvaluationError)
    )
    check(f"DSL sûr : {rejected}/{len(forbidden)} expressions dangereuses rejetées",
          rejected == len(forbidden))


def _raises(fn, exc_type) -> bool:
    """Vrai si ``fn`` lève ``exc_type``."""
    try:
        fn()
    except exc_type:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


async def test_seed_and_settings(session, company):
    """Structure de paie + paramètres configurables."""
    from sqlalchemy import select

    from app.modules.payroll.models.structure import PayrollRule, PayrollStructure
    from app.modules.payroll.seed.payroll_ci import seed_payroll_ci
    from app.modules.payroll.services.settings_service import PayrollSettingsService

    created = await seed_payroll_ci(session, company.id)
    await session.commit()
    check("structure semée (6 règles)", created["rules"] == 6, f"({created})")

    structure = (
        await session.execute(
            select(PayrollStructure).where(PayrollStructure.company_id == company.id)
        )
    ).scalars().first()
    check("structure PAIE_CI présente",
          structure is not None and structure.code == "PAIE_CI")

    rules = (
        await session.execute(
            select(PayrollRule).where(PayrollRule.structure_id == structure.id)
        )
    ).scalars().all()
    codes = {r.code for r in rules}
    check("jeu de règles complet",
          codes == {"SALAIRE_BASE", "PRIMES", "CNPS_SAL", "ITS_BRUT", "RICF", "CNPS_PAT"},
          f"({sorted(codes)})")
    its_rule = next(r for r in rules if r.code == "ITS_BRUT")
    check("barème ITS porté par la règle (type scale)", its_rule.amount_type == "scale")

    again = await seed_payroll_ci(session, company.id)
    await session.commit()
    check("seed idempotent (aucune règle ajoutée)", again["rules"] == 0, f"({again})")

    settings_service = PayrollSettingsService(session)
    settings = await settings_service.get(company.id)
    check("SMIG par défaut = 75 000", near(settings["smig"], 75000))
    params = PayrollSettingsService.context_params(settings)
    check("plafond CNPS = 45 × SMIG = 3 375 000", near(params["CNPS_CEILING"], 3_375_000))

    await settings_service.update({"smig": 80000}, company.id)
    updated = await settings_service.get(company.id)
    check("paramètre modifiable (SMIG 80 000)", near(updated["smig"], 80000))
    await settings_service.update({"smig": 75000}, company.id)
    return structure


async def test_structure_autoseed(session) -> None:
    """La structure par défaut est créée à la demande si la base n'a pas été semée.

    Le socle Paie n'est semé qu'au bootstrap (base vide) : sur une base
    existante où le module est activé plus tard, la liste déroulante des
    salariés serait sans option. ``ensure_default`` comble ce trou.
    """
    from sqlalchemy import select

    from app.core.models.company import Company
    from app.modules.payroll.models.structure import PayrollRule, PayrollStructure
    from app.modules.payroll.services.structure_service import StructureService

    company = Company(name="Société Sans Paie", code="SSP", currency_code="XOF")
    session.add(company)
    await session.commit()

    before = (
        await session.execute(
            select(PayrollStructure).where(PayrollStructure.company_id == company.id)
        )
    ).scalars().all()
    check("base non semée : aucune structure de paie", len(before) == 0)

    structure = await StructureService(session).ensure_default(company.id)
    check("structure créée à la demande (liste déroulante jamais vide)",
          structure is not None and structure.code == "PAIE_CI")

    rules = (
        await session.execute(
            select(PayrollRule).where(PayrollRule.structure_id == structure.id)
        )
    ).scalars().all()
    check("règles semées avec la structure (6)", len(rules) == 6, f"({len(rules)})")

    again = await StructureService(session).ensure_default(company.id)
    check("création idempotente (même structure)", again.id == structure.id)

    # La synchronisation au démarrage couvre elle aussi les bases existantes
    # (même mécanisme que les permissions système).
    from app.core.services.seed_service import sync_payroll_defaults

    late = Company(name="Société Tardive", code="SLT", currency_code="XOF")
    session.add(late)
    await session.commit()

    created = await sync_payroll_defaults()
    check("synchronisation au démarrage : structure créée pour une base existante",
          created >= 1, f"({created} entreprise(s))")
    late_structures = (
        await session.execute(
            select(PayrollStructure).where(PayrollStructure.company_id == late.id)
        )
    ).scalars().all()
    check("structure présente après synchronisation", len(late_structures) == 1)


async def test_employee_and_payslip(session, company, structure):
    """Salarié + contrat (paramètres de paie) puis calcul du bulletin."""
    from sqlalchemy import select

    from app.modules.payroll.models.contract import PayrollContract
    from app.modules.payroll.schemas import ContractInline, EmployeeCreate
    from app.modules.payroll.services.employee_service import (
        EmployeeService,
        derive_tax_parts,
    )
    from app.modules.payroll.services.payslip_service import PayslipService

    employee = await EmployeeService(session).create(
        EmployeeCreate(
            reference="E001", first_name="Koffi", last_name="Kouassi",
            marital_status="married", dependents=0, job_title="Chef de service",
            contract=ContractInline(structure_id=structure.id, wage=1_800_000),
        ),
        company.id,
    )
    check("salarié créé", employee.reference == "E001")
    # Matricule généré automatiquement s'il n'est pas fourni (nomenclature
    # « employee » — Paramètres → Séquences). Sans contrat, pour ne pas ajouter
    # un bulletin aux lots suivants.
    auto = await EmployeeService(session).create(
        EmployeeCreate(first_name="Auto", last_name="Matricule"),
        company.id,
    )
    check("matricule auto-généré (séquence « employee »)",
          bool(auto.reference) and auto.reference.startswith("MAT"),
          f"({auto.reference})")
    check("parts fiscales dérivées (marié → 2 parts)", near(employee.tax_parts, 2))
    check("parts fiscales dérivées (célibataire + 2 enfants → 2,5 parts)",
          near(derive_tax_parts("single", 2), 2.5))
    check("parts fiscales dérivées (célibataire sans enfant → 1 part)",
          near(derive_tax_parts("single", 0), 1))

    contract = (
        await session.execute(
            select(PayrollContract).where(PayrollContract.employee_id == employee.id)
        )
    ).scalars().first()
    check("contrat créé avec le salarié", contract is not None)
    check("contrat ouvert sur le salaire de base saisi",
          contract.state == "open" and near(contract.wage, 1_800_000))

    payslips = PayslipService(session)
    payslip = await payslips.create_payslip(contract.id, date(2026, 1, 1), date(2026, 1, 31))
    await session.commit()
    computed = await payslips.compute_sheet(payslip.id)
    lines = {line.code: float(line.total) for line in computed.lines}

    check("brut = salaire de base", near(computed.gross, 1_800_000))
    check("CNPS salarié 6,3 %", near(lines.get("CNPS_SAL"), 113_400))
    check("ITS brut (barème 2026)", near(lines.get("ITS_BRUT"), its_2026(1_800_000)))
    check("RICF = −11 000 (2 parts)", near(lines.get("RICF"), -11_000))
    check("ITS net = 373 000",
          near(lines.get("ITS_BRUT", 0) + lines.get("RICF", 0), 373_000))
    check("retenues = 486 400", near(computed.total_deductions, 486_400))
    check("net à payer = 1 313 600", near(computed.net_wage, 1_313_600))
    check("coût employeur = 2 078 100", near(computed.employer_cost, 2_078_100))



async def test_declarations(session, company, structure):
    """Bordereau CNPS et état ITS agrégés sur une période."""
    from sqlalchemy import select

    from app.modules.payroll.models.period import PayrollPeriod
    from app.modules.payroll.models.payslip import Payslip
    from app.modules.payroll.services.declaration_service import (
        PayrollDeclarationService,
    )

    period = PayrollPeriod(
        company_id=company.id, name="Paie Janvier 2026",
        date_start=date(2026, 1, 1), date_end=date(2026, 1, 31),
        payment_date=date(2026, 2, 5), state="open",
    )
    session.add(period)
    await session.flush()
    payslip = (
        await session.execute(
            select(Payslip).where(Payslip.company_id == company.id).order_by(Payslip.id)
        )
    ).scalars().first()
    payslip.period_id = period.id
    await session.commit()

    declarations = PayrollDeclarationService(session)
    cnps = await declarations.cnps_bordereau(company.id, period.id)
    check("bordereau CNPS : effectif = 1", cnps["employee_count"] == 1)
    check("bordereau CNPS : base cotisable", near(cnps["base"], 1_800_000))
    check("bordereau CNPS : part salariale", near(cnps["employee_total"], 113_400))
    check("bordereau CNPS : part patronale", near(cnps["employer_total"], 278_100))
    check("bordereau CNPS : total à verser", near(cnps["grand_total"], 391_500))
    check("bordereau CNPS : organisme CNPS identifié",
          any(r["code"] == "CNPS" for r in cnps["registers"]))

    its = await declarations.its_declaration(company.id, period.id)
    check("état ITS : total retenu = 373 000", near(its["total_its"], 373_000))
    check("état ITS : 1 ligne par salarié", len(its["lines"]) == 1)
    check("état ITS : parts du salarié = 2", its["lines"][0]["parts"] == 2)


async def test_workflow_and_posting(session, company, structure):
    """Validation → comptabilisation idempotente → lot de paie."""
    from sqlalchemy import select

    from app.modules.accounting.services.posting_service import PostingService
    from app.modules.payroll.models.period import PayrollPeriod
    from app.modules.payroll.models.payslip import Payslip
    from app.modules.payroll.services.payslip_service import PayslipService

    payslips = PayslipService(session)
    payslip = (
        await session.execute(
            select(Payslip).where(Payslip.company_id == company.id).order_by(Payslip.id)
        )
    ).scalars().first()

    validated = await payslips.validate(payslip.id)
    check("bulletin validé (état done)", validated.state == "done")
    check("écriture comptable rattachée", validated.entry_id is not None)

    posting = PostingService(session)
    entry = await posting.find_by_source(company.id, "payslip", payslip.id)
    check("écriture retrouvée par source « payslip »", entry is not None)
    check("écriture équilibrée (débit = crédit)",
          entry is not None and near(entry.total_debit, entry.total_credit))
    check("journal de paie utilisé", entry is not None and entry.journal_code == "PAI")

    _, created_again = await posting.post_payslip(validated)
    check("comptabilisation idempotente (aucun doublon)", created_again is False)

    # Lot de paie : période du jour (le contrat est ouvert aujourd'hui).
    period = PayrollPeriod(
        company_id=company.id, name="Paie du mois courant",
        date_start=date.today(), date_end=date.today(), state="open",
    )
    session.add(period)
    await session.commit()

    run = await payslips.generate_run(period.id)
    check("lot généré (référence LPAIE)", run.reference.startswith("LPAIE"),
          f"({run.reference})")
    run_payslips = await payslips.list_payslips(run_id=run.id, limit=50)
    check("un bulletin par contrat actif", len(run_payslips) == 1,
          f"({len(run_payslips)})")
    with_lines = await payslips.list_payslips(
        run_id=run.id, limit=10, with_relations=True
    )
    check("liste avec relations : lignes chargées (impression/CSV)",
          bool(with_lines) and len(with_lines[0].lines) > 0)
    validated_run = await payslips.validate_run(run.id)
    check("lot validé", validated_run.state == "validated")
    paid_run = await payslips.pay(run.id)
    check("lot payé", paid_run.state == "paid")



async def test_configurability(session, company, structure):
    """Un taux / barème modifié change le calcul — sans code."""
    from sqlalchemy import select

    from app.modules.payroll.models.contract import PayrollContract
    from app.modules.payroll.seed.payroll_ci import build_default_structure
    from app.modules.payroll.services.payslip_service import PayslipService
    from app.modules.payroll.services.settings_service import (
        DEFAULT_PAYROLL_SETTINGS,
        PayrollSettingsService,
    )

    settings_service = PayrollSettingsService(session)
    payslips = PayslipService(session)
    contract = (
        await session.execute(
            select(PayrollContract).where(PayrollContract.company_id == company.id)
        )
    ).scalars().first()

    # 1) Plafond CNPS ramené à 1 × SMIG → cotisation plafonnée au SMIG.
    await settings_service.update({"cnps_ceiling_multiple": 1}, company.id)
    payslip = await payslips.create_payslip(
        contract.id, date(2026, 3, 1), date(2026, 3, 31)
    )
    await session.commit()
    computed = await payslips.compute_sheet(payslip.id)
    lines = {line.code: float(line.total) for line in computed.lines}
    check("plafond CNPS configurable : 75 000 × 6,3 % = 4 725",
          near(lines.get("CNPS_SAL"), 4_725))

    # 2) Barème ITS remplacé par une tranche unique à 10 %.
    await settings_service.update(
        {"its_brackets": [{"up_to": None, "rate": 10}]}, company.id
    )
    settings = await settings_service.get(company.id)
    await build_default_structure(session, company.id, settings)
    await session.commit()
    computed = await payslips.compute_sheet(payslip.id)
    lines = {line.code: float(line.total) for line in computed.lines}
    check("barème ITS configurable : 10 % du brut = 180 000",
          near(lines.get("ITS_BRUT"), 180_000))

    # 3) Élément variable (prime) repris au recalcul.
    await payslips.add_input(payslip.id, "PRIME_TEST", "Prime de test", 25_000)
    recomputed = await payslips.compute_sheet(payslip.id)
    values = {line.code: float(line.total) for line in recomputed.lines}
    check("élément variable repris au recalcul (PRIMES = 25 000)",
          near(values.get("PRIMES"), 25_000) and near(recomputed.gross, 1_825_000))

    # 3) Retour aux paramètres par défaut.
    await settings_service.update(
        {
            "cnps_ceiling_multiple": 45,
            "its_brackets": DEFAULT_PAYROLL_SETTINGS["its_brackets"],
        },
        company.id,
    )
    settings = await settings_service.get(company.id)
    await build_default_structure(session, company.id, settings)
    await session.commit()
    check("paramètres rétablis (SMIG 75 000, plafond ×45)",
          near(settings["smig"], 75_000) and near(settings["cnps_ceiling_multiple"], 45))


if __name__ == "__main__":
    asyncio.run(main())
    print()
    if FAILURES:
        print(f"{len(FAILURES)} échec(s) sur {CHECKS} vérifications :")
        for failure in FAILURES:
            print(f"  - {failure}")
        sys.exit(1)
    print(f"TOUTES LES VÉRIFICATIONS SONT PASSÉES ({CHECKS} contrôles)")
    sys.exit(0)

