"""
Tâches Celery pour la génération de documents PDF.

Utilise WeasyPrint pour convertir un template HTML+Jinja2 en PDF.
"""
from __future__ import annotations

import logging

from celery import shared_task

from app.core.documents.engine import DocumentEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="pdf.generate")
def generate_pdf(self, template_name: str, context: dict) -> str:
    """
    Génère un PDF à partir d'un template et d'un contexte de données.

    Retourne le chemin relatif du fichier PDF généré.
    """
    logger.info("Génération PDF — template=%s task_id=%s", template_name, self.request.id)
    engine = DocumentEngine()
    pdf_path = engine.render_to_pdf(template_name=template_name, context=context)
    return pdf_path


@shared_task(bind=True, name="pdf.generate_invoice")
def generate_invoice_pdf(self, invoice_id: int) -> str:
    """Génère le PDF d'une facture à partir de son ID."""
    logger.info("Génération facture PDF — invoice_id=%s", invoice_id)
    engine = DocumentEngine()
    pdf_path = engine.render_invoice(invoice_id=invoice_id)
    return pdf_path


@shared_task(bind=True, name="pdf.generate_quote")
def generate_quote_pdf(self, quote_id: int) -> str:
    """Génère le PDF d'un devis à partir de son ID."""
    logger.info("Génération devis PDF — quote_id=%s", quote_id)
    engine = DocumentEngine()
    pdf_path = engine.render_quote(quote_id=quote_id)
    return pdf_path
