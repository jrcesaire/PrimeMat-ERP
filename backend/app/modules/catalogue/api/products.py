"""
Endpoints API du module Catalogue — produits, catégories, unités, tôles BAC.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import or_, select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.shared.file_import import read_rows_from_bytes
from app.modules.catalogue.models.variant import (
    ProductProperty,
)
from app.modules.catalogue.models.product import (
    Product,
    ProductCategory,
    ProductUnit,
    UnitConversion,
)
from app.modules.catalogue.models.bac import BACSheet, BACCut
from app.modules.catalogue.schemas import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductCategoryCreate,
    ProductCategoryRead,
    ProductUnitCreate,
    ProductUnitRead,
    UnitConversionCreate,
    UnitConversionRead,
    BACSheetCreate,
    BACSheetRead,
    BACCutCreate,
    PropertyCreate,
    PropertyRead,
    PropertyValueCreate,
    PropertyValueRead,
    VariantGenerate,
    VariantRead,
    VariantUpdate,
)
from app.modules.catalogue.services.product_service import CatalogueService
from app.modules.catalogue.services.export_service import CatalogueExportService
from app.modules.catalogue.services.import_service import CatalogueImportService
from app.shared.file_export import export_response

router = APIRouter()


@router.get("/products", response_model=list[ProductRead])
async def list_products(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    category_id: int | None = None,
    _: User = Depends(require_permission("product", "view")),
):
    stmt = select(Product)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.reference.ilike(like)))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Product.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# Déclaré AVANT /products/{product_id} : sinon « export » serait capturé
# comme identifiant et renverrait 422.
@router.get("/products/export")
async def export_products(
    session: SessionDep,
    format: str = "xlsx",
    template: bool = False,
    _: User = Depends(require_permission("product", "view")),
):
    """Export Excel / CSV du catalogue (aller‑retour avec l'import).

    - ``format`` : ``xlsx`` (défaut) ou ``csv`` ;
    - ``template=1`` : en‑têtes seuls → modèle vierge à remplir.
    """
    headers, rows = await CatalogueExportService(session).products(
        include_rows=not template
    )
    return export_response(format, "Produits", headers, rows)


@router.get("/products/lookup")
async def lookup_product_by_code(
    session: SessionDep,
    code: str,
    _: User = Depends(require_permission("product", "view")),
):
    """Recherche par scan : code-barres exact, sinon reference.

    Renvoie ``{"found": true, "product": ...}`` ou ``{"found": false}``.
    """
    clean = (code or "").strip()
    if not clean:
        return {"found": False, "code": clean}
    result = await session.execute(
        select(Product)
        .where(or_(Product.barcode == clean, Product.reference == clean))
        .limit(1)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return {"found": False, "code": clean}
    return {"found": True, "product": product}


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    session: SessionDep,
    body: ProductCreate,
    _: User = Depends(require_permission("product", "create")),
):
    service = CatalogueService(session)
    try:
        return await service.create_product(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    service = CatalogueService(session)
    product = await service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product
@router.get("/products/{product_id}/qr.png")
async def product_qr_png(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    """Etiquette QR du produit (encod barcode sinon reference)."""
    import io

    import qrcode
    from fastapi.responses import Response

    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    content = product.barcode or product.reference or str(product.id)
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.put("/products/{product_id}", response_model=ProductRead)
async def update_product(
    session: SessionDep,
    product_id: int,
    body: ProductUpdate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    try:
        product = await service.update_product(product_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "delete")),
):
    service = CatalogueService(session)
    if not await service.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return None


# ------------------------------------------------------------------ #
# Catégories
# ------------------------------------------------------------------ #
@router.get("/categories", response_model=list[ProductCategoryRead])
async def list_categories(
    session: SessionDep,
    _: User = Depends(require_permission("category", "view")),
):
    result = await session.execute(
        select(ProductCategory).order_by(ProductCategory.id)
    )
    return list(result.scalars().all())


@router.get("/categories/tree")
async def get_category_tree(
    session: SessionDep,
    _: User = Depends(require_permission("category", "view")),
):
    """Arborescence des catégories avec mode de vente effectif résolu.

    - ``resolved_sale_mode`` : mode hérité (unit/length/dual)
    - ``sells_by_length`` : vrai si vente au mètre linéaire possible
    """
    service = CatalogueService(session)
    return await service.build_category_tree()


@router.post("/categories", response_model=ProductCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    session: SessionDep,
    body: ProductCategoryCreate,
    _: User = Depends(require_permission("category", "create")),
):
    category = ProductCategory(**body.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


# ------------------------------------------------------------------ #
# Unités
# ------------------------------------------------------------------ #
@router.get("/units", response_model=list[ProductUnitRead])
async def list_units(
    session: SessionDep,
    _: User = Depends(require_permission("unit", "view")),
):
    result = await session.execute(select(ProductUnit).order_by(ProductUnit.id))
    return list(result.scalars().all())


@router.post("/units", response_model=ProductUnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    session: SessionDep,
    body: ProductUnitCreate,
    _: User = Depends(require_permission("unit", "create")),
):
    unit = ProductUnit(**body.model_dump())
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


@router.get("/units/conversions", response_model=list[UnitConversionRead])
async def list_conversions(
    session: SessionDep,
    _: User = Depends(require_permission("unit", "view")),
):
    result = await session.execute(select(UnitConversion).order_by(UnitConversion.id))
    return list(result.scalars().all())


@router.post("/units/conversions", response_model=UnitConversionRead, status_code=status.HTTP_201_CREATED)
async def create_conversion(
    session: SessionDep,
    body: UnitConversionCreate,
    _: User = Depends(require_permission("unit", "create")),
):
    conv = UnitConversion(**body.model_dump())
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv
# ------------------------------------------------------------------ #
# Tôles BAC
# ------------------------------------------------------------------ #
@router.post("/bac-sheets", response_model=BACSheetRead, status_code=status.HTTP_201_CREATED)
async def create_bac_sheet(
    session: SessionDep,
    body: BACSheetCreate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    return await service.create_bac_sheet(body)


@router.get("/bac-sheets/{sheet_id}", response_model=BACSheetRead)
async def get_bac_sheet(
    session: SessionDep,
    sheet_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    service = CatalogueService(session)
    sheet = await service.get_bac_sheet(sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Tôle BAC introuvable")
    return sheet


@router.post("/bac-sheets/{sheet_id}/cuts", status_code=status.HTTP_201_CREATED)
async def add_bac_cut(
    session: SessionDep,
    sheet_id: int,
    body: BACCutCreate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    cut = await service.add_bac_cut(sheet_id, body.model_dump())
    if cut is None:
        raise HTTPException(status_code=404, detail="Tôle BAC introuvable")
    return cut


@router.delete("/bac-sheets/cuts/{cut_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bac_cut(
    session: SessionDep,
    cut_id: int,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    if not await service.delete_bac_cut(cut_id):
        raise HTTPException(status_code=404, detail="Coupe BAC introuvable")
    return None


# ------------------------------------------------------------------ #
# Import en masse (Excel / CSV)
# ------------------------------------------------------------------ #
@router.post("/products/import")
async def import_products(
    file: UploadFile,
    session: SessionDep,
    user: User = Depends(require_permission("product", "create")),
):
    """Import de produits depuis un fichier .xlsx ou .csv.

    Colonnes attendues (première ligne d'en-têtes) ::
        reference | nom | categorie | prix_achat | prix_vente | prix_ml
        | unite | vente_au_metre (oui/non) | marque | code_barre

    Ré-import idempotent : les produits existants (même référence) sont
    mis à jour. Les catégories/unités inconnues sont créées.
    """
    content = await file.read()
    rows = read_rows_from_bytes(file.filename or "import.csv", content)
    service = CatalogueImportService(session, company_id=user.company_id)
    return await service.import_products(rows)

# ------------------------------------------------------------------ #
# Variantes de produits — propriétés, valeurs, génération
# ------------------------------------------------------------------ #
@router.get("/properties", response_model=list[PropertyRead])
async def list_properties(
    session: SessionDep,
    _: User = Depends(require_permission("product", "view")),
):
    result = await session.execute(
        select(ProductProperty).order_by(ProductProperty.position, ProductProperty.id)
    )
    return list(result.scalars().all())


@router.post("/properties", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    session: SessionDep,
    body: PropertyCreate,
    user: User = Depends(require_permission("product", "create")),
):
    service = CatalogueService(session)
    try:
        return await service.create_property(body, company_id=user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    session: SessionDep,
    property_id: int,
    _: User = Depends(require_permission("product", "delete")),
):
    service = CatalogueService(session)
    if not await service.delete_property(property_id):
        raise HTTPException(status_code=404, detail="Propriété introuvable")
    return None


@router.post(
    "/properties/{property_id}/values",
    response_model=PropertyValueRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_property_value(
    session: SessionDep,
    property_id: int,
    body: PropertyValueCreate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    try:
        value = await service.add_property_value(property_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if value is None:
        raise HTTPException(status_code=404, detail="Propriété introuvable")
    return value


@router.delete("/properties/{property_id}/values/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_value(
    session: SessionDep,
    property_id: int,
    value_id: int,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    if not await service.delete_property_value(value_id):
        raise HTTPException(status_code=404, detail="Valeur introuvable")
    return None


@router.get("/products/{product_id}/variants", response_model=list[VariantRead])
async def list_variants(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    service = CatalogueService(session)
    return await service.list_variants(product_id)


@router.post("/products/{product_id}/variants/generate", response_model=list[VariantRead])
async def generate_variants(
    session: SessionDep,
    product_id: int,
    body: VariantGenerate,
    _: User = Depends(require_permission("product", "edit")),
):
    """Génère les variantes (produit cartésien des valeurs choisies)."""
    service = CatalogueService(session)
    try:
        return await service.generate_variants(product_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/variants/{variant_id}", response_model=VariantRead)
async def update_variant(
    session: SessionDep,
    variant_id: int,
    body: VariantUpdate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    variant = await service.update_variant(variant_id, body)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variante introuvable")
    return variant


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    session: SessionDep,
    variant_id: int,
    _: User = Depends(require_permission("product", "delete")),
):
    service = CatalogueService(session)
    if not await service.delete_variant(variant_id):
        raise HTTPException(status_code=404, detail="Variante introuvable")
    return None
