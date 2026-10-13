"""
Test des modes de vente par catégorie : unit / length / dual (solin).

Valide :
- dérivation automatique de sell_by_length / sale_mode depuis la catégorie
- validations des prix selon le mode
- vente BAC par sous-lignes (longueur + quantité de pièces)
- vente à la pièce standard au prorata du ml (solin de rive)
- rejets (coupes sur produit unitaire, BAC vendu à la pièce…)
- héritage du mode par les sous-catégories
- arborescence des catégories (tree)
"""
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

DB_FILE = "test_sale_modes.db"
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
    from app.core.models.company import Company

    import app.core.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    engine = create_async_engine(DB_URL)
    # Nettoyage préalable (un run précédent en échec peut laisser la base)
    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        company = Company(name="Test SARL", code="TST", currency_code="XOF")
        session.add(company)
        await session.flush()

        from app.modules.crm.models.partner import Partner
        client = Partner(company_id=company.id, name="Client Test", role="client")
        session.add(client)
        await session.flush()

        await run_tests(session, company.id, client.id, check)

    await engine.dispose()
    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)

    print()
    if failures:
        print(f"{len(failures)} ÉCHECS : {failures}")
        return 1
    print("TOUS LES TESTS MODES DE VENTE PASSENT ✔")
    return 0


async def run_tests(session, company_id, client_id, check) -> None:
    from sqlalchemy import select

    from app.modules.catalogue.models.product import ProductCategory
    from app.modules.catalogue.services.category_seed import seed_categories
    from app.modules.catalogue.services.product_service import CatalogueService
    from app.modules.catalogue.schemas import ProductCreate

    await seed_categories(session, company_id)
    await session.flush()

    result = await session.execute(select(ProductCategory))
    cat_ids = {c.code: c.id for c in result.scalars().all()}

    svc = CatalogueService(session)

    # 1. Tôle BAC Alu → length : sell_by_length forcé, prix/m requis
    bac = await svc.create_product(ProductCreate(
        reference="BAC-ALU-030", name="Tôle BAC Alu 0,30",
        category_id=cat_ids["TOIT-BAC-ALU"],
        price_per_meter=4200,
    ))
    check("Tôle BAC Alu : sell_by_length auto = True", bac.sell_by_length is True)
    check("Tôle BAC Alu : sale_mode résolu = length", bac.sale_mode == "length")
    check("Tôle BAC Alu : is_bac_sheet = True", bac.is_bac_sheet is True)

    # 2. Tôle BAC sans prix/m → rejet
    rejected = False
    try:
        await svc.create_product(ProductCreate(
            reference="BAC-X", name="Tôle BAC sans prix",
            category_id=cat_ids["TOIT-BAC"],
        ))
    except ValueError:
        rejected = True
    check("Tôle BAC sans price_per_meter → rejetée", rejected)

    # 3. Tôle ondulée (unit) : forcé False, prix pièce requis, prix/m nettoyé
    ond = await svc.create_product(ProductCreate(
        reference="OND-250", name="Tôle ondulée 2,50 m",
        category_id=cat_ids["TOIT-OND"],
        selling_price=15000,
        price_per_meter=9999,  # doit être ignoré/nettoyé
    ))
    check("Tôle ondulée : sell_by_length auto = False", ond.sell_by_length is False)
    check("Tôle ondulée : price_per_meter nettoyé", ond.price_per_meter is None)
    check("Tôle ondulée : sale_mode = unit", ond.sale_mode == "unit")

    # 4. Solin de rive (dual)
    solin = await svc.create_product(ProductCreate(
        reference="SOL-RIV", name="Solin de rive",
        category_id=cat_ids["TOIT-ACC-SOLIN"],
        price_per_meter=1800, unit_length=2.5,
    ))
    check("Solin de rive : sell_by_length auto = True (dual)",
          solin.sell_by_length is True)
    check("Solin de rive : sale_mode résolu = dual", solin.sale_mode == "dual")

    await test_sales_lines(session, client_id, bac, ond, solin, check)
    await test_inheritance_and_tree(session, svc, company_id, check)


async def test_sales_lines(session, client_id, bac, ond, solin, check) -> None:
    from app.modules.sales.services.quote_service import QuoteService
    from app.modules.sales.schemas import QuoteCreate, QuoteLineCreate

    qs = QuoteService(session)

    # 5a. Vente BAC par sous-lignes (longueur + quantité de pièces)
    q1 = await qs.create_quote(QuoteCreate(
        partner_id=client_id,
        lines=[QuoteLineCreate(
            product_id=bac.id, description="Tôle BAC Alu",
            sell_by_length=True, unit_price=4200,
            cuts=[
                {"quantity": 10, "length": 5.5},
                {"quantity": 4, "length": 3.0},
            ],
        )],
    ))
    l1 = q1.lines[0]
    check("BAC : longueur totale = 67 m (10×5,5 + 4×3)",
          float(l1.total_length) == 67.0)
    check("BAC : sous-total = 281 400 (67 × 4 200)",
          float(l1.subtotal) == 281400.0)
    check("BAC : 2 sous-lignes longueur conservées", len(l1.cuts) == 2)

    # 5b. Solin à la pièce standard → prorata ml (10 × 2,5 × 1 800 = 45 000)
    q2 = await qs.create_quote(QuoteCreate(
        partner_id=client_id,
        lines=[QuoteLineCreate(
            product_id=solin.id, description="Solin de rive",
            quantity=10,
        )],
    ))
    l2 = q2.lines[0]
    check("Solin pièce : converti en coupe 10 × 2,5",
          len(l2.cuts) == 1 and float(l2.cuts[0].length) == 2.5)
    check("Solin pièce : total_length = 25 m", float(l2.total_length) == 25.0)
    check("Solin pièce : sous-total = 45 000 (prorata ml)",
          float(l2.subtotal) == 45000.0)

    # 5c. Solin au ml sur mesure (12 × 1 800 = 21 600)
    q3 = await qs.create_quote(QuoteCreate(
        partner_id=client_id,
        lines=[QuoteLineCreate(
            product_id=solin.id, description="Solin sur mesure",
            sell_by_length=True, unit_price=1800,
            cuts=[{"quantity": 1, "length": 12.0}],
        )],
    ))
    check("Solin au ml : sous-total = 21 600",
          float(q3.lines[0].subtotal) == 21600.0)

    # 5d. Coupes sur produit unitaire → rejet
    rej1 = False
    try:
        await qs.create_quote(QuoteCreate(
            partner_id=client_id,
            lines=[QuoteLineCreate(
                product_id=ond.id, sell_by_length=True,
                cuts=[{"quantity": 1, "length": 2.0}],
            )],
        ))
    except ValueError:
        rej1 = True
    check("Coupes sur produit unitaire → rejetées", rej1)

    # 5e. Vente à l'unité d'un produit unit → acceptée (5 × 15 000)
    q4 = await qs.create_quote(QuoteCreate(
        partner_id=client_id,
        lines=[QuoteLineCreate(product_id=ond.id, quantity=5)],
    ))
    check("Vente à l'unité produit unit → acceptée (75 000)",
          float(q4.lines[0].subtotal) == 75000.0)

    # 5f. Tôle BAC vendue à la pièce → rejet
    rej3 = False
    try:
        await qs.create_quote(QuoteCreate(
            partner_id=client_id,
            lines=[QuoteLineCreate(product_id=bac.id, quantity=5)],
        ))
    except ValueError:
        rej3 = True
    check("Tôle BAC vendue à la pièce → rejetée", rej3)


async def test_inheritance_and_tree(session, svc, company_id, check) -> None:
    from sqlalchemy import select

    from app.modules.catalogue.models.product import ProductCategory

    parent_id = (await session.execute(
        select(ProductCategory.id).where(
            ProductCategory.code == "TOIT-BAC",
            ProductCategory.company_id == company_id,
        )
    )).scalar_one()

    new_sub = ProductCategory(
        name="Tôle BAC 3 ondes", code="TOIT-BAC-3O",
        parent_id=parent_id,
        company_id=company_id,
    )
    session.add(new_sub)
    await session.flush()
    mode = await new_sub.resolve_sale_mode(session)
    check("Sous-cat fille de Tôles BAC hérite du mode length",
          mode.value == "length")

    tree = await svc.build_category_tree()
    toit = next((n for n in tree if n["code"] == "TOIT"), None)
    children = {c["code"]: c for c in (toit or {}).get("children", [])}
    check("Arbre : Tôles BAC sells_by_length=True",
          bool(children.get("TOIT-BAC", {}).get("sells_by_length")))
    check("Arbre : Accessoires de tôlerie mode dual",
          children.get("TOIT-ACC", {}).get("resolved_sale_mode") == "dual")
    check("Arbre : 36 catégories racines présentes", len(tree) >= 36)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))