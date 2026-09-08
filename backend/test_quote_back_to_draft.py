"""
Test E2E — parcours devis :
créer → confirmer → remettre au brouillon → modifier → supprimer.

Valide aussi le refus de back-to-draft si une facture est liée.
"""
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND = r"D:\Travail\Projets\JR\ERP Matériaux de construction\backend"
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

DB_FILE = "test_quote_btd.db"
DB_URL = f"sqlite+aiosqlite:///./{DB_FILE}"

failures = []


def check(label, cond):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {label}")
    if not cond:
        failures.append(label)


async def main() -> int:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.core.models.company import Company

    import app.core.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401
    import app.modules.invoicing.models  # noqa: F401
    import app.modules.delivery.models  # noqa: F401

    engine = create_async_engine(DB_URL)
    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        from app.modules.crm.models.partner import Partner
        from app.modules.sales.services.quote_service import QuoteService
        from app.modules.sales.schemas import QuoteCreate, QuoteLineCreate, QuoteUpdate
        from app.modules.sales.models.order import SalesOrder
        from app.modules.invoicing.models.invoice import Invoice

        company = Company(name="Test BTB SARL", code="BTB", currency_code="XOF")
        session.add(company)
        await session.flush()
        cid = company.id

        partner = Partner(name="Client A", company_id=cid)
        session.add(partner)
        await session.flush()

        svc = QuoteService(session)

        quote = await svc.create_quote(QuoteCreate(
            partner_id=partner.id,
            lines=[QuoteLineCreate(description="Ligne test", quantity=2, unit_price=100)],
        ))
        check("Devis créé au statut brouillon", quote.status == "draft")

        order = await svc.confirm_quote(quote.id)
        check("Confirmation → statut confirmed", quote.status == "confirmed")
        check("Confirmation → une commande générée", order is not None)

        # back-to-draft refuse si une facture est liée à la commande
        inv = Invoice(
            reference="INV-BTD", order_id=order.id,
            partner_id=partner.id, company_id=cid,
            amount_total=200, status="draft",
        )
        session.add(inv)
        await session.commit()
        try:
            await svc.back_to_draft(quote.id)
            check("Back-to-draft refusé si facture liée", False)
        except ValueError:
            check("Back-to-draft refusé si facture liée", True)
        await session.delete(inv)
        await session.commit()

        # Retour au brouillon une fois la facture retirée
        restored = await svc.back_to_draft(quote.id)
        check("Back-to-draft → statut brouillon", restored.status == "draft")

        # La commande liée est supprimée
        order_ids = (await session.execute(select(SalesOrder.id))).scalars().all()
        check("Commande liée supprimée", order.id not in order_ids)

        # Back-to-draft interdit sur un devis déjà brouillon
        try:
            await svc.back_to_draft(quote.id)
            check("Double back-to-draft (brouillon) refusé", False)
        except ValueError:
            check("Double back-to-draft (brouillon) refusé", True)

        # Re-modification possible après retour au brouillon
        updated = await svc.update_quote(quote.id, QuoteUpdate(notes="re-modifié"))
        check("Modification OK après retour au brouillon",
              updated.notes == "re-modifié" and updated.status == "draft")

        # Suppression
        await svc.delete_quote(quote.id)
        gone = await svc.get_quote(quote.id)
        check("Suppression après retour au brouillon", gone is None)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))