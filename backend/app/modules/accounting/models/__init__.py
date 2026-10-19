"""Modèles Comptabilité.

L'import garantit l'enregistrement des tables dans la metadata SQLAlchemy.
"""
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.credit_note import CreditNote
from app.modules.accounting.models.exchange_rate import ExchangeRate
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.invoice_allocation import InvoiceAllocation
from app.modules.accounting.models.journal import Journal
from app.modules.accounting.models.journal_entry import (
    JournalEntry,
    JournalEntryLine,
)
from app.modules.accounting.models.ohada import OHADAParameter

# Importer les modèles liés pour résoudre les relationships inter-modules
# (Invoice, Payment référencés par InvoiceAllocation ; Partner par Invoice, etc.)
from app.modules.crm.models.partner import Partner  # noqa: F401
from app.modules.invoicing.models.invoice import Invoice  # noqa: F401
from app.modules.payments.models.payment import Payment  # noqa: F401

__all__ = [
    "Account",
    "CreditNote",
    "ExchangeRate",
    "FiscalYear",
    "InvoiceAllocation",
    "Invoice",
    "Journal",
    "JournalEntry",
    "JournalEntryLine",
    "OHADAParameter",
    "Partner",
    "Payment",
]
