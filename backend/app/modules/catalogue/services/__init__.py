"""Services du module Catalogue."""
from app.modules.catalogue.services.product_service import (
    CatalogueService,
    compute_bac_line,
)

__all__ = ["CatalogueService", "compute_bac_line"]
