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


# --------------------------------------------------------------------------- #
# Helpers de formatage (disponibles dans tous les templates)
# --------------------------------------------------------------------------- #

_UNITE_FR = [
    "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
    "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze",
    "seize", "dix-sept", "dix-huit", "dix-neuf",
]
_DIZAINE_FR = {
    2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante",
    6: "soixante", 7: "soixante", 8: "quatre-vingt", 9: "quatre-vingt",
}


def _centaines_to_words(n: int) -> str:
    """Convertit 0..999 en lettres francaises."""
    if n < 20:
        return _UNITE_FR[n]
    if n < 100:
        d, u = divmod(n, 10)
        base = _DIZAINE_FR[d]
        if d in (7, 9) and u < 10:
            if u == 0:
                return base + "-dix"
            if u == 1:
                return base + (" et onze" if d == 7 else "-onze")
            return base + "-" + _UNITE_FR[u + 10]
        if u == 1 and d != 8:
            return f"{base} et un"
        if u == 0 and d == 8:
            return base
        return f"{base}-{_UNITE_FR[u]}" if u else base
    c, rest = divmod(n, 100)
    if c == 1:
        prefix = "cent" + (" " + _centaines_to_words(rest) if rest else "")
    else:
        prefix = _UNITE_FR[c] + " cent"
        if rest:
            prefix += " " + _centaines_to_words(rest)
        else:
            prefix += "s"
    return prefix


def _number_to_words_fr(n: int) -> str:
    """Convertit un entier (>= 0) en lettres francaises."""
    if n == 0:
        return "zero"
    parts: list[str] = []
    for value, label, plural in ((10**9, "milliard", True), (10**6, "million", True)):
        count, n = divmod(n, value)
        if count:
            head = _centaines_to_words(count) + " " + label
            if plural and count > 1:
                head += "s"
            parts.append(head)
    count, n = divmod(n, 1000)
    if count:
        parts.append("mille" if count == 1 else _centaines_to_words(count) + " mille")
    if n or not parts:
        parts.append(_centaines_to_words(n))
    return " ".join(parts)


def amount_in_words(amount: Any, currency: str = "XOF") -> str:
    """Montant en lettres : "quatre-vingt-douze mille cinq cents francs CFA"."""
    try:
        total = int(round(float(amount)))
    except (TypeError, ValueError):
        return ""
    unit_name = "francs CFA" if currency.upper() in ("XOF", "FCFA", "") else currency
    words = _number_to_words_fr(total)
    if total >= 1_000_000:
        # "deux millions" -> "deux millions de francs CFA"
        unit_name = "de " + unit_name
    centimes = int(round((float(amount) - total) * 100))
    if centimes:
        return f"{words} {unit_name} et {_number_to_words_fr(centimes)} centimes"
    return f"{words} {unit_name}"


def cut_label(cut: Any) -> str:
    """Sous-ligne de coupe : "10 feuilles de 5,50 m"."""
    try:
        fqty = float(cut.quantity)
        length = f"{float(cut.length):.2f}".replace(".", ",")
    except (TypeError, ValueError, AttributeError):
        return ""
    qty = int(fqty) if fqty.is_integer() else f"{fqty:g}".replace(".", ",")
    return f"{qty} feuilles de {length} m"


def fmt_num(value: Any, decimals: int = 0) -> str:
    """Format francais : separateur de milliers espace, virgule decimale."""
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        n = 0.0
    return f"{n:,.{decimals}f}".replace(",", " ").replace(".", ",")


def fmt_date(value: Any) -> str:
    """Date jj/mm/aaaa (chaine vide si absente)."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%d/%m/%Y")


def status_label(status: Any) -> str:
    """Libelle francais du statut d un document."""
    labels = {
        "draft": "Brouillon", "confirmed": "Confirme", "posted": "Validee",
        "paid": "Payee", "partial": "Partiel", "unpaid": "Impayee",
        "cancelled": "Annulee", "pending": "En attente", "sent": "Expedie",
        "delivered": "Livree", "planned": "Prevu",
    }
    return labels.get(str(status or ""), str(status or ""))


def nl2br(value: Any) -> str:
    """Echappe un texte multiligne et convertit les retours en <br/> (CGV)."""
    from markupsafe import Markup, escape

    if not value:
        return ""
    return Markup(escape(str(value)).replace("\n", "<br/>"))


def status_class(status: Any) -> str:
    """Classe CSS du pill de statut (palette du modele)."""
    mapping = {
        "paid": "status-paid", "partial": "status-partial",
        "pending": "status-pending", "unpaid": "status-unpaid",
        "cancelled": "status-cancelled", "posted": "status-paid",
        "confirmed": "status-partial", "draft": "status-cancelled",
    }
    return mapping.get(str(status or ""), "status-cancelled")


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
        self.jinja_env.globals["amount_in_words"] = amount_in_words
        self.jinja_env.globals["cut_label"] = cut_label
        self.jinja_env.globals["fmt_num"] = fmt_num
        self.jinja_env.globals["fmt_date"] = fmt_date
        self.jinja_env.globals["status_label"] = status_label
        self.jinja_env.globals["status_class"] = status_class
        self.jinja_env.filters["nl2br"] = nl2br

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
