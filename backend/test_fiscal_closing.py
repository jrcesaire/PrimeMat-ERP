"""
Test fonctionnel — clôture d'exercice (Lot B de la Phase 2 comptable).

Vérifie de bout en bout, sur une base SQLite temporaire :

1. le **rattachement** des écritures à leur exercice (``fiscal_year_id``) ;
2. le **verrouillage** : aucune écriture possible sur un exercice clôturé
   (``create_entry`` et ``post_entry``) ;
3. la **clôture** : soldage des charges/produits (classes 6-7-8) → résultat
   au compte **121** (bénéfice) ou **129** (perte) ;
4. le **report à nouveau automatique** : affectation du résultat au compte
   **111** (créditeur) ou **119** (débiteur) sur l'exercice suivant, créé au
   besoin ;
5. l'**équilibre** conservé : la somme des soldes de tous les comptes reste
   nulle et le bilan reste équilibré ;
6. la **réouverture** : les écritures générées sont retirées, puis une
   nouvelle clôture les régénère sans doublon.

Usage : ``python backend/test_fiscal_closing.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_fiscal_closing.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_FILE}"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

# Base temporaire : repartir d'un fichier vierge à chaque exécution, sinon
# les données d'un run précédent faussent l'amorçage (comptes déjà présents).
_db_path = os.path.join(BACKEND, DB_FILE)
if os.path.exists(_db_path):
    os.remove(_db_path)

import logging  # noqa: E402

logging.disable(logging.INFO)

# Console Windows : la page de code par défaut (cp1252) ne sait pas encoder
# les libellés accentués ni les flèches « → » des messages de test.
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

    # Tous les paquets de modèles doivent être importés pour que les clés
    # étrangères inter-modules (ex. invoices.order_id → sales_orders) se
    # résolvent au moment du create_all.
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
    from app.core.services.seed_service import bootstrap_defaults
    from app.modules.accounting.schemas import (
        JournalEntryCreate,
        JournalEntryLineCreate,
    )
    from app.modules.accounting.schemas.ohada import FiscalYearCreate
    from app.modules.accounting.services.journal_service import LedgerService
    from app.modules.accounting.services.ohada import OHADAService

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # --- 0. Amorçage (devises, entreprise, plan comptable, journaux) ---
        created = await bootstrap_defaults(
            session,
            company_name="Test Clôture SARL",
            company_code="TCL",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="cloture@test.ci",
            admin_password="MotDePasse@123",
        )
        from sqlalchemy import select

        from app.core.models.company import Company

        company = (
            await session.execute(select(Company).where(Company.code == "TCL"))
        ).scalar_one()
        company_id = company.id
        print(
            f"Amorçage : entreprise #{company_id} "
            f"({created.get('accounts', 0)} comptes créés, "
            f"{created.get('journals', 0)} journaux créés)"
        )

        ohada = OHADAService(session)
        ledger = LedgerService(session)

        # --- 1. Exercice 2026 + écritures de l'année ---
        year = await ohada.create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )
        # Identifiant figé : les ``rollback()`` ultérieurs expirent l'instance
        # ORM, et relire ``year.id`` déclencherait une requête.
        year_id = year.id

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

        # Vente à crédit : D 411 / C 701 + C 4431
        await post(
            date(2026, 3, 15), "VTE", "Facture client FA-001",
            [("411", "Client", 1_200_000, 0),
             ("701", "Ventes", 0, 1_000_000),
             ("4431", "TVA facturée", 0, 200_000)],
        )
        # Achat : D 601 / C 401
        await post(
            date(2026, 4, 10), "ACH", "Facture fournisseur FF-001",
            [("601", "Achats", 400_000, 0),
             ("401", "Fournisseur", 0, 400_000)],
        )
        # Encaissement : D 521 / C 411
        await post(
            date(2026, 5, 20), "BAN", "Encaissement client",
            [("521", "Banque", 1_200_000, 0),
             ("411", "Client", 0, 1_200_000)],
        )
        await session.commit()

        print("\n[1] Rattachement des écritures à l'exercice")
        entries = await ledger.list_entries(company_id, limit=50)
        check(
            "toutes les écritures portent fiscal_year_id",
            all(e.fiscal_year_id == year.id for e in entries),
            f"(ids={[e.fiscal_year_id for e in entries]})",
        )

        # --- 2. Aperçu de la clôture ---
        print("\n[2] Aperçu de la clôture")
        preview = await ohada.closing_preview(company_id, year.id)
        check(
            "résultat = 600 000 (bénéfice)",
            close_to(preview["result"], 600_000),
            f"(obtenu {preview['result']})",
        )
        check("result_type = profit", preview["result_type"] == "profit")
        check("compte de résultat = 121", preview["result_account"] == "121")
        check(
            "exercice suivant absent (créé par la clôture)",
            preview["next_year"] is None and preview["next_year_will_be_created"],
        )
        check(
            "comptes à solder : 601 et 701",
            sorted(l["account_code"] for l in preview["lines"]) == ["601", "701"],
            f"(obtenu {sorted(l['account_code'] for l in preview['lines'])})",
        )

        # --- 3. Clôture ---
        print("\n[3] Clôture de l'exercice")
        closed = await ohada.close_fiscal_year(company_id, year.id)
        check("statut de l'exercice = closed", closed.status == "closed")

        next_year = await ohada._next_fiscal_year(company_id, closed)
        check("exercice suivant créé", next_year is not None)
        if next_year is not None:
            check(
                "exercice suivant = 2027-01-01 → 2027-12-31",
                next_year.start_date == date(2027, 1, 1)
                and next_year.end_date == date(2027, 12, 31),
                f"({next_year.start_date} → {next_year.end_date})",
            )

        async def balances_map() -> dict[str, float]:
            rows = await ledger.account_balances(company_id)
            return {b["account_code"]: b["balance"] for b in rows}

        balances = await balances_map()
        check("charges soldées (601 = 0)", close_to(balances.get("601", 0), 0))
        check("produits soldés (701 = 0)", close_to(balances.get("701", 0), 0))
        check(
            "TVA collectée conservée au bilan (4431 = -200 000)",
            close_to(balances.get("4431", 0), -200_000),
            f"(obtenu {balances.get('4431')})",
        )
        check("résultat affecté (121 = 0)", close_to(balances.get("121", 0), 0))
        check(
            "report à nouveau créditeur (111 = -600 000)",
            close_to(balances.get("111", 0), -600_000),
            f"(obtenu {balances.get('111')})",
        )
        check(
            "trésorerie intacte (521 = 1 200 000)",
            close_to(balances.get("521", 0), 1_200_000),
        )
        check("créance client soldée (411 = 0)", close_to(balances.get("411", 0), 0))
        check(
            "dette fournisseur intacte (401 = -400 000)",
            close_to(balances.get("401", 0), -400_000),
        )
        total = sum(balances.values())
        check(
            "somme des soldes de tous les comptes = 0",
            close_to(total, 0),
            f"(obtenu {total})",
        )

        closing = await ohada._find_generated_entry(
            company_id, "fiscal_year_closing", year.id
        )
        opening = await ohada._find_generated_entry(
            company_id, "fiscal_year_opening", year.id
        )
        check("écriture de clôture générée", closing is not None)
        check("écriture d'affectation générée", opening is not None)
        if closing is not None:
            check(
                "écriture de clôture équilibrée",
                close_to(float(closing.total_debit), float(closing.total_credit)),
            )
            check("écriture de clôture publiée", closing.status == "posted")
        if opening is not None:
            check(
                "affectation datée du 1er jour de l'exercice suivant",
                opening.entry_date == date(2027, 1, 1),
                f"({opening.entry_date})",
            )
            check(
                "affectation équilibrée",
                close_to(float(opening.total_debit), float(opening.total_credit)),
            )

        # --- 4. Verrouillage de l'exercice clôturé ---
        print("\n[4] Verrouillage de l'exercice clôturé")
        try:
            await post(
                date(2026, 6, 1),
                "OD",
                "Écriture interdite sur exercice clôturé",
                [("601", "Achats", 1000, 0), ("401", "Fournisseur", 0, 1000)],
            )
            check("écriture sur exercice clôturé refusée", False, "(aucune erreur)")
        except ValueError as exc:
            check(
                "écriture sur exercice clôturé refusée",
                "clôturé" in str(exc),
                f"({exc})",
            )
            await session.rollback()

        # --- 5. Réouverture puis nouvelle clôture ---
        print("\n[5] Réouverture puis nouvelle clôture")
        reopened = await ohada.reopen_fiscal_year(company_id, year_id)
        check("statut de l'exercice = open", reopened.status == "open")

        balances = await balances_map()
        check("charges restaurées (601 = 400 000)", close_to(balances.get("601", 0), 400_000))
        check(
            "produits restaurés (701 = -1 000 000)",
            close_to(balances.get("701", 0), -1_000_000),
        )
        check(
            "résultat soldé après réouverture (121 = 0)",
            close_to(balances.get("121", 0), 0),
            f"(obtenu {balances.get('121')})",
        )
        check("report à nouveau retiré (111 = 0)", close_to(balances.get("111", 0), 0))

        await ohada.close_fiscal_year(company_id, year_id)
        balances = await balances_map()
        check(
            "re-clôture : report à nouveau (111 = -600 000)",
            close_to(balances.get("111", 0), -600_000),
        )
        check("re-clôture : résultat soldé (121 = 0)", close_to(balances.get("121", 0), 0))

        from sqlalchemy import func

        from app.modules.accounting.models.journal_entry import JournalEntry

        dupes = (
            await session.execute(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.source_type.in_(
                        ["fiscal_year_closing", "fiscal_year_opening"]
                    ),
                )
            )
        ).scalar_one()
        check(
            "aucun doublon d'écriture de clôture (2 écritures au total)",
            dupes == 2,
            f"(obtenu {dupes})",
        )

    await engine.dispose()
    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)

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
