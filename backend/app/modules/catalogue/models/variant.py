"""Modèles des variantes de produits : propriétés, valeurs, variantes."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class ProductProperty(Base, TenantMixin):
    """Propriété d'un produit (ex. « Couleur », « Épaisseur », « Finition »).

    Une propriété est globale a l'entreprise (réutilisable sur plusieurs
    produits) et porte une liste de valeurs possibles (Rouge, Vert, ...).
    """

    name: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    position: Mapped[int] = MappedColumn(Integer, default=0)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    values: Mapped[list["ProductPropertyValue"]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductPropertyValue.position, ProductPropertyValue.id",
    )

    def __repr__(self) -> str:
        return f"<ProductProperty {self.name}>"


class ProductPropertyValue(Base, TenantMixin):
    """Valeur possible d'une propriété (ex. Rouge, Vert, Gris foncé)."""

    property_id: Mapped[int] = MappedColumn(
        ForeignKey("product_properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = MappedColumn(String(100), nullable=False)
    position: Mapped[int] = MappedColumn(Integer, default=0)

    property: Mapped["ProductProperty"] = relationship(
        "ProductProperty", back_populates="values"
    )

    def __repr__(self) -> str:
        return f"<ProductPropertyValue {self.value}>"


class ProductVariant(Base, TenantMixin):
    """Variante d'un produit (ex. « Tôle bac texturée - Rouge »).

    - ``name_suffix`` : libellé de la combinaison (« Rouge » ou « Rouge / Mat ») ;
    - ``reference``   : référence propre de la variante (ex. TOL-BAC-R) ;
    - prix            : vides => héritent du produit de base.
    """

    __table_args__ = (
        UniqueConstraint("company_id", "product_id", "name_suffix",
                         name="uq_variant_product_suffix"),
    )

    product_id: Mapped[int] = MappedColumn(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference: Mapped[Optional[str]] = MappedColumn(String(50), index=True)
    name_suffix: Mapped[str] = MappedColumn(String(300), nullable=False)
    selling_price: Mapped[Optional[float]] = MappedColumn(Numeric(12, 4))
    purchase_price: Mapped[Optional[float]] = MappedColumn(Numeric(12, 4))
    price_per_meter: Mapped[Optional[float]] = MappedColumn(Numeric(10, 4))
    is_default: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    product: Mapped["Product"] = relationship(
        "Product", back_populates="variants"
    )
    properties: Mapped[list["ProductVariantProperty"]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        return f"{self.product.name} - {self.name_suffix}" if self.product else self.name_suffix

    def __repr__(self) -> str:
        return f"<ProductVariant {self.reference or self.name_suffix}>"


class ProductVariantProperty(Base, TenantMixin):
    """Lien variante <-> (propriété, valeur choisie)."""

    __table_args__ = (
        UniqueConstraint("variant_id", "property_id", name="uq_variant_property"),
    )

    variant_id: Mapped[int] = MappedColumn(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[int] = MappedColumn(
        ForeignKey("product_properties.id", ondelete="CASCADE"), nullable=False
    )
    value_id: Mapped[int] = MappedColumn(
        ForeignKey("product_property_values.id", ondelete="CASCADE"), nullable=False
    )

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="properties"
    )
    property_ref: Mapped["ProductProperty"] = relationship(
        "ProductProperty", lazy="selectin"
    )
    value_ref: Mapped["ProductPropertyValue"] = relationship(
        "ProductPropertyValue", lazy="selectin"
    )

    @property
    def property_name(self) -> str:
        return self.property_ref.name if self.property_ref else ""

    @property
    def value(self) -> str:
        return self.value_ref.value if self.value_ref else ""

    def __repr__(self) -> str:
        return f"<ProductVariantProperty variant={self.variant_id} value={self.value_id}>"
