"""
Test de fumée — logique métier principale sur SQLite en mémoire.

Valide : création des tables, calcul BAC multi-longueurs,
devis → commande (coupes préservées), fulfillment hybride, réservations.
"""
import asyncio
import os
import sys

# Console Windows : force l'UTF-8 pour les caractères spéciaux
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND = r"D:\Travail\Projets\JR\ERP Matériaux de construction\backend"
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

DB_FILE = "test_smoke.db"
DB_URL = f"sqlite+aiosqlite:///./{DB_FILE}"

failures = []


def check(label, cond):
    status_ok = "OK " if cond else "FAIL"
    print(f"[{status_ok}] {label}")
    if not cond:
        failures.append(label)


async def main() -> int:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.core.database import Base

    engine = create_async_engine(DB_URL)

    import app.core.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        await run_business_tests(session, check)

    await engine.dispose()
    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)

    print()
    if failures:
        print(f"{len(failures)} ÉCHECS :", failures)
        return 1
    print("TOUS LES TESTS PASSENT ✔")
    return 0


async def run_business_tests(session, check) -> None:
    """Scénario complet : produits → devis BAC → commande → fulfillment."""
    from sqlalchemy import select

    from app.core.models.company import Company
    company = Company(name="Test SARL", code="TST", currency_code="XOF")
    session.add(company)
    await session.flush()

    from app.modules.catalogue.models.product import Product
    cement = Product(
        company_id=company.id,
        reference="CIM-50", name="Ciment 50kg",
        storage_type="stockable", selling_price=5000,
        purchase_price=4200,
    )
    bac = Product(
        company_id=company.id,
        reference="BAC-U115", name="Tôle BAC U115",
        storage_type="on_demand", sell_by_length=True,
        price_per_meter=3500,
    )
    session.add_all([cement, bac])
    await session.flush()

    from app.modules.crm.models.partner import Partner
    client = Partner(company_id=company.id, name="Entreprise ABC", role="client")
    session.add(client)
    await session.flush()

    # Devis avec ligne BAC multi-longueurs :
    # 10×5.50m + 20×4.50m + 15×3.00m = 190 m @ 3500/m
    from app.modules.sales.services.quote_service import QuoteService
    from app.modules.sales.schemas import QuoteCreate, QuoteLineCreate

    qs = QuoteService(session)
    quote = await qs.create_quote(QuoteCreate(
        partner_id=client.id,
        lines=[
            QuoteLineCreate(
                product_id=cement.id, description="Ciment",
                quantity=100, unit_price=5000,
            ),
            QuoteLineCreate(
                product_id=bac.id, description="Tôle BAC Profil X",
                sell_by_length=True, unit_price=3500,
                cuts=[
                    {"quantity": 10, "length": 5.5, "unit_price": 3500},
                    {"quantity": 20, "length": 4.5, "unit_price": 3500},
                    {"quantity": 15, "length": 3.0, "unit_price": 3500},
                ],
            ),
        ],
    ))

    check(f"Devis créé : {quote.reference}", quote.reference.startswith("DEV"))
    total_expected = 100 * 5000 + 190 * 3500
    check(f"Total devis = {float(quote.amount_total)} (attendu {total_expected})",
          float(quote.amount_total) == total_expected)

    # Recharge le devis avec ses lignes (lazy-load async safe)
    from app.modules.sales.models.quote import Quote as QuoteModel
    res = await session.execute(select(QuoteModel).where(QuoteModel.id == quote.id))
    quote = res.scalar_one()

    bac_line = [l for l in quote.lines if l.sell_by_length][0]
    check(f"Ligne BAC longueur totale = {float(bac_line.total_length)} m (attendu 190)",
          float(bac_line.total_length) == 190.0)
    check(f"Ligne BAC sous-total = {float(bac_line.subtotal)} (attendu {190*3500})",
          float(bac_line.subtotal) == 190 * 3500)
    check("3 coupes BAC conservées", len(bac_line.cuts) == 3)

    # Devis → Commande : les coupes ne sont jamais perdues
    order = await qs.confirm_quote(quote.id)
    check(f"Commande créée : {order.reference}", order.reference.startswith("COM"))

    # Recharge la commande avec ses lignes
    from app.modules.sales.models.order import SalesOrder as OrderModel
    res = await session.execute(select(OrderModel).where(OrderModel.id == order.id))
    order = res.scalar_one()

    o_bac = [l for l in order.lines if l.sell_by_length][0]
    check(f"Commande : coupes BAC préservées ({len(o_bac.cuts)})",
          len(o_bac.cuts) == 3)
    check(f"Commande : montant {float(order.amount_total)} (attendu {total_expected})",
          float(order.amount_total) == total_expected)

    # Entrepôt, stock et fulfillment hybride
    await test_stock_and_fulfillment(session, cement, bac, order, check)


async def test_stock_and_fulfillment(session, cement, bac, order, check):
    """Entrepôt, stock et analyse de fulfillment hybride."""
    from app.modules.stock.models.inventory import Warehouse
    wh = Warehouse(company_id=cement.company_id, name="Entrepôt principal", code="WH1")
    session.add(wh)
    await session.flush()

    from app.modules.stock.services.stock_service import StockService
    ss = StockService(session)
    await ss.record_movement(
        movement_type="inbound", warehouse_id=wh.id,
        product_id=cement.id, quantity=80, unit_cost=4200,
        reference_document="PO-1",
    )
    avail = await ss.get_available_stock(cement.id)
    check(f"Stock ciment disponible = {avail} (attendu 80)", avail == 80.0)

    from app.modules.sales.services.order_service import OrderService
    osvc = OrderService(session)
    analysis = await osvc.analyze_fulfillment(order.id)

    check(f"Fulfillment : réservations={len(analysis['reservations'])} (attendu 1)",
          len(analysis["reservations"]) == 1)
    check(f"Fulfillment : besoins achat={len(analysis['purchase_needs'])} (attendu 2)",
          len(analysis["purchase_needs"]) == 2)

    res = analysis["reservations"][0]
    check(f"Réservation ciment = {res['quantity']} (attendu 80)",
          res["quantity"] == 80.0)
    needs_by_product = {n["product_id"]: n["quantity"] for n in analysis["purchase_needs"]}
    check(f"Besoin achat ciment = {needs_by_product.get(cement.id)} (attendu 20)",
          needs_by_product.get(cement.id) == 20.0)
    check(f"Besoin achat BAC = {needs_by_product.get(bac.id)} (attendu 190)",
          needs_by_product.get(bac.id) == 190.0)

    avail_after = await ss.get_available_stock(cement.id)
    check(f"Stock dispo après réservation = {avail_after} (attendu 0)",
          avail_after == 0.0)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))