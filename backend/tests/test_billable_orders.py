"""Non-régressions — commandes facturables et contrôle du statut.

Le formulaire de facturation utilisait auparavant deux listes générales
(commandes et factures), chacune limitée à 100 éléments, puis filtrait côté
navigateur. Une commande confirmée pouvait donc ne jamais être retournée.

Le filtre serveur dédié a ensuite été restreint au seul statut « confirmé » :
la liste déroulante se vidait alors que des commandes restaient à facturer,
car une commande issue d'un devis confirmé est créée **en brouillon**
(``QuoteService.confirm_quote``) puis facturée par le parcours « Créer facture »
de l'écran Ventes. Ce test verrouille le contrat :

* facturable = commande ni annulée ni retournée, avec un reste à facturer
  strictement positif ;
* ventes comptoir exclues (facturées au moment de la vente) ;
* ``create_from_order`` refuse une commande annulée / retournée, mais accepte
  une commande brouillon.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

import app.main  # noqa: F401 — enregistre tous les modèles SQLAlchemy
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.invoicing.models.invoice import Invoice
from app.modules.invoicing.services.invoice_service import (
    NON_BILLABLE_ORDER_STATUSES,
    InvoiceService,
)
from app.modules.sales.models.order import OrderLineCut, SalesOrder, SalesOrderLine


def test_commandes_facturables_filtrees_et_triees_avant_la_limite() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            tables = [
                SalesOrder.__table__,
                SalesOrderLine.__table__,
                OrderLineCut.__table__,
                Invoice.__table__,
            ]
            async with engine.begin() as connection:
                await connection.run_sync(
                    lambda sync: Base.metadata.create_all(sync, tables=tables)
                )

            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                orders = [
                    SalesOrder(
                        reference="CONF-NEW",
                        partner_id=1,
                        status="confirmed",
                        fulfillment_mode="stock",
                        order_date=date(2026, 11, 8),
                        amount_total=100,
                        company_id=1,
                    ),
                    SalesOrder(
                        reference="CONF-OLD",
                        partner_id=1,
                        status="confirmed",
                        fulfillment_mode="stock",
                        order_date=date(2026, 10, 1),
                        amount_total=80,
                        company_id=1,
                    ),
                    SalesOrder(
                        reference="CONF-PAID",
                        partner_id=1,
                        status="confirmed",
                        fulfillment_mode="stock",
                        order_date=date(2026, 10, 2),
                        amount_total=40,
                        company_id=1,
                    ),
                    SalesOrder(
                        reference="POS",
                        partner_id=1,
                        status="confirmed",
                        fulfillment_mode="pos",
                        order_date=date(2026, 11, 7),
                        amount_total=60,
                        company_id=1,
                    ),
                    SalesOrder(
                        reference="DRAFT",
                        partner_id=1,
                        status="draft",
                        fulfillment_mode="stock",
                        order_date=date(2026, 11, 6),
                        amount_total=70,
                        company_id=1,
                    ),
                    SalesOrder(
                        reference="CANCELLED",
                        partner_id=1,
                        status="cancelled",
                        fulfillment_mode="stock",
                        order_date=date(2026, 11, 9),
                        amount_total=50,
                        company_id=1,
                    ),
                ]
                session.add_all(orders)
                await session.flush()
                session.add_all(
                    [
                        Invoice(
                            reference="INV-PART",
                            order_id=orders[1].id,
                            partner_id=1,
                            status="draft",
                            invoice_date=date(2026, 10, 2),
                            currency_code="XOF",
                            amount_total=30,
                            company_id=1,
                        ),
                        Invoice(
                            reference="INV-FULL",
                            order_id=orders[2].id,
                            partner_id=1,
                            status="posted",
                            invoice_date=date(2026, 10, 3),
                            currency_code="XOF",
                            amount_total=40,
                            company_id=1,
                        ),
                    ]
                )
                await session.commit()

                service = InvoiceService(session)
                billable = await service.list_billable_orders()

                # Tri décroissant sur la date de commande : la commande en
                # brouillon (issue d'un devis confirmé) et la partiellement
                # facturée restent proposées ; la vente comptoir, la commande
                # soldée et l'annulée sont écartées.
                assert [row["reference"] for row in billable] == [
                    "CONF-NEW",
                    "DRAFT",
                    "CONF-OLD",
                ]
                assert [row["status"] for row in billable] == [
                    "confirmed",
                    "draft",
                    "confirmed",
                ]
                assert billable[2]["invoiced_amount"] == 30
                assert billable[2]["remaining_amount"] == 50

                # Statuts définitivement non facturables
                assert set(NON_BILLABLE_ORDER_STATUSES) == {"cancelled", "returned"}
                with pytest.raises(ValueError) as excinfo:
                    await service.create_from_order(orders[5].id)
                assert "ne peut plus être facturée" in str(excinfo.value)
        finally:
            await engine.dispose()

    asyncio.run(scenario())
