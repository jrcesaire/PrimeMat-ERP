"""Import en masse des commandes clients (Excel / CSV).

Format « une ligne par article », regroupées en commandes ::
    client (obligatoire), produit (réf. ou nom), quantite, prix_unitaire,
    remise (%), date (JJ/MM/AAAA ou AAAA-MM-JJ), reference_commande,
    description, devise

Regroupement :
- colonne ``reference_commande`` présente → même référence = même commande
- sinon → regroupement par (client, date)

Résolution tolérante : produits et clients inconnus sont retrouvés par
nom/référence ; le prix unitaire absent reprend le prix de vente du
produit (ou le prix/ml). Les commandes sont créées en brouillon via
``OrderService`` (numérotation, totaux, tenant hérité du client).
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product import Product
from app.modules.crm.models.partner import Partner
from app.modules.sales.schemas import OrderLineCreate, SalesOrderCreate
from app.modules.sales.services.order_service import OrderService
from app.shared.enums import EntityType
from app.shared.file_import import clean_str, to_date, to_float

logger = logging.getLogger(__name__)

_LINE_ALIASES = {
    "client": "partner", "clients": "partner", "customer": "partner",
    "partenaire": "partner", "partner": "partner",
    "produit": "product", "product": "product", "article": "product",
    "quantite": "quantity", "quantity": "quantity", "qty": "quantity",
    "qte": "quantity",
    "prix_unitaire": "unit_price", "prix": "unit_price",
    "unit_price": "unit_price", "pu": "unit_price",
    "remise": "discount_percent", "discount": "discount_percent",
    "discount_percent": "discount_percent",
    "date": "date", "date_commande": "date", "order_date": "date",
    "reference_commande": "order_ref", "ref_commande": "order_ref",
    "order_ref": "order_ref", "commande": "order_ref",
    "description": "description", "libelle": "description",
    "devise": "currency", "currency": "currency", "monnaie": "currency",
}


def _map_line(row: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {"__line__": row.get("__line__")}
    for key, value in row.items():
        if key.startswith("__"):
            continue
        field = _LINE_ALIASES.get(key)
        if field and field not in mapped:
            mapped[field] = value
    return mapped


class SalesImportService:
    """Import des commandes clients depuis un fichier Excel / CSV."""

    def __init__(self, session: AsyncSession, company_id: int | None = None):
        self.session = session
        self.company_id = company_id

    # -- résolutions -------------------------------------------------- #
    async def _resolve_partner(self, raw: Any) -> Partner:
        name = clean_str(raw, 200)
        if not name:
            raise ValueError("Colonne « client » obligatoire")
        stmt = select(Partner).where(Partner.name.ilike(name))
        if self.company_id:
            stmt = stmt.where(Partner.company_id == self.company_id)
        partner = (await self.session.execute(stmt)).scalars().first()
        if partner is None:
            partner = Partner(
                name=name, role="client",
                entity_type=EntityType.COMPANY.value,
                company_id=self.company_id,
            )
            self.session.add(partner)
            await self.session.flush()
        return partner

    async def _resolve_product(self, raw: Any) -> Product | None:
        text = clean_str(raw, 200)
        if not text:
            return None
        product = (await self.session.execute(
            select(Product)
            .where(
                (Product.reference.ilike(text)) | (Product.name.ilike(text))
            )
            .order_by(Product.id)
        )).scalars().first()
        return product

    # -- import ------------------------------------------------------- #
    async def import_orders(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        # 1) Normalise et regroupe les lignes par commande
        groups: OrderedDict[tuple, dict[str, Any]] = OrderedDict()
        parse_errors: list[dict] = []

        for row in rows:
            data = _map_line(row)
            line_no = data.get("__line__")
            try:
                partner_name = clean_str(data.get("partner"), 200)
                if not partner_name:
                    raise ValueError("Colonne « client » obligatoire")
                order_date = to_date(data.get("date"))
                quantity = to_float(data.get("quantity"), 1.0) or 1.0
                if quantity <= 0:
                    raise ValueError("Quantité invalide")
                discount = to_float(data.get("discount_percent"), 0.0) or 0.0
                if not 0 <= discount <= 100:
                    raise ValueError("Remise invalide (0-100 %)")
                order_ref = clean_str(data.get("order_ref"), 30)
                currency = (clean_str(data.get("currency"), 3) or "XOF").upper()
                key = ("ref", order_ref) if order_ref else (
                    "pd", partner_name.lower(),
                    order_date.isoformat() if order_date else "",
                )
                group = groups.setdefault(key, {
                    "order_ref": order_ref,
                    "partner": partner_name,
                    "date": order_date,
                    "currency": currency,
                    "lines": [],
                })
                group["lines"].append({
                    "product": clean_str(data.get("product"), 200),
                    "description": clean_str(data.get("description"), 500),
                    "quantity": quantity,
                    "unit_price": to_float(data.get("unit_price")),
                    "discount_percent": discount,
                    "__line__": line_no,
                })
            except Exception as exc:  # noqa: BLE001
                parse_errors.append({
                    "line": line_no, "error": str(exc) or exc.__class__.__name__,
                })

        # 2) Création des commandes (OrderService = numérotation + totaux)
        service = OrderService(self.session)
        orders_created = 0
        lines_created = 0
        errors: list[dict] = list(parse_errors)

        for group in groups.values():
            try:
                partner = await self._resolve_partner(group["partner"])

                line_schemas: list[OrderLineCreate] = []
                for line in group["lines"]:
                    product = await self._resolve_product(line["product"])
                    unit_price = line["unit_price"]
                    sell_by_length = False
                    if product is not None:
                        sell_by_length = product.sell_by_length
                        if unit_price is None:
                            unit_price = (
                                product.price_per_meter
                                if sell_by_length
                                else product.selling_price
                            ) or 0
                    line_schemas.append(OrderLineCreate(
                        product_id=product.id if product else None,
                        description=line["description"],
                        quantity_ordered=line["quantity"],
                        sell_by_length=sell_by_length,
                        unit_price=unit_price or 0,
                        discount_percent=line["discount_percent"],
                    ))

                order = await service.create_order(SalesOrderCreate(
                    partner_id=partner.id,
                    currency_code=group["currency"],
                    lines=line_schemas,
                ))
                if group["date"]:
                    order.order_date = group["date"]
                await self.session.commit()
                orders_created += 1
                lines_created += len(line_schemas)
            except Exception as exc:  # noqa: BLE001
                await self.session.rollback()
                logger.warning("Import commande échoué : %s", exc)
                errors.append({
                    "line": ",".join(
                        str(l["__line__"]) for l in group["lines"]
                    ) or "?",
                    "error": str(exc) or exc.__class__.__name__,
                })

        return {
            "orders_created": orders_created,
            "lines_created": lines_created,
            "errors": errors,
            "total": orders_created + len(errors),
        }
