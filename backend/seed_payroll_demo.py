"""
Jeu de données de DÉMONSTRATION — module Paie (profils variés + PDF imprimables).

Crée une base SQLite dédiée (``demo_payroll.db``), une entreprise, la structure de
paie 2026, **8 salariés aux profils variés** (du SMIG à la direction, situations
familiales et parts fiscales différentes, primes imposables), génère le lot de
paie d'une période puis édite les **documents imprimables** :

- un **bulletin de paie** par salarié ;
- le **bordereau CNPS** de la période ;
- l'**état ITS** de la période ;
- un **récapitulatif CSV**.

Les PDF sont écrits dans ``resources/generated/demo_paie_janvier_2026/``.

Usage : ``python backend/seed_payroll_demo.py``
"""
import asyncio
import os
import sys

DB_FILE = "demo_payroll.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_FILE}"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Sortie console lisible (l'écho SQL dépend de DEBUG dans .env).
import logging  # noqa: E402

logging.disable(logging.INFO)

_db_path = os.path.join(BACKEND, DB_FILE)
if os.path.exists(_db_path):
    os.remove(_db_path)

#: Dossier de sortie des documents.
OUT_DIR = os.path.join(
    BACKEND, "resources", "generated", "demo_paie_janvier_2026"
)

#: Entreprise de démonstration.
COMPANY = dict(
    name="PRIMEMAT MATÉRIAUX SARL",
    code="PMP",
    currency_code="XOF",
    phone="27 22 45 67 89",
    email="contact@primemat.ci",
    address={
        "street": "Zone Industrielle de Yopougon, Lot 42",
        "city": "Abidjan",
        "country": "Côte d'Ivoire",
    },
    ncc="1234567 A",
    rccm="CI-ABJ-2019-B-12345",
    share_capital="10 000 000",
    social_security_code="170001199958",
)

#: Salariés : (référence, prénom, nom, situation, enfants, emploi, salaire, primes).
#: Les primes sont des **éléments variables imposables** (rubrique PRIMES).
EMPLOYEES: list[dict] = [
    dict(reference="E001", first_name="Awa", last_name="TRAORÉ",
         marital_status="single", dependents=0, job_title="Ouvrier spécialisé",
         hire_date="2024-03-01", cnps_number="170002000001",
         wage=75_000, primes=[]),
    dict(reference="E002", first_name="Koffi", last_name="KOUASSI",
         marital_status="married", dependents=0, job_title="Ouvrier qualifié",
         hire_date="2021-09-15", cnps_number="170002000002",
         wage=120_000, primes=[]),
    dict(reference="E003", first_name="Mamadou", last_name="DIALLO",
         marital_status="married", dependents=2, job_title="Chef d'équipe",
         hire_date="2018-01-05", cnps_number="170002000003",
         wage=150_000, primes=[]),
    dict(reference="E004", first_name="Adjoa", last_name="N'GUESSAN",
         marital_status="single", dependents=1, job_title="Technicienne",
         hire_date="2022-06-01", cnps_number="170002000004",
         wage=220_000,
         primes=[("PRIME_TRANSPORT", "Prime de transport imposable", 20_000)]),
    dict(reference="E005", first_name="Ibrahim", last_name="KONÉ",
         marital_status="married", dependents=3, job_title="Agent de maîtrise",
         hire_date="2016-02-20", cnps_number="170002000005",
         wage=350_000, primes=[]),
    dict(reference="E006", first_name="Fatou", last_name="BAMBA",
         marital_status="married", dependents=2, job_title="Cadre comptable",
         hire_date="2015-11-10", cnps_number="170002000006",
         wage=600_000,
         primes=[("PRIME_REPRES", "Prime de représentation", 50_000)]),
    dict(reference="E007", first_name="Serge", last_name="YAO",
         marital_status="married", dependents=1, job_title="Directeur commercial",
         hire_date="2013-05-02", cnps_number="170002000007",
         wage=1_200_000, primes=[]),
    dict(reference="E008", first_name="Ibrahim", last_name="OUATTARA",
         marital_status="married", dependents=4, job_title="Directeur général",
         hire_date="2010-01-04", cnps_number="170002000008",
         wage=4_000_000,
         primes=[("PRIME_RESPONS", "Prime de responsabilité", 100_000)]),
]

#: Période de paie de démonstration.
PERIOD = dict(
    name="Paie Janvier 2026",
    date_start="2026-01-01",
    date_end="2026-01-31",
    payment_date="2026-02-05",
)


async def main() -> None:
    from datetime import date

    from sqlalchemy import select
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
    import app.modules.payroll.models  # noqa: F401
    import app.modules.purchases.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    engine = create_async_engine(f"sqlite+aiosqlite:///./{DB_FILE}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        # 1. Entreprise + plan comptable + journaux (dont le journal PAI).
        from app.core.models.company import Company
        from app.modules.accounting.services.account_service import AccountService

        company = Company(**COMPANY)
        session.add(company)
        await session.flush()
        await AccountService(session).seed_ohada_chart(company.id, "SYSCOHADA")
        await AccountService(session).seed_default_journals(company.id)
        await session.commit()
        print(f"Entreprise « {company.name} » créée (id={company.id}).")

        # 2. Structure de paie (paramètres 2026 par défaut).
        from app.modules.payroll.models.structure import PayrollStructure
        from app.modules.payroll.seed.payroll_ci import seed_payroll_ci

        created = await seed_payroll_ci(session, company.id)
        await session.commit()
        structure = (
            await session.execute(
                select(PayrollStructure).where(
                    PayrollStructure.company_id == company.id
                )
            )
        ).scalars().first()
        print(f"Structure « {structure.name} » semée : {created}.")

        # 3. Salariés + contrats (paramètres de paie à la création).
        from app.modules.payroll.schemas import ContractInline, EmployeeCreate
        from app.modules.payroll.services.employee_service import EmployeeService

        employees_service = EmployeeService(session)
        for spec in EMPLOYEES:
            hire = date.fromisoformat(spec["hire_date"])
            await employees_service.create(
                EmployeeCreate(
                    reference=spec["reference"],
                    first_name=spec["first_name"],
                    last_name=spec["last_name"],
                    marital_status=spec["marital_status"],
                    dependents=spec["dependents"],
                    job_title=spec["job_title"],
                    hire_date=hire,
                    cnps_number=spec["cnps_number"],
                    contract=ContractInline(
                        structure_id=structure.id, wage=spec["wage"], date_start=hire
                    ),
                ),
                company.id,
            )
        print(f"{len(EMPLOYEES)} salariés créés (avec leur contrat).")

        # 4. Période de paie + génération du lot.
        from app.modules.payroll.models.period import PayrollPeriod
        from app.modules.payroll.services.payslip_service import PayslipService

        period = PayrollPeriod(
            company_id=company.id,
            name=PERIOD["name"],
            date_start=date.fromisoformat(PERIOD["date_start"]),
            date_end=date.fromisoformat(PERIOD["date_end"]),
            payment_date=date.fromisoformat(PERIOD["payment_date"]),
            state="open",
        )
        session.add(period)
        await session.commit()

        payslips_service = PayslipService(session)
        run = await payslips_service.generate_run(period.id)
        print(f"Lot {run.reference} généré sur « {period.name} ».")

        # 5. Éléments variables (primes imposables) + recalcul.
        from app.modules.payroll.models.employee import Employee

        primes_by_ref = {spec["reference"]: spec["primes"] for spec in EMPLOYEES}
        for payslip in await payslips_service.list_payslips(run_id=run.id, limit=100):
            employee = await session.get(Employee, payslip.employee_id)
            primes = primes_by_ref.get(employee.reference, [])
            if not primes:
                continue
            for code, label, amount in primes:
                await payslips_service.add_input(payslip.id, code, label, amount)
            await payslips_service.compute_sheet(payslip.id)
        print("Primes imposables saisies et bulletins recalculés.")

        # 6. Validation (comptabilisation) puis paiement du lot.
        run = await payslips_service.validate_run(run.id)
        run = await payslips_service.pay(run.id)
        print(f"Lot {run.reference} validé (écritures) puis payé.")


        # 7. Édition des documents imprimables (PDF).
        from app.core.documents.context import ContextBuilder
        from app.core.documents.engine import DocumentEngine

        os.makedirs(OUT_DIR, exist_ok=True)
        builder = ContextBuilder()
        documents = DocumentEngine()

        lot = await payslips_service.list_payslips(
            run_id=run.id, limit=100, with_relations=True
        )
        lot.sort(key=lambda p: p.number)

        recap: list[tuple] = []
        for index, payslip in enumerate(lot, start=1):
            context = await builder.load_payslip(payslip.id)
            employee = context["employee"]
            filename = (
                f"{index:02d}_Bulletin_{employee.reference}_{employee.last_name}.pdf"
            )
            await asyncio.to_thread(
                documents.render_to_pdf,
                "payslip.html", context, os.path.join(OUT_DIR, filename),
            )
            recap.append((payslip, employee))

        cnps_context = await builder.load_cnps(company.id, period.id)
        await asyncio.to_thread(
            documents.render_to_pdf,
            "cnps_return.html", cnps_context,
            os.path.join(OUT_DIR, "90_Declaration_CNPS.pdf"),
        )
        its_context = await builder.load_its(company.id, period.id)
        await asyncio.to_thread(
            documents.render_to_pdf,
            "its_return.html", its_context,
            os.path.join(OUT_DIR, "91_Etat_ITS.pdf"),
        )

        # 8. Récapitulatif CSV.
        import csv

        from app.modules.payroll.services.declaration_service import (
            PayrollDeclarationService,
        )

        declarations = PayrollDeclarationService(session)
        cnps = await declarations.cnps_bordereau(company.id, period.id)
        its = await declarations.its_declaration(company.id, period.id)

        csv_path = os.path.join(OUT_DIR, "00_Recapitulatif.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([
                "Bulletin", "Matricule", "Salarié", "Emploi", "Parts", "Brut",
                "CNPS salarié", "ITS net", "Retenues", "Net à payer",
                "Coût employeur",
            ])
            for payslip, employee in recap:
                values = _line_values(payslip)
                writer.writerow([
                    payslip.number, employee.reference, employee.full_name,
                    employee.job_title, employee.tax_parts,
                    f"{float(payslip.gross):.0f}", f"{values['cnps_sal']:.0f}",
                    f"{values['its']:.0f}", f"{float(payslip.total_deductions):.0f}",
                    f"{float(payslip.net_wage):.0f}",
                    f"{float(payslip.employer_cost):.0f}",
                ])

        # 9. Affichage console — contrôle des sorties.
        print()
        header = (
            f"{'Bulletin':<14}{'Salarié':<26}{'Parts':>6}{'Brut':>12}"
            f"{'CNPS sal.':>11}{'ITS':>10}{'Net':>12}{'Coût empl.':>13}"
        )
        print(header)
        print("-" * len(header))
        for payslip, employee in recap:
            values = _line_values(payslip)
            name = f"{employee.first_name} {employee.last_name}"
            print(
                f"{payslip.number:<14}{name:<26}{float(employee.tax_parts):>6.1f}"
                f"{float(payslip.gross):>12,.0f}{values['cnps_sal']:>11,.0f}"
                f"{values['its']:>10,.0f}{float(payslip.net_wage):>12,.0f}"
                f"{float(payslip.employer_cost):>13,.0f}"
            )
        print("-" * len(header))
        print(
            f"CNPS période : {cnps['grand_total']:>12,.0f}  "
            f"(salarié {cnps['employee_total']:,.0f} / "
            f"patronal {cnps['employer_total']:,.0f})"
        )
        print(f"ITS période  : {its['total_its']:>12,.0f}")

        print()
        print(f"Documents générés dans : {OUT_DIR}")
        for name in sorted(os.listdir(OUT_DIR)):
            print(f"  - {name}")

    await engine.dispose()

    # Le moteur du socle (app.core.database) ouvre aussi la base : il faut le
    # libérer, sinon SQLite garde le fichier verrouillé sous Windows.
    from app.core.database import engine as core_engine

    await core_engine.dispose()


def _line_values(payslip) -> dict[str, float]:
    """Valeurs de synthèse d'un bulletin (CNPS salarié, ITS net)."""
    lines = {line.code: float(line.total or 0) for line in payslip.lines}
    return {
        "cnps_sal": lines.get("CNPS_SAL", 0.0),
        "its": lines.get("ITS_BRUT", 0.0) + lines.get("RICF", 0.0),
        "cnps_pat": lines.get("CNPS_PAT", 0.0),
    }


if __name__ == "__main__":
    asyncio.run(main())
    try:
        if os.path.exists(_db_path):
            os.remove(_db_path)
        print("\nBase de démonstration supprimée (les PDF sont conservés).")
    except PermissionError:
        print(f"\nBase de démonstration conservée : {_db_path}")

