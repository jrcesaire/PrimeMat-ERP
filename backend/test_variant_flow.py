"""
Test E2E — variante de produit sur les lignes des documents commerciaux.

Parcours : devis → commande → facture + bon de livraison + vente comptoir.

Valide :
- validation de la variante (propriétaire + actif) et prix par défaut repris
  de la variante plutôt que du produit de base ;
- instantané de ``variant_name`` résolu côté serveur (jamais depuis le client) ;
- propagation du couple (variant_id, variant_name) à chaque conversion ;
- rendu HTML (devis / facture / BL / ticket POS) avec badge de variante,
  y compris après renommage de la variante (l'instantané doit survivre).

Usage : ``python test_variant_flow.py`` (crée puis supprime sa base SQLite).
"""
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

DB_FILE = "test_variant_flow.db"
DB_URL = f"sqlite+aiosqlite:///./{DB_FILE}"
# À définir AVANT tout import de app.* : ContextBuilder construit les contextes
# de rendu via AsyncSessionLocal, qui doit pointer sur la base de test.
os.environ["DATABASE_URL"] = DB_URL

VARIANT_SUFFIX = "Rouleau 25 m"
RENAME_SUFFIX = "Rouleau 30 m (renomme)"

failures = []


def check(label, cond):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {label}")
    if not cond:
        failures.append(label)


async def main() -> int:
    from app.core.database import AsyncSessionLocal, Base, engine
    from app.core.models.company import Company

    import app.core.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401
    import app.modules.invoicing.models  # noqa: F401
    import app.modules.delivery.models  # noqa: F401

    db_path = os.path.join(BACKEND, DB_FILE)
    if os.path.exists(db_path):
        os.remove(db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ------------------------------------------------------------------ #
    # Fixtures : entreprise, client, produit + variantes
    # ------------------------------------------------------------------ #
    async with AsyncSessionLocal() as session:
        from app.modules.crm.models.partner import Partner
        from app.modules.catalogue.models.product import Product
        from app.modules.catalogue.models.variant import ProductVariant

        company = Company(name="Test Variante SARL", code="TVAR",
                          currency_code="XOF")
        session.add(company)
        await session.flush()
        cid = company.id

        partner = Partner(name="Client Variante", company_id=cid)
        product = Product(
            reference="TOL-BAC-40", name="Tôle bac 40/40", sale_mode="unit",
            selling_price=1000, price_per_meter=500, company_id=cid,
        )
        other = Product(
            reference="CIM-50", name="Ciment CPJ 45", sale_mode="unit",
            selling_price=2500, company_id=cid,
        )
        session.add_all([partner, product, other])
        await session.flush()

        variant = ProductVariant(
            product_id=product.id, name_suffix=VARIANT_SUFFIX,
            reference="TOL-BAC-40-R25", selling_price=1500,
            price_per_meter=750, is_default=True, company_id=cid,
        )
        orphan = ProductVariant(
            product_id=other.id, name_suffix="Sac 50 kg",
            selling_price=2750, company_id=cid,
        )
        inactive = ProductVariant(
            product_id=product.id, name_suffix="Variante inactive",
            selling_price=9999, is_active=False, company_id=cid,
        )
        session.add_all([variant, orphan, inactive])
        await session.commit()

        ids = {
            "product": product.id, "other": other.id,
            "variant": variant.id, "orphan": orphan.id,
            "inactive": inactive.id, "partner": partner.id, "company": cid,
        }

    # ------------------------------------------------------------------ #
    # 1. Devis : validations + création avec variante
    # ------------------------------------------------------------------ #
    from app.modules.sales.schemas import QuoteCreate, QuoteLineCreate
    from app.modules.sales.services.quote_service import QuoteService

    async with AsyncSessionLocal() as session:
        svc = QuoteService(session)

        # Variante d'un AUTRE produit → refus
        try:
            await svc.create_quote(QuoteCreate(
                partner_id=ids["partner"],
                lines=[QuoteLineCreate(product_id=ids["product"],
                                       variant_id=ids["orphan"])],
            ))
            check("Refus variante appartenant à un autre produit", False)
        except ValueError:
            check("Refus variante appartenant à un autre produit", True)

        # Variante inactive → refus
        try:
            await svc.create_quote(QuoteCreate(
                partner_id=ids["partner"],
                lines=[QuoteLineCreate(product_id=ids["product"],
                                       variant_id=ids["inactive"])],
            ))
            check("Refus variante inactive", False)
        except ValueError:
            check("Refus variante inactive", True)

        # Création valide : unit_price omis (0) → prix de la variante
        quote = await svc.create_quote(QuoteCreate(
            partner_id=ids["partner"],
            lines=[QuoteLineCreate(product_id=ids["product"],
                                   variant_id=ids["variant"], quantity=2)],
        ))
        line = quote.lines[0]
        check("Devis : variant_id mémorisé",
              line.variant_id == ids["variant"])
        check("Devis : variant_name résolu côté serveur",
              line.variant_name == VARIANT_SUFFIX)
        check("Devis : prix par défaut repris de la variante",
              float(line.unit_price) == 1500.0)
        check("Devis : sous-total recalculé avec le prix de la variante",
              float(line.subtotal) == 3000.0)
        quote_id = quote.id

        # Confirmation → commande
        order = await svc.confirm_quote(quote_id)
        oline = order.lines[0]
        check("Commande : variant_id propagé depuis le devis",
              oline.variant_id == ids["variant"])
        check("Commande : variant_name propagé depuis le devis",
              oline.variant_name == VARIANT_SUFFIX)
        order_id = order.id

    # ------------------------------------------------------------------ #
    # 2. Facture, bon de livraison et vente comptoir depuis la commande
    # ------------------------------------------------------------------ #
    async with AsyncSessionLocal() as session:
        from app.modules.invoicing.services.invoice_service import (
            InvoiceService,
        )
        invoice = await InvoiceService(session).create_from_order(order_id)
        iline = invoice.lines[0]
        check("Facture : variant_id propagé", iline.variant_id == ids["variant"])
        check("Facture : variant_name propagé",
              iline.variant_name == VARIANT_SUFFIX)

        from app.modules.delivery.services.delivery_service import (
            DeliveryService,
        )
        delivery = await DeliveryService(session).create_from_order(order_id)
        dline = delivery.lines[0]
        check("Bon de livraison : variant_id propagé",
              dline.variant_id == ids["variant"])
        check("Bon de livraison : variant_name propagé",
              dline.variant_name == VARIANT_SUFFIX)

        invoice_id, delivery_id = invoice.id, delivery.id

        # Vente comptoir (ticket POS 80 mm) avec variante
        from app.modules.sales.schemas import OrderLineCreate, SalesOrderCreate
        from app.modules.sales.services.order_service import OrderService

        pos_order = await OrderService(session).create_order(SalesOrderCreate(
            partner_id=ids["partner"], fulfillment_mode="pos",
            lines=[OrderLineCreate(product_id=ids["product"],
                                   variant_id=ids["variant"], quantity=1)],
        ))
        pos_id = pos_order.id
        pos_line = pos_order.lines[0]
        check("Comptoir : variant_id mémorisé",
              pos_line.variant_id == ids["variant"])
        check("Comptoir : variant_name résolu côté serveur",
              pos_line.variant_name == VARIANT_SUFFIX)

    # ------------------------------------------------------------------ #
    # 3. Instantané : renommer la variante ne doit pas modifier les docs
    # ------------------------------------------------------------------ #
    async with AsyncSessionLocal() as session:
        from app.modules.catalogue.models.variant import ProductVariant
        v = await session.get(ProductVariant, ids["variant"])
        v.name_suffix = RENAME_SUFFIX
        await session.commit()


    # ------------------------------------------------------------------ #
    # 4. Rendu HTML des documents (contextes construits depuis la BDD)
    # ------------------------------------------------------------------ #
    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    docs = DocumentEngine()
    builder = ContextBuilder()

    async def render_ctx(get_ctx, template_name: str) -> str:
        """Construit le contexte (async, via BDD) puis rend le template."""
        return docs.render_to_html(template_name, await get_ctx())

    quote_html = await render_ctx(
        lambda: builder.build_quote_context(quote_id), "quote.html")
    check("Rendu devis : badge de variante présent",
          "variant-tag" in quote_html)
    check("Rendu devis : libellé d'origine affiché (instantané)",
          VARIANT_SUFFIX in quote_html)
    check("Rendu devis : libellé renommé NON affiché",
          RENAME_SUFFIX not in quote_html)

    invoice_html = await render_ctx(
        lambda: builder.build_invoice_context(invoice_id), "invoice.html")
    check("Rendu facture : badge de variante présent",
          "variant-tag" in invoice_html)
    check("Rendu facture : libellé d'origine affiché (instantané)",
          VARIANT_SUFFIX in invoice_html)

    delivery_html = await render_ctx(
        lambda: builder.load_delivery(delivery_id), "delivery.html")
    check("Rendu bon de livraison : badge de variante présent",
          "variant-tag" in delivery_html)
    check("Rendu bon de livraison : libellé d'origine affiché (instantané)",
          VARIANT_SUFFIX in delivery_html)

    pos_html = await render_ctx(
        lambda: builder.load_pos(pos_id), "pos_ticket.html")
    check("Rendu ticket POS : libellé de variante en ligne",
          VARIANT_SUFFIX in pos_html)

    return 1 if failures else 0


if __name__ == "__main__":
    code = asyncio.run(main())
    print("\n" + "=" * 60)
    if failures:
        print(f"ÉCHEC — {len(failures)} contrôle(s) en échec :")
        for f in failures:
            print(f"  - {f}")
    else:
        print("SUCCÈS — tous les contrôles sont passés")
    print("=" * 60)
    sys.exit(code)

