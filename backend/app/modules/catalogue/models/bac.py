"""
Modèles de tôles BAC — gestion des lignes multi-longueurs.

Une tôle BAC peut être vendue avec plusieurs longueurs différentes dans
le même devis/facture.  Chaque ``BACCut`` représente une sous-ligne
(quantité × longueur) et ``BACSheet`` représente la tôle elle-même.

Formule ::
    Montant sous-ligne = Quantité × Longueur × Prix unitaire
    Montant total = Σ(Quantité × Longueur × Prix unitaire)
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class BACSheet(Base, TenantMixin):
    """
    Tôle BAC — définition du produit avec caractéristiques techniques.

    - profil (U115, U125, etc.)
    - matière
    - épaisseur
    - largeur utile / totale
    - couleur / finition
    - longueur standard
    - coût unitaire (par mètre ou unité de calcul)
    - prix de vente
    """

    product_id: Mapped[int] = MappedColumn(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    profile: Mapped[str | None] = MappedColumn(String(50))
    material: Mapped[str | None] = MappedColumn(String(100))
    thickness: Mapped[float | None] = MappedColumn(Numeric(10, 4))

    useful_width: Mapped[float | None] = MappedColumn(Numeric(10, 4))
    total_width: Mapped[float | None] = MappedColumn(Numeric(10, 4))

    color: Mapped[str | None] = MappedColumn(String(50))
    finish: Mapped[str | None] = MappedColumn(String(50))
    standard_length: Mapped[float | None] = MappedColumn(Numeric(10, 4))

    unit_measure: Mapped[str] = MappedColumn(String(10), default="m")
    unit_cost: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    unit_price: Mapped[float | None] = MappedColumn(Numeric(12, 4))
    supplier_id: Mapped[int | None] = MappedColumn(
        ForeignKey("partners.id"), nullable=True
    )

    cuts: Mapped[list["BACCut"]] = relationship(
        "BACCut",
        back_populates="sheet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<BACSheet {self.profile or self.product_id}>"


class BACCut(Base, TenantMixin):
    """
    Sous-ligne de découpe d'une tôle BAC.

    Représente une longueur précise commandée :
    ``quantité`` feuilles de ``length`` mètres.
    """

    sheet_id: Mapped[int] = MappedColumn(
        ForeignKey("bac_sheets.id", ondelete="CASCADE"), nullable=False
    )

    quantity: Mapped[float] = MappedColumn(Numeric(12, 4), default=1)
    length: Mapped[float] = MappedColumn(Numeric(12, 4), nullable=False)
    unit_price: Mapped[float | None] = MappedColumn(Numeric(12, 4))

    @property
    def total_length(self) -> float:
        """Longueur totale = quantité × longueur."""
        return float(self.quantity * self.length)

    @property
    def subtotal(self) -> float:
        """Montant sous-ligne = quantité × longueur × prix unitaire."""
        price = self.unit_price or 0
        return float(self.quantity * self.length * price)

    sheet: Mapped["BACSheet"] = relationship("BACSheet", back_populates="cuts")

    def __repr__(self) -> str:
        return f"<BACCut {self.quantity} x {self.length}m>"