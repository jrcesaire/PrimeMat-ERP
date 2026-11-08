"""
Test fonctionnel — Achat de quincaillerie saisi depuis le PoS (PRD US5).

Vérifie, sur une base SQLite temporaire, que la saisie d'un achat comptoir
depuis le Point de Vente :

1. **crée une facture fournisseur réglée** (module Achats global) et la
   comptabilise — ``D 601 + D 4452 / C 401`` puis ``D 401 / C 531`` ;
2. **déduit correctement la TVA** d'un montant saisi TTC (taux 18 %) ;
3. **n'applique aucune TVA** quand le taux est à 0 (pas de ligne 4452) ;
4. **laisse la dette ouverte** quand l'achat n'est pas réglé (``paid=False``) :
   facture ``posted``, solde 401 = montant TTC, caisse inchangée ;
5. **décaissse la banque** (511) pour un règlement autre qu'en espèces ;
6. **rattache l'achat au fournisseur** dans le grand livre (tiers sur les
   lignes 601 / 4452 / 401) ;
7. **refuse** un montant nul ou négatif et un libellé vide.

Usage : ``python backend/test_pos_purchase.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_pos_purchase.db"
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


def close_to(value: float, expected: float, tol: float = 0.02) -> bool:
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

    from sqlalchemy import func, select

    from app.core.models.company import Company
    from app.core.services.seed_service import bootstrap_defaults
    from app.modules.accounting.models.journal_entry import JournalEntryLine
    from app.modules.accounting.schemas.ohada import FiscalYearCreate
    from app.modules.accounting.services.journal_service import LedgerService
    from app.modules.accounting.services.ohada import OHADAService
    from app.modules.purchases.schemas import PosPurchaseCreate, SupplierCreate
    from app.modules.purchases.services.supplier_invoice_service import (
        SupplierInvoiceService,
    )
    from app.modules.purchases.services.supplier_service import SupplierService

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await bootstrap_defaults(
            session,
            company_name="Test PoS SARL",
            company_code="TPO",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="pos@test.ci",
            admin_password="MotDePasse@123",
        )
        company = (
            await session.execute(select(Company).where(Company.code == "TPO"))
        ).scalar_one()
        company_id = company.id

        ohada = OHADAService(session)
        await ohada.create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )

        # Fournisseur de quincaillerie utilisé pour tous les achats du test.
        supplier = await SupplierService(session).create_supplier(
            SupplierCreate(name="Quincaillerie du Plateau", code="QUI-001"),
            company_id,
        )

        invoices = SupplierInvoiceService(session)
        ledger = LedgerService(session)

        async def balances() -> dict[str, float]:
            rows = await ledger.account_balances(company_id)
            return {b["account_code"]: float(b["balance"]) for b in rows}

        # -------------------------------------------------------------- #
        # 1. Achat réglé en espèces, avec TVA 18 %
        # -------------------------------------------------------------- #
        print("[1] Achat de quincaillerie réglé en espèces (TVA 18 %)")
        purchase = await invoices.create_pos_purchase(
            PosPurchaseCreate(
                supplier_id=supplier.id,
                label="Quincaillerie — vis, pointes et ciment",
                amount_total=120_000,
                tax_rate=18,
                purchase_date=date(2026, 5, 12),
                payment_method="cash",
            ),
            company_id,
        )
        check(
            "facture fournisseur créée (référence FAF…)",
            purchase.reference.startswith("FAF"),
            f"({purchase.reference})",
        )
        check(
            "achat réglé immédiatement (statut paid)",
            purchase.status == "paid",
            f"({purchase.status})",
        )
        check(
            "base HT = 101 694,92",
            close_to(purchase.amount_untaxed, 101_694.92),
            f"({purchase.amount_untaxed})",
        )
        check(
            "TVA déductible = 18 305,08",
            close_to(purchase.tax_amount, 18_305.08),
            f"({purchase.tax_amount})",
        )
        check(
            "montant TTC = 120 000,00 (HT + TVA)",
            close_to(purchase.amount_total, 120_000.00),
            f"({purchase.amount_total})",
        )
        check(
            "HT + TVA == TTC au centime (équilibre de l'écriture)",
            close_to(
                purchase.amount_untaxed + purchase.tax_amount,
                purchase.amount_total,
                0.0001,
            ),
        )
        check(
            "reste dû soldé",
            close_to(purchase.amount_due, 0),
            f"({purchase.amount_due})",
        )

        b = await balances()
        check(
            "grand livre : 601 (achats) débité de 101 694,92",
            close_to(b.get("601000", 0), 101_694.92),
            f"({b.get('601')})",
        )
        check(
            "grand livre : 4452 (TVA déductible) débité de 18 305,08",
            close_to(b.get("445000", 0), 18_305.08),
            f"({b.get('4452')})",
        )
        check(
            "grand livre : 401 (fournisseurs) soldé après règlement",
            close_to(b.get("401000", 0), 0),
            f"({b.get('401')})",
        )
        check(
            "grand livre : 531 (caisse) crédité de 120 000",
            close_to(b.get("571000", 0), -120_000),
            f"({b.get('531')})",
        )

        # Rattachement du tiers (fournisseur) sur les lignes de l'achat.
        partner_lines = (
            await session.execute(
                select(func.count(JournalEntryLine.id)).where(
                    JournalEntryLine.company_id == company_id,
                    JournalEntryLine.partner_id == supplier.id,
                    JournalEntryLine.account_code.in_(["601000", "445000", "401000"]),
                )
            )
        ).scalar_one()
        check(
            "grand livre : achat rattaché au fournisseur (601 / 4452 / 401)",
            partner_lines >= 3,
            f"({partner_lines} lignes)",
        )


        # -------------------------------------------------------------- #
        # 2. Achat sans TVA (taux 0)
        # -------------------------------------------------------------- #
        print("\n[2] Achat sans TVA (taux 0 %)")
        no_tax = await invoices.create_pos_purchase(
            PosPurchaseCreate(
                supplier_id=supplier.id,
                label="Sacs de ciment (fournisseur non assujetti)",
                amount_total=50_000,
                tax_rate=0,
                purchase_date=date(2026, 5, 12),
            ),
            company_id,
        )
        check("aucune TVA sur la facture", close_to(no_tax.tax_amount, 0))
        check(
            "montant HT = montant TTC (50 000)",
            close_to(no_tax.amount_untaxed, 50_000)
            and close_to(no_tax.amount_total, 50_000),
            f"({no_tax.amount_untaxed} / {no_tax.amount_total})",
        )
        b = await balances()
        check(
            "grand livre : 601 porté à 151 694,92",
            close_to(b.get("601000", 0), 151_694.92),
            f"({b.get('601')})",
        )
        check(
            "grand livre : 4452 inchangé (aucune TVA)",
            close_to(b.get("445000", 0), 18_305.08),
            f"({b.get('4452')})",
        )
        check(
            "grand livre : caisse créditée de 170 000 au total",
            close_to(b.get("571000", 0), -170_000),
            f"({b.get('531')})",
        )

        # -------------------------------------------------------------- #
        # 3. Achat non réglé : dette fournisseur laissée ouverte
        # -------------------------------------------------------------- #
        print("\n[3] Achat non réglé (dette fournisseur ouverte)")
        unpaid = await invoices.create_pos_purchase(
            PosPurchaseCreate(
                supplier_id=supplier.id,
                label="Fournitures diverses — à régler",
                amount_total=30_000,
                purchase_date=date(2026, 5, 13),
                paid=False,
            ),
            company_id,
        )
        check(
            "facture comptabilisée mais non réglée (statut posted)",
            unpaid.status == "posted",
            f"({unpaid.status})",
        )
        b = await balances()
        check(
            "grand livre : 401 crédité de 30 000 (dette ouverte)",
            close_to(b.get("401000", 0), -30_000),
            f"({b.get('401')})",
        )
        check(
            "grand livre : caisse inchangée (170 000)",
            close_to(b.get("571000", 0), -170_000),
            f"({b.get('531')})",
        )


        # -------------------------------------------------------------- #
        # 4. Règlement par mobile money : décaissement de la banque
        # -------------------------------------------------------------- #
        print("\n[4] Achat réglé par mobile money (banque 511)")
        mobile = await invoices.create_pos_purchase(
            PosPurchaseCreate(
                supplier_id=supplier.id,
                label="Quincaillerie urgente (mobile money)",
                amount_total=11_800,
                tax_rate=18,
                purchase_date=date(2026, 5, 14),
                payment_method="mobile_money",
            ),
            company_id,
        )
        check(
            "achat réglé (statut paid)",
            mobile.status == "paid",
            f"({mobile.status})",
        )
        check(
            "ventilation 10 000 HT / 1 800 TVA",
            close_to(mobile.amount_untaxed, 10_000)
            and close_to(mobile.tax_amount, 1_800),
            f"({mobile.amount_untaxed} / {mobile.tax_amount})",
        )
        b = await balances()
        check(
            "grand livre : 511 (banque) créditée de 11 800",
            close_to(b.get("521000", 0), -11_800),
            f"({b.get('511')})",
        )
        check(
            "grand livre : caisse (531) non touchée",
            close_to(b.get("571000", 0), -170_000),
            f"({b.get('531')})",
        )

        # -------------------------------------------------------------- #
        # 5. Garde-fous
        # -------------------------------------------------------------- #
        print("\n[5] Garde-fous")
        from pydantic import ValidationError

        def rejects(**kwargs) -> bool:
            """Le schéma refuse-t-il cette saisie ?"""
            payload = {
                "supplier_id": supplier.id,
                "label": "Test",
                "amount_total": 1_000,
            }
            payload.update(kwargs)
            try:
                PosPurchaseCreate(**payload)
            except ValidationError:
                return True
            return False

        check("montant nul refusé", rejects(amount_total=0))
        check("montant négatif refusé", rejects(amount_total=-500))
        check("libellé vide refusé", rejects(label=""))
        check("taux de TVA > 100 refusé", rejects(tax_rate=150))
        check("saisie valide acceptée", not rejects())

        double_post_rejected = False
        try:
            await invoices.post(purchase.id)
        except ValueError:
            double_post_rejected = True
        check(
            "double comptabilisation refusée (facture déjà enregistrée)",
            double_post_rejected,
        )

        # L'achat est bien visible dans la liste du module Achats global.
        listed = await invoices.list_invoices(limit=50)
        check(
            "achat visible dans le module Achats global",
            any(inv.id == purchase.id for inv in listed),
            f"({len(listed)} factures)",
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

