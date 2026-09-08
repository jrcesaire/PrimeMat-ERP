"""Services du module Ventes."""
from app.modules.sales.services.quote_service import QuoteService
from app.modules.sales.services.order_service import OrderService

__all__ = ["QuoteService", "OrderService"]