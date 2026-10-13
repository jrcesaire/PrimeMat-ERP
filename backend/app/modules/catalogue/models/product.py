"""Modèles Produit, Catégorie, Unité et Conversion."""
from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship
from sqlalchemy import select

from app.core.database import Base, TenantMixin
from app.shared.enums import DocumentStatus, ProductType, SaleMode


class ProductCategory(Base, TenantMixin):
    """Catégorie de produit (Ciment, Fer, Tôles...).

    ``sale_mode`` définit le mode de vente des produits de la catégorie :

    - ``unit``   : vendus à l'unité (défaut)
    - ``length`` : vendus au mètre linéaire (tôles BAC)
    - ``dual``   : au ml OU à la pièce de longueur standard (accessoires)

    Les sous-catégories héritent du mode de leur parent.
    """

    name: Mapped[str] = MappedColumn(String(100), nullable=False)
    code: Mapped[str | None] = MappedColumn(String(20), index=True)
    description: Mapped[str | None] = MappedColumn(String(500))
    parent_id: Mapped[int | None] = MappedColumn(
        Integer, ForeignKey("product_categories.id"), nullable=True
    )
    sale_mode: Mapped[str] = MappedColumn(
        String(10), default=SaleMode.UNIT.value, nullable=False
    )
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category", lazy="selectin"
    )
    children: Mapped[list["ProductCategory"]] = relationship(
        "ProductCategory",
        back_populates="parent",
        lazy="selectin",
    )
    parent: Mapped["ProductCategory | None"] = relationship(
        "ProductCategory",
        back_populates="children",
        remote_side="ProductCategory.id",
    )

    async def resolve_sale_mode(self, session=None) -> SaleMode:
        """Résout le mode de vente effectif en remontant les ancêtres.

        La première catégorie de la chaîne (self → racine) portant un mode
        non-unitaire (length/dual) le définit ; sinon ``unit``.
        """
        current: ProductCategory | None = self
        depth = 0
        while current is not None and depth < 10:  # garde-fou anti-boucle
            try:
                mode = SaleMode(current.sale_mode or SaleMode.UNIT.value)
            except ValueError:
                mode = SaleMode.UNIT
            if mode != SaleMode.UNIT:
                return mode
            if current.parent_id is None:
                return SaleMode.UNIT
            if session is not None:
                current = await session.get(ProductCategory, current.parent_id)
            else:
                current = await ProductCategory.get_by_id(current.parent_id)
            depth += 1
        return SaleMode.UNIT

    @classmethod
    async def get_by_id(cls, category_id: int) -> "ProductCategory | None":
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            return await session.get(cls, category_id)

    def __repr__(self) -> str:
        return f"<ProductCategory {self.code or self.name}>"


class ProductUnit(Base, TenantMixin):
    """Unité de mesure (sac, pièce, barre, mètre, kg, litre, rouleau...)."""

    name: Mapped[str] = MappedColumn(String(50), nullable=False)
    code: Mapped[str] = MappedColumn(String(10), nullable=False, index=True)
    symbol: Mapped[str | None] = MappedColumn(String(10))
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<ProductUnit {self.code}>"


class UnitConversion(Base, TenantMixin):
    """Conversion entre unités (1 palette = 50 sacs, 1 rouleau = 100 mètres)."""

    from_unit_id: Mapped[int] = MappedColumn(
        ForeignKey("product_units.id"), nullable=False
    )
    to_unit_id: Mapped[int] = MappedColumn(
        ForeignKey("product_units.id"), nullable=False
    )
    factor: Mapped[float] = MappedColumn(Numeric(20, 8), nullable=False)

    from_unit: Mapped["ProductUnit"] = relationship(
        "ProductUnit", foreign_keys=[from_unit_id], lazy="selectin"
    )
    to_unit: Mapped["ProductUnit"] = relationship(
        "ProductUnit", foreign_keys=[to_unit_id], lazy="selectin"
    )
class Product(Base, TenantMixin):
    """
    Produit du catalogue.

    Types de produits : ``STOCKABLE``, ``NON_STOCKABLE``, ``HYBRIDE``, ``SERVICE``.
    Pour les tôles BAC : ``sell_by_length`` active la segmentation par longueur.
    """

    reference: Mapped[str] = MappedColumn(String(50), nullable=False, index=True)
    barcode: Mapped[str | None] = MappedColumn(String(50), index=True)
    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    description: Mapped[str | None] = MappedColumn(String(1000))

    category_id: Mapped[int | None] = MappedColumn(
        ForeignKey("product_categories.id"), nullable=True
    )
    category: Mapped["ProductCategory | None"] = relationship(
        "ProductCategory", back_populates="products"
    )

    brand: Mapped[str | None] = MappedColumn(String(100))
    storage_type: Mapped[str] = MappedColumn(
        String(20), default=ProductType.STOCKABLE.value, index=True
    )

    purchase_unit_id: Mapped[int | None] = MappedColumn(
        ForeignKey("product_units.id"), nullable=True
    )
    sale_unit_id: Mapped[int | None] = MappedColumn(
        ForeignKey("product_units.id"), nullable=True
    )
    conversion_factor: Mapped[float] = MappedColumn(Numeric(10, 6), default=1)

    # Segmentation longueur (tôles BAC)
    sell_by_length: Mapped[bool] = MappedColumn(Boolean, default=False)
    sale_mode: Mapped[str] = MappedColumn(
        String(10), default=SaleMode.UNIT.value, index=True
    )
    unit_length: Mapped[float | None] = MappedColumn(Numeric(10, 4))
    price_per_meter: Mapped[float | None] = MappedColumn(Numeric(10, 4))

    @property
    def is_bac_sheet(self) -> bool:
        """Vrai si le produit se vend au mètre linéaire (tôle BAC ou dual)."""
        return bool(self.sell_by_length)

    # Prix
    purchase_price: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    selling_price: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    margin_percent: Mapped[float | None] = MappedColumn(Numeric(6, 2))
    tax_id: Mapped[int | None] = MappedColumn(ForeignKey("taxes.id"), nullable=True)

    # Approvisionnement
    lead_time_days: Mapped[int | None] = MappedColumn(Integer)
    reorder_point: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    reorder_quantity: Mapped[float | None] = MappedColumn(Numeric(12, 4))

    primary_supplier_id: Mapped[int | None] = MappedColumn(
        ForeignKey("partners.id"), nullable=True
    )

    # Divers
    status: Mapped[str] = MappedColumn(String(20), default=DocumentStatus.DRAFT.value)
    attributes: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)

    # Relations
    supplier_links: Mapped[list["ProductSupplier"]] = relationship(
        "ProductSupplier",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Variantes (propriétés + valeurs => combinaisons vendables)
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def variants_count(self) -> int:
        return len(self.variants)

    def __repr__(self) -> str:
        return f"<Product {self.reference} - {self.name}>"


product_units_link = Table(
    "product_units_link",
    Base.metadata,
    Column(
        "product_id", Integer,
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "unit_id", Integer,
        ForeignKey("product_units.id", ondelete="CASCADE"), primary_key=True,
    ),
)


class ProductSupplier(Base, TenantMixin):
    """
    Relation Produit <-> Fournisseur.

    - prix d'achat spécifique
    - fournisseur principal / alternatif
    - délai d'approvisionnement
    """

    product_id: Mapped[int] = MappedColumn(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    is_primary: Mapped[bool] = MappedColumn(Boolean, default=False)
    purchase_price: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    lead_time_days: Mapped[int | None] = MappedColumn(Integer)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    product: Mapped["Product"] = relationship("Product", back_populates="supplier_links")
    supplier: Mapped["Partner"] = relationship("Partner", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ProductSupplier product={self.product_id} supplier={self.supplier_id}>"