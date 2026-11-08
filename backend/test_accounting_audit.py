"""
Test fonctionnel — journal d'audit comptable (Lot F de la Phase 2).

Vérifie, sur une base SQLite temporaire, que la comptabilisation alimente le
journal d'audit :

1. **création** d'une écriture → une entrée ``journal_entry.created`` ;
2. **publication** → une entrée ``journal_entry.posted`` ;
3. **brouillon** (``post=False``) → une seule entrée (pas de publication) ;
4. **auteur** (``user_id``) et **valeurs** (référence, statut, montants,
   rattachement à l'exercice) correctement tracés ;
5. **immuabilité** : le journal n'est jamais modifié par une opération
   ultérieure.

Usage : ``python backend/test_accounting_audit.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_accounting_audit.db"
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

    from app.core.models.audit_log import AuditLog
    from app.core.models.company import Company
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
        await bootstrap_defaults(
            session,
            company_name="Test Audit SARL",
            company_code="TAU",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="audit@test.ci",
            admin_password="MotDePasse@123",
        )
        company = (
            await session.execute(select(Company).where(Company.code == "TAU"))
        ).scalar_one()
        company_id = company.id
        ledger = LedgerService(session)
        year = await OHADAService(session).create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )

        def payload(description: str) -> JournalEntryCreate:
            return JournalEntryCreate(
                entry_date=date(2026, 5, 10),
                journal_code="OD",
                description=description,
                lines=[
                    JournalEntryLineCreate(
                        account_code="601000", label="Achats", debit=100_000, credit=0
                    ),
                    JournalEntryLineCreate(
                        account_code="401000",
                        label="Fournisseur",
                        debit=0,
                        credit=100_000,
                    ),
                ],
            )

        async def audit_rows() -> list[AuditLog]:
            result = await session.execute(
                select(AuditLog)
                .where(AuditLog.company_id == company_id)
                .order_by(AuditLog.id)
            )
            return list(result.scalars().all())

        # --- 1. Écriture publiée : création + publication tracées ---
        print("[1] Écriture publiée (post=True)")
        entry = await ledger.create_entry(
            company_id, payload("Écriture publiée"), post=True, user_id=42
        )
        await session.commit()

        rows = await audit_rows()
        check("2 entrées d'audit", len(rows) == 2, f"({len(rows)})")
        check(
            "actions tracées dans l'ordre",
            [r.action for r in rows]
            == ["journal_entry.created", "journal_entry.posted"],
            f"({[r.action for r in rows]})",
        )
        check(
            "type d'entité = journal_entry",
            all(r.entity_type == "journal_entry" for r in rows),
        )
        check(
            "écriture ciblée",
            all(r.entity_id == entry.id for r in rows),
            f"({[r.entity_id for r in rows]} / {entry.id})",
        )
        check(
            "auteur tracé (user_id=42)",
            all(r.user_id == 42 for r in rows),
            f"({[r.user_id for r in rows]})",
        )
        values = rows[0].new_values or {}
        check("référence tracée", values.get("reference") == entry.reference)
        check("statut de création = draft", values.get("status") == "draft")
        check(
            "montant tracé (100 000)",
            abs(float(values.get("total_debit", 0)) - 100_000) < 0.01,
            f"({values.get('total_debit')})",
        )
        check(
            "exercice rattaché",
            values.get("fiscal_year_id") == year.id,
            f"({values.get('fiscal_year_id')} / {year.id})",
        )
        posted_values = rows[1].new_values or {}
        check(
            "statut de publication = posted",
            posted_values.get("status") == "posted",
        )

        # --- 2. Brouillon : seule la création est tracée ---
        print("\n[2] Brouillon (post=False)")
        draft = await ledger.create_entry(
            company_id, payload("Écriture brouillon"), post=False, user_id=7
        )
        await session.commit()
        rows = await audit_rows()
        check("3 entrées d'audit au total", len(rows) == 3, f"({len(rows)})")
        check(
            "dernière action = création",
            rows[-1].action == "journal_entry.created",
            f"({rows[-1].action})",
        )
        check("brouillon ciblé", rows[-1].entity_id == draft.id)
        check("auteur du brouillon tracé", rows[-1].user_id == 7)

        # --- 3. Publication différée du brouillon ---
        print("\n[3] Publication différée du brouillon")
        await ledger.post_entry(draft.id, company_id, user_id=7)
        await session.commit()
        rows = await audit_rows()
        check("4 entrées d'audit au total", len(rows) == 4, f"({len(rows)})")
        check(
            "action de publication tracée",
            rows[-1].action == "journal_entry.posted",
            f"({rows[-1].action})",
        )
        check("brouillon publié ciblé", rows[-1].entity_id == draft.id)

        # --- 4. Immuabilité ---
        print("\n[4] Immuabilité du journal")
        check(
            "les 2 premières entrées sont inchangées",
            [r.action for r in rows[:2]]
            == ["journal_entry.created", "journal_entry.posted"]
            and (rows[0].new_values or {}).get("status") == "draft",
        )
        check(
            "horodatage présent sur toutes les entrées",
            all(r.created_at is not None for r in rows),
        )

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
