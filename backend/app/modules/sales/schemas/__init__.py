"""
Schémas du module Ventes — devis, lignes de devis, commandes, vente comptoir.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CutBase(BaseModel):
    """Sous-ligne de coupe BAC (quantité × longueur)."""

    quantity: float = 1
    length: float
    unit_price: float | None = None


class CutRead(CutBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class QuoteLineCreate(BaseModel):
    product_id: int | None = None
    # Variante du produit (optionnelle). ``variant_name`` est un champ interne
    # réécrit côté serveur depuis la variante — ne pas s'y fier en entrée.
    variant_id: int | None = None
    variant_name: str | None = None
    description: str | None = None
    quantity: float = 1
    unit: str | None = None
    sell_by_length: bool = False
    unit_price: float = 0
    discount_percent: float = 0
    cuts: list[CutBase] = Field(default_factory=list)


class QuoteLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    product_id: int | None = None
    variant_id: int | None = None
    variant_name: str | None = None
    description: str | None = None
    quantity: float
    unit: str | None = None
    sell_by_length: bool
    unit_price: float
    discount_percent: float
    total_length: float
    subtotal: float
    cuts: list[CutRead] = Field(default_factory=list)


class QuoteCreate(BaseModel):
    partner_id: int
    site_id: int | None = None
    # Contact commercial (vendeur) : choisi par l'admin, sinon = créateur.
    salesperson_id: int | None = None
    quote_date: date | None = None
    valid_until: date | None = None
    currency_code: str = "XOF"
    notes: str | None = None
    terms: str | None = None
    # Remise globale (montant) et TVA (%)
    discount_amount: float = 0
    tax_percent: float = 0
    # Infos commerciales (stockées dans metadata_json)
    payment_term: str | None = None
    customer_reference: str | None = None
    lines: list[QuoteLineCreate] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    """Mise à jour d'un devis — brouillon uniquement (lignes remplaçables)."""

    partner_id: int | None = None
    site_id: int | None = None
    salesperson_id: int | None = None
    quote_date: date | None = None
    valid_until: date | None = None
    currency_code: str | None = None
    notes: str | None = None
    terms: str | None = None
    discount_amount: float | None = None
    tax_percent: float | None = None
    payment_term: str | None = None
    customer_reference: str | None = None
    status: str | None = None
    lines: list[QuoteLineCreate] | None = None


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    partner_id: int
    site_id: int | None = None
    salesperson_id: int | None = None
    status: str
    quote_date: date
    valid_until: date | None = None
    currency_code: str
    amount_untaxed: float
    discount_amount: float
    tax_amount: float
    amount_total: float
    expected_margin: float | None = None
    notes: str | None = None
    terms: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    lines: list[QuoteLineRead] = Field(default_factory=list)


class QuoteInvoiceCreate(BaseModel):
    """Créer la facture d'un devis confirmé (parcours de vente, étape 2).

    Reprend les modes de facturation d'une commande : ``full`` (totale, ou
    solde si des acomptes existent), ``down_payment_percent`` (acompte en %),
    ``down_payment_fixed`` (acompte en montant).
    """

    mode: Literal["full", "down_payment_percent", "down_payment_fixed"] = "full"
    value: float | None = None
    due_days: int = 0
    post: bool = False


class QuoteInvoiceRead(BaseModel):
    """Résultat du parcours devis → commande → facture."""

    quote_id: int
    quote_reference: str
    order_id: int
    order_reference: str
    invoice_id: int
    invoice_reference: str
    invoice_status: str
    created: bool = False


class OrderLineCreate(BaseModel):
    product_id: int | None = None
    # Variante du produit (optionnelle) ; ``variant_name`` est résolu côté
    # serveur depuis la variante.
    variant_id: int | None = None
    description: str | None = None
    quantity_ordered: float = 1
    unit: str | None = None
    sell_by_length: bool = False
    unit_price: float = 0
    purchase_price: float | None = None
    discount_percent: float = 0
    cuts: list[CutBase] = Field(default_factory=list)


class OrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int | None = None
    variant_id: int | None = None
    variant_name: str | None = None
    description: str | None = None
    quantity_ordered: float
    quantity_reserved: float
    quantity_available: float
    quantity_to_purchase: float
    quantity_purchased: float
    quantity_delivered: float
    sell_by_length: bool
    unit_price: float
    total_length: float
    subtotal: float
    remaining_to_supply: float
    cuts: list[CutRead] = Field(default_factory=list)


class SalesOrderCreate(BaseModel):
    partner_id: int
    site_id: int | None = None
    quote_id: int | None = None
    fulfillment_mode: str = "stock"
    delivery_date_planned: date | None = None
    currency_code: str = "XOF"
    notes: str | None = None
    lines: list[OrderLineCreate] = Field(default_factory=list)


class SalesOrderUpdate(BaseModel):
    """Mise à jour d'une commande — brouillon uniquement (lignes remplaçables)."""

    partner_id: int | None = None
    site_id: int | None = None
    delivery_date_planned: date | None = None
    currency_code: str | None = None
    notes: str | None = None
    status: str | None = None
    lines: list[OrderLineCreate] | None = None


class SalesOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    partner_id: int
    site_id: int | None = None
    quote_id: int | None = None
    fulfillment_mode: str
    status: str
    pos_session_id: int | None = None
    archived: bool = False
    order_date: date
    currency_code: str
    amount_untaxed: float
    tax_amount: float
    shipping_amount: float
    amount_total: float
    paid_amount: float
    created_at: datetime
    lines: list[OrderLineRead] = Field(default_factory=list)


class PosSaleCreate(BaseModel):
    """Vente comptoir simple — panier → sortie stock → facture → paiement.

    ``partner_id`` est facultatif : sans client choisi, le service rattache
    la vente au partenaire walk-in « Client de passage ».
    """

    partner_id: int | None = None
    site_id: int | None = None
    currency_code: str = "XOF"
    warehouse_id: int | None = None
    method: str = "cash"       # cash | mobile_money | ...
    amount: float = 0          # montant encaissé (pour la vente comptoir)
    notes: str | None = None
    lines: list[OrderLineCreate] = Field(default_factory=list)

    def to_sales_order_create(
        self, partner_id: int | None = None
    ) -> SalesOrderCreate:
        resolved = partner_id if partner_id is not None else self.partner_id
        if resolved is None:
            raise ValueError("Aucun client résolu pour la vente comptoir")
        return SalesOrderCreate(
            partner_id=resolved,
            site_id=self.site_id,
            fulfillment_mode="pos",
            currency_code=self.currency_code,
            notes=self.notes,
            lines=self.lines,
        )


# ------------------------------------------------------------------ #
# Schémas PosSession (caisse)
# ------------------------------------------------------------------ #
class PosSessionCreate(BaseModel):
    """Création d'une session de caisse."""

    initial_balance: float = 0
    notes: str | None = None


class PosSessionUpdate(BaseModel):
    """Mise à jour d'une session (notes uniquement, session ouverte)."""

    notes: str | None = None


class PosSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    status: str
    closing_hour: int
    accounting_write_up_hour: int
    initial_balance: float
    closing_balance: float | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    opened_by_id: int | None = None
    closed_by_id: int | None = None
    company_id: int
    notes: str | None = None


class PosSessionClose(BaseModel):
    """Clôture d'une session de caisse."""

    closing_balance: float
    notes: str | None = None


# ------------------------------------------------------------------ #
# Rapport de clôture de session (PRD §4.1.2 §4)
# ------------------------------------------------------------------ #
class PosSessionSaleLine(BaseModel):
    """Ligne de vente résumée pour le rapport de clôture."""

    order_reference: str
    created_at: str
    partner_name: str | None
    amount_total: float


class PosSessionCloseReport(BaseModel):
    """Etat récapitulatif de clôture d'une session de caisse."""

    session_id: int
    reference: str
    status: str
    opened_at: str
    closed_at: str | None
    initial_balance: float
    closing_balance: float | None
    sales_count: int
    sales_total: float
    fund_movements_total: float  # net des dépôts/retraits manuels
    theoretical_balance: float  # initial_balance + sales_total + fund_movements_total
    variance: float | None  # closing_balance - theoretical_balance
    sales: list[PosSessionSaleLine]


# ------------------------------------------------------------------ #
# Schémas PosFundMovement (journal des mouvements de fonds manuels) — PRD §4.1.2 §5
# ------------------------------------------------------------------ #
class PosFundMovementCreate(BaseModel):
    """Création d'un mouvement de fonds manuel en caisse."""

    session_id: int
    movement_type: str  # deposit | withdrawal
    amount: float = 0
    label: str
    reference: str | None = None
    notes: str | None = None


class PosFundMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    movement_type: str
    amount: float
    label: str
    reference: str | None = None
    created_at: datetime
    created_by: int | None = None
    company_id: int
    notes: str | None = None