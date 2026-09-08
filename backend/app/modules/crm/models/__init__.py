"""Models du module CRM."""
from app.modules.crm.models.partner import Partner, Contact, PartnerAddress
from app.modules.crm.models.site import Site

__all__ = ["Partner", "Contact", "PartnerAddress", "Site"]