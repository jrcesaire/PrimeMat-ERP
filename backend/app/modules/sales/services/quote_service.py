"""
Service Ventes — devis.

Logique clé :
- lignes standard et lignes tôle BAC multi-longueurs (sous-lignes longueur + qté)
- vente à la pièce standard (mode dual) convertie en coupe de longueur standard,
  facturée au prorata du ml : montant = qty × unit_length × prix/ml
- validation croisée ligne ↔ produit (mode de vente dérivé de la catégorie)
- conversion devis → commande (coupes BAC préservées)
- événements : sales.quote.created / sales.quote.confirmed
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.shared.events import event_bus
from app.modules.catalogue.models.product import Product
from app.modules.crm.models.partner import Partner
from app.modules.sales.models.order import OrderLineCut, SalesOrder, SalesOrderLine
from app.modules.sales.models.quote import Quote, QuoteLine, QuoteLineCut
from app.modules.sales.schemas import QuoteCreate, QuoteLineCreate, QuoteUpdate

logger = logging.getLogger(__name__)


async def prepare_line_data(
    session: AsyncSession, data: QuoteLineCreate
) -> QuoteLineCreate:
    """Valide la cohérence ligne ↔ produit et normalise la ligne.

    Règles (mode de vente dérivé de la catégorie du produit) :
    - produit ``unit``  : vente à l'unité uniquement — coupes refusées
    - produit ``length``: vente au ml uniquement — ``sell_by_length`` forcé,
      sous-lignes (qty pièces × longueur) attendues (ou qty en mètres)
    - produit ``dual``  : au ml (coupes) OU à la pièce standard → convertie
      en coupe ``{quantity: qty, length: unit_length}`` (facturation au
      prorata du ml)
    - prix par défaut repris du produit si non fourni
    """
    if data.product_id is None:
        return data  # ligne libre (description seule)

    product = await session.get(Product, data.product_id)
    if product is None:
        raise ValueError(f"Produit {data.product_id} introuvable")

    sells_length = bool(product.sell_by_length)
    payload = data.model_dump()

    if data.sell_by_length and not sells_length:
        raise ValueError(
            f"Le produit « {product.name} » ne se vend pas au mètre linéaire."
        )
    if sells_length and not data.sell_by_length:
        if product.sale_mode != "dual":
            raise ValueError(
                f"Le produit « {product.name} » se vend au mètre linéaire : "
                "fournissez les longueurs (sous-lignes quantité × longueur)."
            )
        # Vente à la pièce standard (dual) → coupe de longueur standard,
        # facturée au prorata du ml.
        if not product.unit_length:
            raise ValueError(
                f"Le produit « {product.name} » n'a pas de longueur standard "
                "(unit_length) définie : vente à la pièce impossible."
            )
        payload["sell_by_length"] = True
        payload["cuts"] = [
            {"quantity": float(data.quantity or 1), "length": float(product.unit_length)}
        ]

    # Prix par défaut depuis le produit
    if not payload.get("unit_price"):
        if payload["sell_by_length"]:
            payload["unit_price"] = float(product.price_per_meter or 0)
        else:
            payload["unit_price"] = float(product.selling_price or 0)

    # Validations des sous-lignes de coupe
    if payload["sell_by_length"]:
        for cut in payload.get("cuts", []):
            if float(cut.get("length", 0)) <= 0:
                raise ValueError(
                    f"Longueur invalide pour « {product.name} » : "
                    "chaque sous-ligne doit avoir une longueur > 0."
                )
            if float(cut.get("quantity", 0)) < 1:
                raise ValueError(
                    f"Quantité invalide pour « {product.name} » : "
                    "au moins 1 pièce par longueur."
                )

    return QuoteLineCreate(**payload)


def build_quote_line(data: QuoteLineCreate) -> QuoteLine:
    """Construit une ligne de devis (standard ou BAC) avec totaux calculés."""
    line = QuoteLine(
        product_id=data.product_id,
        description=data.description,
        quantity=data.quantity,
        unit=data.unit,
        sell_by_length=data.sell_by_length,
        unit_price=data.unit_price,
        discount_percent=data.discount_percent,
    )
    if data.sell_by_length and data.cuts:
        for cut in data.cuts:
            line.cuts.append(
                QuoteLineCut(
                    quantity=cut.quantity,
                    length=cut.length,
                    unit_price=cut.unit_price,
                )
            )
    line.compute_totals()
    return line


def build_order_line_from_quote(ql: QuoteLine) -> SalesOrderLine:
    """Devis → commande : le détail des longueurs n'est jamais perdu."""
    ol = SalesOrderLine(
        product_id=ql.product_id,
        description=ql.description,
        quantity_ordered=float(ql.total_length or ql.quantity),
        unit=ql.unit,
        sell_by_length=ql.sell_by_length,
        unit_price=ql.unit_price,
        discount_percent=ql.discount_percent,
        total_length=ql.total_length,
        subtotal=ql.subtotal,
    )
    for cut in ql.cuts:
        ol.cuts.append(
            OrderLineCut(
                quantity=cut.quantity,
                length=cut.length,
                unit_price=cut.unit_price,
            )
        )
    return ol


class QuoteService:
    """Service des devis."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    def _recompute_totals(
        self,
        quote: Quote,
        tax_percent: float = 0,
        global_discount: float | None = None,
    ) -> None:
        """Calcule les totaux du devis.

        - ``amount_untaxed`` : somme des sous-totaux de lignes (après
          remises par ligne)
        - ``discount_amount`` : remise globale (montant fixe)
        - ``tax_amount``     : TVA appliquée sur (HT − remise globale)
        - ``amount_total``   : HT − remise globale + TVA
        """
        untaxed = sum(float(l.subtotal or 0) for l in quote.lines)
        discount = max(float(global_discount or 0), 0)
        base = max(untaxed - discount, 0)
        tax = base * float(tax_percent or 0) / 100

        quote.amount_untaxed = untaxed
        quote.discount_amount = discount
        quote.tax_amount = tax
        quote.amount_total = base + tax

    @staticmethod
    def _merge_metadata(
        quote: Quote,
        payment_term: str | None,
        customer_reference: str | None,
    ) -> None:
        """Stocke payment_term / customer_reference dans metadata_json."""
        meta = dict(quote.metadata_json or {})
        if payment_term is not None:
            meta["payment_term"] = payment_term
        if customer_reference is not None:
            meta["customer_reference"] = customer_reference
        quote.metadata_json = meta

    async def create_quote(self, data: QuoteCreate) -> Quote:
        reference = await self.sequences.next_value("quote", "DEV")
        quote = Quote(
            reference=reference,
            partner_id=data.partner_id,
            site_id=data.site_id,
            quote_date=data.quote_date or date.today(),
            valid_until=data.valid_until,
            currency_code=data.currency_code,
            notes=data.notes,
            terms=data.terms,
        )
        for line_data in data.lines:
            prepared = await prepare_line_data(self.session, line_data)
            quote.lines.append(build_quote_line(prepared))
        self._merge_metadata(quote, data.payment_term, data.customer_reference)
        self._recompute_totals(quote, data.tax_percent, data.discount_amount)

        # Le document hérite du tenant de son partenaire
        if quote.company_id is None:
            partner = await self.session.get(Partner, data.partner_id)
            if partner is None:
                raise ValueError(f"Client {data.partner_id} introuvable")
            quote.company_id = partner.company_id
        for line in quote.lines:
            line.company_id = quote.company_id

        self.session.add(quote)
        await self.session.commit()

        # Recharge avec lignes + coupes (évite les lazy-loads async non awaités)
        result = await self.session.execute(
            select(Quote)
            .options(
                selectinload(Quote.lines).selectinload(QuoteLine.cuts)
            )
            .where(Quote.id == quote.id)
        )
        quote = result.scalar_one()

        await event_bus.emit(
            "sales.quote.created", {"quote_id": quote.id, "reference": reference}
        )
        return quote

    async def get_quote(self, quote_id: int) -> Quote | None:
        return await self.session.get(Quote, quote_id)

    async def update_quote(self, quote_id: int, data: QuoteUpdate) -> Quote:
        """Met à jour un devis — autorisé uniquement au statut brouillon.

        Si ``data.lines`` est fourni, toutes les lignes existantes sont
        remplacées (coupes BAC comprises) et les totaux recalculés.
        """
        quote = await self.session.get(Quote, quote_id)
        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")
        if quote.status != "draft":
            raise ValueError(
                "Seul un devis au statut « brouillon » peut être modifié."
            )

        if data.partner_id is not None:
            quote.partner_id = data.partner_id
        if data.site_id is not None:
            quote.site_id = data.site_id
        if data.quote_date is not None:
            quote.quote_date = data.quote_date
        if data.valid_until is not None:
            quote.valid_until = data.valid_until
        if data.currency_code is not None:
            quote.currency_code = data.currency_code
        if data.notes is not None:
            quote.notes = data.notes
        if data.terms is not None:
            quote.terms = data.terms
        if data.payment_term is not None or data.customer_reference is not None:
            self._merge_metadata(
                quote, data.payment_term, data.customer_reference
            )

        recompute = False
        if data.lines is not None:
            # Remplace l'ensemble des lignes (cascade delete-orphan sur coupes)
            quote.lines.clear()
            await self.session.flush()
            for line_data in data.lines:
                prepared = await prepare_line_data(self.session, line_data)
                line = build_quote_line(prepared)
                line.company_id = quote.company_id
                quote.lines.append(line)
            recompute = True

        # Remise globale / TVA modifiables seules
        if (
            data.discount_amount is not None
            or data.tax_percent is not None
            or recompute
        ):
            self._recompute_totals(
                quote,
                data.tax_percent
                if data.tax_percent is not None
                else (quote.metadata_json or {}).get("tax_percent", 0),
                data.discount_amount
                if data.discount_amount is not None
                else float(quote.discount_amount or 0),
            )
            if data.tax_percent is not None:
                meta = dict(quote.metadata_json or {})
                meta["tax_percent"] = data.tax_percent
                quote.metadata_json = meta

        await self.session.commit()

        result = await self.session.execute(
            select(Quote)
            .options(selectinload(Quote.lines).selectinload(QuoteLine.cuts))
            .where(Quote.id == quote.id)
        )
        return result.scalar_one()

    async def delete_quote(self, quote_id: int) -> None:
        """Supprime un devis — brouillon uniquement."""
        quote = await self.session.get(Quote, quote_id)
        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")
        if quote.status != "draft":
            raise ValueError(
                "Seul un devis au statut « brouillon » peut être supprimé."
            )
        await self.session.delete(quote)  # cascade lines + cuts
        await self.session.commit()

    async def back_to_draft(self, quote_id: int) -> Quote:
        """Remet un devis confirmé au statut brouillon.

        - annule la commande générée à la confirmation si elle est encore
          au brouillon (aucune réservation de stock à cette étape)
        - refuse si la commande liée est elle-même confirmée, ou si une
          facture / un bon de livraison y est déjà rattaché
        """
        quote = await self.session.get(Quote, quote_id)
        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")
        if quote.status != "confirmed":
            raise ValueError(
                "Seul un devis confirmé peut être remis au brouillon."
            )

        from app.modules.delivery.models.delivery import DeliveryNote
        from app.modules.invoicing.models.invoice import Invoice

        # Commandes générées depuis ce devis
        result = await self.session.execute(
            select(SalesOrder).where(SalesOrder.quote_id == quote.id)
        )
        orders = list(result.scalars().all())

        for order in orders:
            if order.status != "draft":
                raise ValueError(
                    "Impossible : la commande liée à ce devis est confirmée. "
                    "Remettez d'abord la commande au brouillon."
                )
            inv = await self.session.execute(
                select(Invoice).where(Invoice.order_id == order.id).limit(1)
            )
            if inv.scalar_one_or_none() is not None:
                raise ValueError(
                    "Impossible : une facture est liée à ce devis. "
                    "Annulez d'abord la facture."
                )
            dlv = await self.session.execute(
                select(DeliveryNote).where(DeliveryNote.order_id == order.id).limit(1)
            )
            if dlv.scalar_one_or_none() is not None:
                raise ValueError(
                    "Impossible : un bon de livraison est lié à ce devis. "
                    "Annulez d'abord le bon de livraison."
                )

        # Supprime la (ou les) commande(s) encore au brouillon (cascade lines+cuts)
        for order in orders:
            if order.status == "draft":
                await self.session.delete(order)

        quote.status = "draft"
        await self.session.commit()

        await event_bus.emit("sales.quote.back_to_draft", {"quote_id": quote.id})

        result = await self.session.execute(
            select(Quote)
            .options(selectinload(Quote.lines).selectinload(QuoteLine.cuts))
            .where(Quote.id == quote.id)
        )
        return result.scalar_one()


    async def list_quotes(
        self, skip: int = 0, limit: int = 100, partner_id: int | None = None
    ) -> list[Quote]:
        stmt = select(Quote).offset(skip).limit(limit).order_by(Quote.id.desc())
        if partner_id:
            stmt = stmt.where(Quote.partner_id == partner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def confirm_quote(self, quote_id: int) -> SalesOrder:
        """Convertit un devis confirmé en commande client."""
        quote = await self.session.get(Quote, quote_id)
        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")

        order = SalesOrder(
            reference=await self.sequences.next_value("order", "COM"),
            partner_id=quote.partner_id,
            site_id=quote.site_id,
            quote_id=quote.id,
            currency_code=quote.currency_code,
        )
        for ql in quote.lines:
            order.lines.append(build_order_line_from_quote(ql))

        order.amount_untaxed = quote.amount_untaxed
        order.tax_amount = quote.tax_amount
        order.amount_total = quote.amount_total
        # La commande hérite du tenant du devis
        order.company_id = quote.company_id
        for line in order.lines:
            line.company_id = order.company_id

        quote.status = "confirmed"
        self.session.add(order)
        await self.session.commit()

        # Recharge la commande avec lignes + coupes
        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts)
            )
            .where(SalesOrder.id == order.id)
        )
        order = result.scalar_one()

        await event_bus.emit(
            "sales.quote.confirmed", {"quote_id": quote.id}
        )
        await event_bus.emit(
            "sales.order.created",
            {"order_id": order.id, "reference": order.reference},
        )
        return order