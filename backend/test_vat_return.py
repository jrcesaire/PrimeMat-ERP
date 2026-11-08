"""
Test fonctionnel — TVA déclarative (Lot D de la Phase 2 comptable).

Vérifie, sur une base SQLite temporaire :

1. **calcul** de la TVA collectée (``tax_collected``) et déductible
   (``tax_deductible``) sur une période ;
2. **liquidation** (``submit``) : soldage des comptes de TVA et position nette
   sur le compte de l'État (``441``) ;
3. **stabilité du calcul** : après liquidation, un nouvel aperçu de la même
   période donne toujours les mêmes montants (les écritures générées par le
   module sont exclues) ;
4. **règlement** (``pay``) : ``D 441 / C 521`` ;
5. **crédit de TVA** : période dégageant un crédit reportable, non réglable ;
6. **garde-fous** : période en doublon, double soumission, règlement d'un
   brouillon, suppression d'une déclaration soumise.

Usage : ``python backend/test_vat_return.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_vat_return.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_FILE}"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

_db_path = os.path.join(BACKEND, DB_FILE)
if os.path.exists(_db_path):
    os.remove(_db_path)

import logging  # noqa: E402

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
        print(f"  OK   {label}")
    else:
        FAILURES.append(f"{label} {detail}".strip())
        print(f"  ECHEC {label} {detail}")


def close_to(value: float, expected: float, tol: float = 0.01) -> bool:
    return abs(float(value) - float(expected)) < tol


async def main() -> int:
    from app.core.database import AsyncSessionLocal, Base, engine

    import app.core.models  # noqa: F401
    import app.modules.accounting.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.delivery.models  # noqa: F401
    import app.modules.finance.models  # noqa: F401
    import app.modules.invoicing.models  # noqa: F401
    import app.modules.payments.models  # noqa: F401
    import app.modules.purchases.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    from sqlalchemy import select

    from app.core.models.company import Company
    from app.core.services.seed_service import bootstrap_defaults
    from app.modules.accounting.schemas import (
        JournalEntryCreate,
        JournalEntryLineCreate,
    )
    from app.modules.accounting.schemas.ohada import FiscalYearCreate
    from app.modules.accounting.schemas.vat import VATPayRequest, VATReturnCreate
    from app.modules.accounting.services.journal_service import LedgerService
    from app.modules.accounting.services.ohada import OHADAService
    from app.modules.accounting.services.vat_service import VATService

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await bootstrap_defaults(
            session,
            company_name="Test TVA SARL",
            company_code="TTV",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="tva@test.ci",
            admin_password="MotDePasse@123",
        )
        company = (
            await session.execute(select(Company).where(Company.code == "TTV"))
        ).scalar_one()
        company_id = company.id

        service = VATService(session)
        ledger = LedgerService(session)
        ohada = OHADAService(session)
        await ohada.create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )

        async def post(entry_date, journal, description, lines):
            return await ledger.create_entry(
                company_id,
                JournalEntryCreate(
                    entry_date=entry_date,
                    journal_code=journal,
                    description=description,
                    lines=[
                        JournalEntryLineCreate(
                            account_code=code, label=label, debit=debit, credit=credit
                        )
                        for code, label, debit, credit in lines
                    ],
                ),
                post=True,
            )

        async def balances_map() -> dict[str, float]:
            rows = await ledger.account_balances(company_id)
            return {b["account_code"]: b["balance"] for b in rows}

        # --- 1. Écritures de mars 2026 ---
        print("[1] Écritures de la période (mars 2026)")
        await post(
            date(2026, 3, 10), "VTE", "Facture client FA-100",
            [("411000", "Client", 1_200_000, 0),
             ("701000", "Ventes", 0, 1_000_000),
             ("443000", "TVA facturée sur ventes", 0, 200_000)],
        )
        await post(
            date(2026, 3, 20), "ACH", "Facture fournisseur FF-100",
            [("601000", "Achats", 400_000, 0),
             ("445000", "TVA récupérable sur achats", 80_000, 0),
             ("401000", "Fournisseur", 0, 480_000)],
        )
        print("  écritures enregistrées (collectée 200 000 / déductible 80 000)")

        # --- 2. Aperçu ---
        print("\n[2] Aperçu de la déclaration")
        preview = await service.preview(
            company_id, date(2026, 3, 1), date(2026, 3, 31)
        )
        check(
            "TVA collectée = 200 000",
            close_to(preview["collected_amount"], 200_000),
            f"({preview['collected_amount']})",
        )
        check(
            "TVA déductible = 80 000",
            close_to(preview["deductible_amount"], 80_000),
            f"({preview['deductible_amount']})",
        )
        check(
            "TVA à payer = 120 000",
            close_to(preview["net_due"], 120_000),
            f"({preview['net_due']})",
        )
        check("crédit reportable = 0", close_to(preview["credit_carry"], 0))
        check(
            "2 lignes (une collectée, une déductible)",
            len(preview["lines"]) == 2,
            f"({[l['account_code'] for l in preview['lines']]})",
        )
        check(
            "libellé par défaut « Mars 2026 »",
            preview["label"] == "Mars 2026",
            f"({preview['label']})",
        )
        kinds = {l["account_code"]: l["kind"] for l in preview["lines"]}
        check("4431 classé collectée", kinds.get("443000") == "collected")
        check("4452 classé déductible", kinds.get("445000") == "deductible")

        # --- 3. Création de la déclaration ---
        print("\n[3] Création de la déclaration (brouillon)")
        vat_return = await service.create_return(
            company_id,
            VATReturnCreate(
                period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
            ),
        )
        vat_id = vat_return.id
        check("statut = draft", vat_return.status == "draft")
        check(
            "référence générée",
            bool(vat_return.reference),
            f"({vat_return.reference})",
        )
        check("libellé = Mars 2026", vat_return.label == "Mars 2026")
        check("détail par compte persisté", len(vat_return.lines) == 2)
        check(
            "TVA à payer enregistrée = 120 000",
            close_to(vat_return.net_due, 120_000),
        )

        # --- 4. Liquidation ---
        print("\n[4] Liquidation (submit)")
        submitted = await service.submit(company_id, vat_id)
        check("statut = submitted", submitted.status == "submitted")
        check("écriture de liquidation générée", submitted.journal_entry_id is not None)

        balances = await balances_map()
        check(
            "compte 4431 soldé (0)",
            close_to(balances.get("443000", 0), 0),
            f"({balances.get('4431')})",
        )
        check(
            "compte 4452 soldé (0)",
            close_to(balances.get("445000", 0), 0),
            f"({balances.get('4452')})",
        )
        check(
            "TVA due au crédit du compte 441 (-120 000)",
            close_to(balances.get("444000", 0), -120_000),
            f"({balances.get('441')})",
        )
        check(
            "somme des soldes de tous les comptes = 0",
            close_to(sum(balances.values()), 0),
            f"({sum(balances.values())})",
        )

        # --- 5. Stabilité du calcul après liquidation ---
        print("\n[5] Stabilité du calcul après liquidation")
        after = await service.preview(
            company_id, date(2026, 3, 1), date(2026, 3, 31)
        )
        check(
            "collectée inchangée (200 000)",
            close_to(after["collected_amount"], 200_000),
            f"({after['collected_amount']})",
        )
        check(
            "déductible inchangée (80 000)",
            close_to(after["deductible_amount"], 80_000),
            f"({after['deductible_amount']})",
        )
        check(
            "TVA à payer inchangée (120 000)",
            close_to(after["net_due"], 120_000),
            f"({after['net_due']})",
        )

        # --- 6. Règlement ---
        print("\n[6] Règlement de la TVA due")
        paid = await service.pay(company_id, vat_id, VATPayRequest())
        check("statut = paid", paid.status == "paid")
        check("écriture de règlement générée", paid.payment_entry_id is not None)
        balances = await balances_map()
        check(
            "compte 441 soldé (0)",
            close_to(balances.get("444000", 0), 0),
            f"({balances.get('441')})",
        )
        check(
            "décaissement banque 521 (-120 000)",
            close_to(balances.get("521000", 0), -120_000),
            f"({balances.get('521')})",
        )
        check(
            "somme des soldes de tous les comptes = 0",
            close_to(sum(balances.values()), 0),
        )

        # --- 7. Crédit de TVA (avril 2026) ---
        print("\n[7] Crédit de TVA (avril 2026 : achats > ventes)")
        await post(
            date(2026, 4, 15), "ACH", "Facture fournisseur FF-200",
            [("601000", "Achats", 500_000, 0),
             ("445000", "TVA récupérable sur achats", 100_000, 0),
             ("401000", "Fournisseur", 0, 600_000)],
        )
        credit_return = await service.create_return(
            company_id,
            VATReturnCreate(
                period_start=date(2026, 4, 1), period_end=date(2026, 4, 30)
            ),
        )
        credit_id = credit_return.id
        check(
            "TVA collectée = 0",
            close_to(credit_return.collected_amount, 0),
            f"({credit_return.collected_amount})",
        )
        check(
            "TVA déductible = 100 000",
            close_to(credit_return.deductible_amount, 100_000),
        )
        check(
            "TVA à payer = 0",
            close_to(credit_return.net_due, 0),
            f"({credit_return.net_due})",
        )
        check(
            "crédit reportable = 100 000",
            close_to(credit_return.credit_carry, 100_000),
            f"({credit_return.credit_carry})",
        )
        check("libellé par défaut « Avril 2026 »", credit_return.label == "Avril 2026")

        credit_submitted = await service.submit(company_id, credit_id)
        balances = await balances_map()
        check(
            "crédit constaté au débit du compte 441 (+100 000)",
            close_to(balances.get("444000", 0), 100_000),
            f"({balances.get('441')})",
        )
        check(
            "somme des soldes de tous les comptes = 0",
            close_to(sum(balances.values()), 0),
            f"({sum(balances.values())})",
        )
        check(
            "déclaration en crédit soumise",
            credit_submitted.status == "submitted",
        )

        # --- 8. Garde-fous ---
        print("\n[8] Garde-fous")

        async def expect_error(label: str, coro, needle: str) -> None:
            """Exécute ``coro`` en attendant un ValueError contenant ``needle``."""
            try:
                await coro
                check(label, False, "(aucune erreur levée)")
            except ValueError as exc:
                check(label, needle in str(exc), f"({exc})")
                await session.rollback()

        await expect_error(
            "période en doublon refusée",
            service.create_return(
                company_id,
                VATReturnCreate(
                    period_start=date(2026, 3, 1), period_end=date(2026, 3, 31)
                ),
            ),
            "existe déjà",
        )
        await expect_error(
            "double soumission refusée",
            service.submit(company_id, vat_id),
            "déjà été soumise",
        )
        await expect_error(
            "règlement d'une déclaration en crédit refusé",
            service.pay(company_id, credit_id, VATPayRequest()),
            "crédit reportable",
        )
        await expect_error(
            "suppression d'une déclaration soumise refusée",
            service.delete_return(company_id, vat_id),
            "brouillon",
        )
        await expect_error(
            "période incohérente refusée",
            service.preview(company_id, date(2026, 5, 31), date(2026, 5, 1)),
            "suivre le début",
        )

        # Un brouillon est supprimable
        draft = await service.create_return(
            company_id,
            VATReturnCreate(
                period_start=date(2026, 6, 1), period_end=date(2026, 6, 30)
            ),
        )
        draft_id = draft.id
        await expect_error(
            "règlement d'un brouillon refusé",
            service.pay(company_id, draft_id, VATPayRequest()),
            "soumise",
        )
        await service.delete_return(company_id, draft_id)
        remaining = {v.id for v in await service.list_returns(company_id)}
        check("brouillon supprimable", draft_id not in remaining)

        # Historique et filtre par statut
        all_returns = await service.list_returns(company_id)
        check("historique : 2 déclarations", len(all_returns) == 2, f"({len(all_returns)})")
        paid_only = await service.list_returns(company_id, status="paid")
        check("filtre par statut : 1 déclaration payée", len(paid_only) == 1)

    await engine.dispose()
    if os.path.exists(_db_path):
        os.remove(_db_path)

    print("\n" + "=" * 64)
    if FAILURES:
        print(f"{len(FAILURES)} ÉCHEC(S) sur {CHECKS} vérifications :")
        for failure in FAILURES:
            print("  -", failure)
        return 1
    print(f"TOUTES LES VÉRIFICATIONS SONT PASSÉES ({CHECKS}/{CHECKS})")
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
