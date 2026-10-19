"""
Énumérations partagées entre les modules métier.

Centraliser les enums évite les duplications et garantit la cohérence
des valeurs stockées en base de données.
"""
from __future__ import annotations

import enum


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSET = "unset"


class EntityType(str, enum.Enum):
    """Type d'entité client."""
    INDIVIDUAL = "individual"
    COMPANY = "company"
    PROFESSIONAL = "professional"


class AddressType(str, enum.Enum):
    BILLING = "billing"
    DELIVERY = "delivery"
    SITE = "site"


class ProductType(str, enum.Enum):
    """Type de produit selon la gestion de stock."""
    STOCKABLE = "stockable"      # Produit physiquement géré en stock
    ON_DEMAND = "on_demand"      # Sur commande (pas de stock)
    HYBRID = "hybrid"            # Peut être partiellement en stock
    SERVICE = "service"          # Service (pas de stock)


class SaleMode(str, enum.Enum):
    """
    Mode de vente d'une catégorie de produits (hérité par les produits).

    - UNIT   : vendu à l'unité (sac, pièce, pot...) → prix ``selling_price``
    - LENGTH : vendu au mètre linéaire, coupes à la demande (tôles BAC)
               → prix ``price_per_meter``, sous-lignes (qty × longueur)
    - DUAL   : les deux — au ml sur mesure OU à la pièce de longueur
               standard facturée au prorata (qty × unit_length × prix/ml)
               (ex. solin de rive : au ml ou pièce de 2,50 m)
    """
    UNIT = "unit"
    LENGTH = "length"
    DUAL = "dual"

    @property
    def sells_by_length(self) -> bool:
        """Vrai si le mode implique une vente au mètre linéaire possible."""
        return self in (SaleMode.LENGTH, SaleMode.DUAL)


class UnitOfMeasureCategory(str, enum.Enum):
    LENGTH = "length"
    WEIGHT = "weight"
    VOLUME = "volume"
    COUNT = "count"
    AREA = "area"


class PurchaseRequestStatus(str, enum.Enum):
    """Workflow de la Demande d'Achat (DA)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"    # soumise — en attente de validation
    APPROVED = "approved"      # validée → convertible en BC
    REJECTED = "rejected"
    CONVERTED = "converted"    # convertie en bon de commande
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    DONE = "done"


class PurchaseReceptionStatus(str, enum.Enum):
    """Bon de réception fournisseur."""

    DRAFT = "draft"
    VALIDATED = "validated"
    CANCELLED = "cancelled"


class SupplierInvoiceStatus(str, enum.Enum):
    """Facture fournisseur (rapprochée avec BC / BR)."""

    DRAFT = "draft"
    POSTED = "posted"          # enregistrée + comptabilisée
    PAID = "paid"
    CANCELLED = "cancelled"


class SalesOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PROFORMA = "proforma"
    CONFIRMED = "confirmed"
    RESERVED = "reserved"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class DeliveryStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PROFORMA = "proforma"
    POSTED = "posted"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    CANCELLED = "cancelled"
    CREDIT = "credit"


class PaymentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class PaymentDirection(str, enum.Enum):
    RECEIPT = "receipt"     # Paiement reçu du client
    PAYMENT = "payment"     # Paiement fait au fournisseur


class StockMovementType(str, enum.Enum):
    INBOUND = "inbound"     # Entrée (réception fournisseur)
    OUTBOUND = "outbound"   # Sortie (livraison client)
    TRANSFER = "transfer"   # Transfert entre entrepôts
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    LOSS = "loss"
    DAMAGE = "damage"


class TaxType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    GROUP = "group"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    GENERATED = "generated"
    SENT = "sent"
    ARCHIVED = "archived"


class DocumentType(str, enum.Enum):
    QUOTE = "quote"
    ORDER = "order"
    INVOICE = "invoice"
    DELIVERY = "delivery"
    CREDIT_NOTE = "credit_note"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    REPORT = "report"


class ModuleStatus(str, enum.Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    NOT_INSTALLED = "not_installed"


class TaxRegime(str, enum.Enum):
    """Régimes d'imposition fiscale Côte d'Ivoire (OHADA).

    - TEE : Taxe d'État de l'Entreprenant (CA ≤ 50 000 000 FCFA) — TVA bloquée
    - RME : Régime de la Micro-Entreprise (50 M < CA ≤ 200 M) — TVA bloquée
    - RSI : Réel Simplifié (200 M < CA ≤ 500 M) — TVA autorisée
    - RNI : Réel Normal (CA > 500 M) — TVA autorisée
    """

    TEE = "TEE"
    RME = "RME"
    RSI = "RSI"
    RNI = "RNI"


# Seuils de CA annuel TTC (en FCFA) par régime — utilisé pour la détection de dépassement
TAX_REGIME_THRESHOLDS: dict[TaxRegime, int] = {
    TaxRegime.TEE: 50_000_000,
    TaxRegime.RME: 200_000_000,
    TaxRegime.RSI: 500_000_000,
    TaxRegime.RNI: 0,  # pas de plafond supérieur
}
