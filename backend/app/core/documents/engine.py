"""
Moteur documentaire — génération de PDF à partir de templates.

Utilise Jinja2 + WeasyPrint pour convertir des templates HTML en PDF.

Architecture ::

    Données métier → DocumentEngine → Template Jinja2 → HTML → WeasyPrint → PDF → Stockage

Indépendant des modules métier (le moteur PDF ne dépend pas du Stock,
le designer ne dépend pas de la Facturation).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.documents.context import ContextBuilder

logger = logging.getLogger(__name__)

# Répertoire des templates de documents  (<backend>/resources/templates)
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "resources",
    "templates",
)
os.makedirs(TEMPLATE_DIR, exist_ok=True)


def _fmt_addr(company: Any) -> str:
    """Formate l'adresse d'une entreprise : 'rue, ville, pays'."""
    if not company:
        return ""
    addr = getattr(company, "address", None) or {}
    parts = [addr.get("street"), addr.get("city"), addr.get("country")]
    return ", ".join(str(p) for p in parts if p)


def _fmt_contacts(company: Any) -> str:
    """Formate les contacts d'une entreprise : 'Tél : ... • email'."""
    if not company:
        return ""
    parts: list[str] = []
    if getattr(company, "phone", None):
        parts.append(f"Tél : {company.phone}")
    if getattr(company, "email", None):
        parts.append(str(company.email))
    return " • ".join(parts)


class DocumentEngine:
    """
    Moteur centralisé de génération de documents PDF.
    """

    def __init__(self, template_dir: str | None = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        os.makedirs(self.template_dir, exist_ok=True)
        self.context_builder = ContextBuilder()

        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            keep_trailing_newline=True,
        )
        # Helpers disponibles dans tous les templates de documents
        self.jinja_env.globals["fmt_addr"] = _fmt_addr
        self.jinja_env.globals["fmt_contacts"] = _fmt_contacts

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Rend un template HTML avec le contexte fourni."""
        context.setdefault("now", datetime.utcnow())
        context.setdefault("uuid", uuid.uuid4())
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def render_to_html(self, template_name: str, context: dict[str, Any]) -> str:
        """Génère le HTML du document (pour aperçu avant PDF)."""
        return self.render_template(template_name, context)

    def render_to_pdf(
        self, template_name: str, context: dict[str, Any], output_path: str | None = None
    ) -> str:
        """
        Génère un PDF à partir d'un template. Retourne le chemin du PDF.

        Moteurs (par priorité) :
        1. WeasyPrint (rendu fidèle — nécessite GTK/Pango sous Windows)
        2. xhtml2pdf (fallback pur Python, sans dépendance système)
        """
        html_content = self.render_template(template_name, context)

        if output_path is None:
            filename = f"{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(
                os.path.dirname(self.template_dir), "generated", filename
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            from weasyprint import HTML

            html = HTML(string=html_content, base_url=self.template_dir)
            html.write_pdf(output_path)
        except ImportError:
            # Fallback : xhtml2pdf (pur Python)
            from io import BytesIO

            from xhtml2pdf import pisa

            with open(output_path, "wb") as pdf_file:
                result = BytesIO()
                pisa_status = pisa.CreatePDF(
                    BytesIO(html_content.encode("utf-8")), dest=result,
                    encoding="utf-8",
                )
                pdf_file.write(result.getvalue())
            if getattr(pisa_status, "err", False):
                logger.error("xhtml2pdf : erreurs lors de la génération")

        logger.info("PDF généré : %s (template=%s)", output_path, template_name)
        return output_path

    # ------------------------------------------------------------------ #
    # Rendus spécifiques par type de document
    # ------------------------------------------------------------------ #
    def render_invoice(self, invoice_id: int) -> str:
        """Génère le PDF d'une facture."""
        import asyncio
        context = asyncio.run(self.context_builder.build_invoice_context(invoice_id))
        return self.render_to_pdf("invoice.html", context)

    def render_quote(self, quote_id: int) -> str:
        """Génère le PDF d'un devis."""
        import asyncio
        context = asyncio.run(self.context_builder.build_quote_context(quote_id))
        return self.render_to_pdf("quote.html", context)

    def render_delivery(self, delivery_id: int) -> str:
        """Génère le PDF d'un bon de livraison."""
        import asyncio
        context = asyncio.run(self.context_builder.build_delivery_context(delivery_id))
        return self.render_to_pdf("delivery.html", context)

    def render_purchase_order(self, order_id: int) -> str:
        """Génère le PDF d'un bon de commande fournisseur."""
        import asyncio
        context = asyncio.run(self.context_builder.build_purchase_order_context(order_id))
        return self.render_to_pdf("purchase_order.html", context)

    # ------------------------------------------------------------------ #
    # Gestion des templates (No-Code designer)
    # ------------------------------------------------------------------ #
    def list_templates(self) -> list[str]:
        """Liste les templates disponibles."""
        if not os.path.exists(self.template_dir):
            return []
        return [
            f for f in os.listdir(self.template_dir)
            if f.endswith((".html", ".jinja2"))
        ]

    def get_template_source(self, template_name: str) -> str:
        """Retourne le source HTML d'un template."""
        path = os.path.join(self.template_dir, template_name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def save_template(self, template_name: str, content: str) -> None:
        """Sauvegarde un template (utilisé par le designer No-Code)."""
        path = os.path.join(self.template_dir, template_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Template sauvegardé : %s", template_name)
