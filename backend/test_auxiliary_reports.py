"""
Test fonctionnel — états auxiliaires (Lot E de la Phase 2 comptable).

Vérifie, sur une base SQLite temporaire :

1. **grand livre auxiliaire** (``partner_ledger``) : mouvements du tiers,
   solde progressif, solde d'ouverture et de clôture, filtrage par période ;
2. **chéancier** (``payment_schedule``) : échéances à venir et retards,
   tranches (``overdue``, ``d0_30``…), horizon, exclusion des brouillons ;
3. garde-fous (tiers inconnu).

Usage : ``python backend/test_auxiliary_reports.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_auxiliary_reports.db"
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
    from app.modules.accounting.services.financial_service import FinancialService
    from app.modules.accounting.services.journal_service import LedgerService
    from app.modules.accounting.services.ohada import OHADAService
    from app.modules.crm.models.partner import Partner
    from app.modules.invoicing.models.invoice import Invoice

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await bootstrap_defaults(
            session,
            company_name="Test États Auxiliaires SARL",
            company_code="TEA",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="aux@test.ci",
            admin_password="MotDePasse@123",
        )
        company = (
            await session.execute(select(Company).where(Company.code == "TEA"))
        ).scalar_one()
        company_id = company.id

        service = FinancialService(session)
        ledger = LedgerService(session)
        await OHADAService(session).create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )

        # --- 1. Tiers, factures et écritures ---
        print("[1] Tiers, factures et écritures")
        partner = Partner(
            name="Client Alpha SARL",
            code="CLI-A",
            role="client",
            company_id=company_id,
        )
        session.add(partner)
        await session.flush()
        partner_id = partner.id

        invoices = [
            # référence, date, échéance, total, payé, statut
            ("FA-001", date(2026, 3, 1), date(2026, 3, 31), 1_200_000, 200_000, "posted"),
            ("FA-002", date(2026, 4, 1), date(2026, 5, 15), 500_000, 0, "posted"),
            ("FA-003", date(2026, 6, 1), date(2026, 7, 30), 300_000, 0, "draft"),
        ]
        for ref, inv_date, due, total, paid, status in invoices:
            session.add(
                Invoice(
                    reference=ref,
                    partner_id=partner_id,
                    status=status,
                    invoice_date=inv_date,
                    due_date=due,
                    amount_total=total,
                    paid_amount=paid,
                    company_id=company_id,
                )
            )
        await session.flush()
        print(f"  {len(invoices)} factures (dont 1 brouillon) pour {partner.name}")

        async def post(entry_date, journal, description, lines):
            return await ledger.create_entry(
                company_id,
                JournalEntryCreate(
                    entry_date=entry_date,
                    journal_code=journal,
                    description=description,
                    lines=[
                        JournalEntryLineCreate(
                            account_code=code,
                            label=label,
                            debit=debit,
                            credit=credit,
                            partner_id=pid,
                        )
                        for code, label, debit, credit, pid in lines
                    ],
                ),
                post=True,
            )

        await post(
            date(2026, 3, 1), "VTE", "Facture FA-001",
            [("411", "Client Alpha", 1_200_000, 0, partner_id),
             ("701", "Ventes", 0, 1_000_000, None),
             ("4431", "TVA facturée", 0, 200_000, None)],
        )
        await post(
            date(2026, 3, 20), "BAN", "Encaissement FA-001",
            [("521", "Banque", 200_000, 0, None),
             ("411", "Client Alpha", 0, 200_000, partner_id)],
        )
        await post(
            date(2026, 4, 1), "VTE", "Facture FA-002",
            [("411", "Client Alpha", 500_000, 0, partner_id),
             ("701", "Ventes", 0, 416_667, None),
             ("4431", "TVA facturée", 0, 83_333, None)],
        )
        await session.commit()

        # --- 2. Grand livre auxiliaire ---
        print("\n[2] Grand livre auxiliaire du tiers")
        book = await service.partner_ledger(company_id, partner_id)
        check("tiers reconnu", book["partner_name"] == "Client Alpha SARL")
        check("3 mouvements", len(book["lines"]) == 3, f"({len(book['lines'])})")
        check("solde d'ouverture = 0", close_to(book["opening_balance"], 0))
        check(
            "débit total = 1 700 000",
            close_to(book["total_debit"], 1_700_000),
            f"({book['total_debit']})",
        )
        check(
            "crédit total = 200 000",
            close_to(book["total_credit"], 200_000),
            f"({book['total_credit']})",
        )
        check(
            "solde de clôture = 1 500 000",
            close_to(book["closing_balance"], 1_500_000),
            f"({book['closing_balance']})",
        )
        running = [line["balance"] for line in book["lines"]]
        check(
            "solde progressif : 1 200 000 → 1 000 000 → 1 500 000",
            [round(b, 2) for b in running] == [1_200_000, 1_000_000, 1_500_000],
            f"({running})",
        )
        check(
            "mouvements classés par date",
            [line["entry_date"] for line in book["lines"]]
            == [date(2026, 3, 1), date(2026, 3, 20), date(2026, 4, 1)],
        )

        period = await service.partner_ledger(
            company_id, partner_id, date_from=date(2026, 4, 1)
        )
        check(
            "période à partir du 01/04 : ouverture = 1 000 000",
            close_to(period["opening_balance"], 1_000_000),
            f"({period['opening_balance']})",
        )
        check("période à partir du 01/04 : 1 mouvement", len(period["lines"]) == 1)
        check(
            "période à partir du 01/04 : clôture = 1 500 000",
            close_to(period["closing_balance"], 1_500_000),
        )

        # --- 3. Chéancier ---
        print("\n[3] Chéancier au 30/04/2026")
        schedule = await service.payment_schedule(
            company_id,
            partner_type="customer",
            as_of=date(2026, 4, 30),
            horizon_days=90,
        )
        check(
            "2 factures échéancées (le brouillon est exclu)",
            len(schedule["lines"]) == 2,
            f"({[l['reference'] for l in schedule['lines']]})",
        )
        check(
            "tri par date d'échéance",
            [l["reference"] for l in schedule["lines"]] == ["FA-001", "FA-002"],
        )

        first = schedule["lines"][0]
        check("FA-001 en retard de 30 jours", first["days_remaining"] == -30, f"({first['days_remaining']})")
        check("FA-001 classée « en retard »", first["bucket"] == "overdue")
        check(
            "FA-001 montant dû = 1 000 000 (1 200 000 − 200 000 payés)",
            close_to(first["amount_due"], 1_000_000),
            f"({first['amount_due']})",
        )

        second = schedule["lines"][1]
        check("FA-002 échoit dans 15 jours", second["days_remaining"] == 15, f"({second['days_remaining']})")
        check("FA-002 classée 0-30 jours", second["bucket"] == "d0_30")
        check(
            "FA-002 montant dû = 500 000",
            close_to(second["amount_due"], 500_000),
        )

        check(
            "total en retard = 1 000 000",
            close_to(schedule["totals"]["overdue"], 1_000_000),
            f"({schedule['totals']['overdue']})",
        )
        check(
            "total 0-30 jours = 500 000",
            close_to(schedule["totals"]["d0_30"], 500_000),
        )
        check(
            "total échéancé = 1 500 000",
            close_to(schedule["total"], 1_500_000),
            f"({schedule['total']})",
        )
        check(
            "aucune échéance au-delà de 30 jours",
            close_to(schedule["totals"]["d31_60"], 0)
            and close_to(schedule["totals"]["d61_90"], 0),
        )

        # Horizon nul : seule l'échéance déjà dépassée reste
        tight = await service.payment_schedule(
            company_id,
            partner_type="customer",
            as_of=date(2026, 4, 30),
            horizon_days=0,
        )
        check(
            "horizon 0 jour : seule FA-001 subsiste",
            [l["reference"] for l in tight["lines"]] == ["FA-001"],
            f"({[l['reference'] for l in tight['lines']]})",
        )
        check(
            "horizon 0 jour : total = 1 000 000",
            close_to(tight["total"], 1_000_000),
        )

        # --- 4. Garde-fous ---
        print("\n[4] Garde-fous")
        try:
            await service.partner_ledger(company_id, 999_999)
            check("tiers inconnu refusé", False, "(aucune erreur levée)")
        except ValueError as exc:
            check("tiers inconnu refusé", "introuvable" in str(exc), f"({exc})")

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
