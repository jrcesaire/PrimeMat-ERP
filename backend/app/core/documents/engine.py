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
import threading
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


# Verrou global : un seul rendu Chromium a la fois (pic memoire maitrise).
_CHROMIUM_LOCK = threading.Lock()
_CHROMIUM_LAUNCH_ARGS = (
    "--no-sandbox",
    "--disable-dev-shm",
    "--disable-gpu",
    "--font-render-hinting=none",
)

# Pagination des documents A4.  Chromium n'implémente PAS les « margin
# boxes » CSS (``@page { @bottom { content: "Page " counter(page) } }``) :
# la pagination est donc estampillée après coup par ``_apply_pagination``
# (reportlab + pypdf) dans la bande basse de 12 mm réservée par le socle
# ``_model_base.html``.  Avantages : même rendu avec le repli xhtml2pdf et
# total de pages exact une fois l'annexe CGV concaténée.
_PAGE_FOOTER_BAND_MM = 12.0      # hauteur de bande réservée par le CSS @page
_PAGE_FOOTER_BASELINE_MM = 5.5   # ligne de base du texte, depuis le bord bas
_PAGE_FOOTER_RIGHT_MM = 8.0      # retrait du bord droit (comme le socle)
_PAGE_FOOTER_FONT_SIZE = 7.5   # 10 px CSS = 7,5 pt
_PAGE_FOOTER_COLOR = "#8a8fa3"    # gris du socle — doit rester synchro avec le CSS

# --------------------------------------------------------------------------- #
# Polices Open Sans embarquees (famille complete, hors ligne)
# --------------------------------------------------------------------------- #
# ``resources/fonts`` contient toute la famille Open Sans (Light -> ExtraBold,
# romain/italique, Condensed et SemiCondensed) + la licence OFL. Le socle
# ``_model_base.html`` porte le marqueur ``_OPEN_SANS_MARKER`` que le rendu
# remplace par des ``@font-face`` en data URI : plus aucune dépendance réseau.
# (L'ancien ``@import`` Google Fonts échouait sans accès à fonts.googleapis.com
# et Chromium basculait alors sur une police de substitution système — glyphes
# décalés dans les documents.)
FONTS_DIR = os.path.join(os.path.dirname(TEMPLATE_DIR), "fonts")
_OPEN_SANS_MARKER = "/*__OPEN_SANS_FACES__*/"
# (jeton, poids) — testés dans l'ordre (ExtraBold avant Bold, etc.)
_OPEN_SANS_WEIGHTS = (
    ("ExtraBold", 800),
    ("Semibold", 600),
    ("SemiBold", 600),
    ("Bold", 700),
    ("Medium", 500),
    ("Light", 300),
    ("Regular", 400),
    ("Italic", 400),
)
_faces_cache: list[tuple[str, int, str, str]] | None = None
_faces_css_cache: str | None = None
_fonts_registered = False


def _scan_open_sans_faces() -> list[tuple[str, int, str, str]]:
    """Scane ``resources/fonts`` -> liste ``(famille, poids, style, chemin)``.

    Famille dans {"Open Sans", "Open Sans Condensed", "Open Sans SemiCondensed"}.
    Les polices variables sont ignorées (les statiques couvrent tous les
    poids/styles). Résultat mis en cache au premier appel.
    """
    global _faces_cache
    if _faces_cache is not None:
        return _faces_cache
    faces: list[tuple[str, int, str, str]] = []
    try:
        names = sorted(os.listdir(FONTS_DIR))
    except OSError:
        names = []
    for name in names:
        if not name.lower().endswith(".ttf") or "VariableFont" in name:
            continue
        stem = name[:-4]
        if stem.startswith("OpenSans_SemiCondensed-"):
            family, rest = "Open Sans SemiCondensed", stem[len("OpenSans_SemiCondensed-"):]
        elif stem.startswith("OpenSans_Condensed-"):
            family, rest = "Open Sans Condensed", stem[len("OpenSans_Condensed-"):]
        elif stem.startswith("OpenSans-"):
            family, rest = "Open Sans", stem[len("OpenSans-"):]
        else:
            continue
        style = "italic" if "Italic" in rest else "normal"
        weight = None
        for token, value in _OPEN_SANS_WEIGHTS:
            if rest.startswith(token):
                weight = value
                break
        if weight is None:
            if rest in ("", "Italic"):
                weight = 400
            else:
                logger.debug("Police Open Sans ignorée (poids inconnu) : %s", name)
                continue
        faces.append((family, weight, style, os.path.join(FONTS_DIR, name)))
    if not faces:
        logger.warning("Aucune police Open Sans trouvée dans %s", FONTS_DIR)
    _faces_cache = faces
    return faces


def _open_sans_css() -> str:
    """Bloc CSS ``@font-face`` de la famille complète, polices en data URI.

    Construit une seule fois puis mis en cache (~6 Mo pour les 36 variantes
    statiques ; le HTML transitant en mémoire, le coût est négligeable et le
    rendu devient totalement hors ligne).
    """
    global _faces_css_cache
    if _faces_css_cache is None:
        import base64

        rules = []
        for family, weight, style, path in _scan_open_sans_faces():
            try:
                with open(path, "rb") as fh:
                    payload = base64.b64encode(fh.read()).decode("ascii")
            except OSError as exc:
                logger.warning("Police illisible (%s) : %s", exc, path)
                continue
            rules.append(
                "@font-face { font-family: '%s'; font-style: %s; font-weight: %d;"
                " src: url(data:font/ttf;base64,%s) format('truetype'); }"
                % (family, style, weight, payload)
            )
        _faces_css_cache = chr(10).join(rules)
    return _faces_css_cache


def _inject_open_sans(html: str) -> str:
    """Remplace le marqueur du socle par le CSS embarqué des polices.

    Un HTML sans marqueur (ticket POS, socle « Helvetica » du repli) est
    renvoyé inchangé : l'injection reste explicite et maîtrisée.
    """
    if _OPEN_SANS_MARKER not in html:
        return html
    css = _open_sans_css()
    if not css:
        return html.replace(
            _OPEN_SANS_MARKER,
            "/* Polices Open Sans introuvables dans resources/fonts */",
        )
    return html.replace(_OPEN_SANS_MARKER, css)


def _register_embedded_fonts() -> bool:
    """Pré-enregistre les familles Open Sans pour reportlab/xhtml2pdf.

    Utilisé par le repli xhtml2pdf — dont le chargement ``@font-face`` échoue
    sous Windows (fichier temporaire verrouillé par reportlab) — et par la
    pagination estampillée en pied de page. Idempotent, ne lève jamais.
    Retourne ``True`` si au moins une famille est enregistrée.
    """
    global _fonts_registered
    if _fonts_registered:
        return True
    faces = _scan_open_sans_faces()
    if not faces:
        return False
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        logger.warning("reportlab indisponible — polices embarquées non enregistrées")
        return False
    variants = {
        (400, "normal"): "",
        (400, "italic"): "-Italic",
        (700, "normal"): "-Bold",
        (700, "italic"): "-BoldItalic",
    }
    by_family: dict[str, dict[tuple[int, str], str]] = {}
    for family, weight, style, path in faces:
        by_family.setdefault(family, {})[(weight, style)] = path
    registered = False
    for family, table in by_family.items():
        if any(key not in table for key in variants):
            continue  # variante incomplète : famille non enregistrée
        try:
            names: dict[tuple[int, str], str] = {}
            for key, suffix in variants.items():
                name = family + suffix
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, table[key]))
                names[key] = name
            pdfmetrics.registerFontFamily(
                family,
                normal=names[(400, "normal")],
                bold=names[(700, "normal")],
                italic=names[(400, "italic")],
                boldItalic=names[(700, "italic")],
            )
            # xhtml2pdf résout les familles via xhtml2pdf.default.DEFAULT_FONT
            # (recopié dans chaque contexte) : on y ajoute les noms de famille,
            # apostrophe comprise selon le parsing CSS rencontré.
            try:
                import xhtml2pdf.default as xhtml2pdf_default

                xhtml2pdf_default.DEFAULT_FONT.setdefault(family.lower(), family)
                xhtml2pdf_default.DEFAULT_FONT.setdefault(
                    "'" + family.lower() + "'", family
                )
            except ImportError:
                pass
            registered = True
        except Exception:  # noqa: BLE001 — jamais bloquant
            logger.exception("Enregistrement de la police « %s » impossible", family)
    _fonts_registered = registered
    return registered


def _footer_font(default: str = "Helvetica") -> str:
    """Police de la pagination « Page X / Y » : Open Sans si enregistrée."""
    return "Open Sans" if _register_embedded_fonts() else default


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


def amount_in_words(amount: Any, currency: str = "FCFA") -> str:
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


def line_qty_parts(line: Any) -> tuple[str, str]:
    """Couple (quantité, unité) pour la colonne Qté des rapports.

    Sépare l'affichage de :meth:`line_qty` afin que la quantité et
    l'unité soient rendues sur deux lignes centrées et alignées
    (plus de mention « Unité : … » dans la colonne Désignation).
    """
    try:
        if getattr(line, "sell_by_length", False):
            cuts = getattr(line, "cuts", None) or []
            if cuts:
                total = sum(float(c.quantity) * float(c.length) for c in cuts)
            else:
                total = float(getattr(line, "total_length", 0) or 0)
            if total:
                unit = getattr(line, "unit", None) or "ml"
                return fmt_num(total, 2), str(unit)
        qty_attr = getattr(line, "quantity", None)
        if qty_attr is None:
            qty_attr = getattr(line, "quantity_ordered", 0) or 0
        unit = getattr(line, "unit", None) or ""
        return fmt_num(float(qty_attr or 0), 2), str(unit)
    except (TypeError, ValueError, AttributeError):
        return "", ""


def line_qty(line: Any) -> str:
    """Quantité affichée d'une ligne : métrage réel (BAC) sinon quantité.

    Pour une ligne vendue au mètre avec coupes (ex. 20 × 7,50 m +
    45 × 7,00 m), renvoie le métrage total (465,00 ml) plutôt que la
    quantité de référence (1,00).
    """
    try:
        if getattr(line, "sell_by_length", False):
            cuts = getattr(line, "cuts", None) or []
            if cuts:
                total = sum(float(c.quantity) * float(c.length) for c in cuts)
            else:
                total = float(getattr(line, "total_length", 0) or 0)
            if total:
                unit = getattr(line, "unit", None) or "ml"
                return f"{fmt_num(total, 2)} {unit}"
        return fmt_num(float(getattr(line, "quantity", 0) or 0), 2)
    except (TypeError, ValueError, AttributeError):
        return fmt_num(getattr(line, "quantity", 0) or 0, 2)


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
    # Markup.replace() echappe ses arguments non-Markup : passer un Markup
    # evite d'obtenir "&lt;br/&gt;" au lieu d'une balise de saut de ligne.
    return Markup(escape(str(value)).replace("\n", Markup("<br/>")))


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
        self.jinja_env.globals["line_qty"] = line_qty
        self.jinja_env.globals["line_qty_parts"] = line_qty_parts
        self.jinja_env.globals["fmt_num"] = fmt_num
        self.jinja_env.globals["fmt_date"] = fmt_date
        self.jinja_env.globals["status_label"] = status_label
        self.jinja_env.globals["status_class"] = status_class
        self.jinja_env.filters["nl2br"] = nl2br
        self._angle_data_uri: str | None = None

    def _angle_uri(self) -> str:
        """Data URI du triangle de découpe du bandeau (assets/angle-navy.png)."""
        if self._angle_data_uri is None:
            import base64

            path = os.path.join(self.template_dir, "assets", "angle-navy.png")
            try:
                with open(path, "rb") as f:
                    self._angle_data_uri = (
                        "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
                    )
            except OSError:
                self._angle_data_uri = ""
        return self._angle_data_uri

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Rend un template HTML avec le contexte fourni.

        Le marqueur ``/*__OPEN_SANS_FACES__*/`` du socle est remplacé
        par le CSS embarqué des polices (voir :func:`_inject_open_sans`).
        """
        context.setdefault("now", datetime.utcnow())
        context.setdefault("uuid", uuid.uuid4())
        context.setdefault("angle_png", self._angle_uri())
        template = self.jinja_env.get_template(template_name)
        return _inject_open_sans(template.render(**context))

    def render_to_html(self, template_name: str, context: dict[str, Any]) -> str:
        """Génère le HTML du document (pour aperçu avant PDF)."""
        return self.render_template(template_name, context)

    def render_to_pdf(
        self,
        template_name: str,
        context: dict[str, Any],
        output_path: str | None = None,
        append_pdf: str | None = None,
        doc_title: str | None = None,
    ) -> str:
        """
        Génère un PDF à partir d'un template. Retourne le chemin du PDF.

        Moteurs (par priorité) :
        1. Playwright/Chromium (rendu Chrome fidèle : flex, radius,
           @page/@bottom, en-têtes de tableau répétés)
        2. xhtml2pdf (repli pur Python si Chromium absent)

        ``append_pdf`` : chemin optionnel d'un PDF à concaténer à la fin
        (ex. CGV chargées par l'utilisateur) — via pypdf.

        ``doc_title`` : titre du rapport inscrit dans la métadonnée ``/Title``
        du PDF (ex. ``"Devis - DEV-000019"``).  Par défaut, la clé
        ``doc_title`` du contexte (voir :mod:`app.core.documents.naming`).
        """
        html_content = self.render_template(template_name, context)

        if output_path is None:
            filename = f"{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(
                os.path.dirname(self.template_dir), "generated", filename
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        page_width = "80mm" if template_name == "pos_ticket.html" else None
        pdf_bytes = self._render_pdf_bytes(html_content, page_width)
        with open(output_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)

        logger.info("PDF généré : %s (template=%s)", output_path, template_name)

        wm_pages: int | None = None
        if page_width is None and self._watermark_file():
            # Filigrane limité aux documents A4 (jamais le ticket POS 80 mm) et
            # appliqué AVANT la concaténation : la ou les pages CGV ajoutées
            # ensuite par ``append_pdf`` restent donc sans filigrane.
            wm_pages = self._apply_watermark(output_path)

        annex_pages = 0
        if append_pdf:
            annex_pages = self._append_pdf(output_path, append_pdf)
            if wm_pages:
                logger.info(
                    "Annexe concaténée : filigrane limité aux %d page(s) du document",
                    wm_pages,
                )

        if page_width is None:
            # Pagination « Page X / Y » : estampillée en dernier pour compter
            # l'annexe CGV (pages annexes laissées sans numéro).
            self._apply_pagination(output_path, skip_last=annex_pages)

        # Titre du rapport (ex. « Devis - DEV-000019 ») : appliqué APRÈS la
        # pagination — celle-ci réécrit le PDF avec un ``PdfWriter`` neuf, ce
        # qui effacerait une métadonnée posée plus tôt.
        self._apply_metadata(output_path, doc_title or context.get("doc_title"))
        return output_path


    # ------------------------------------------------------------------ #
    # Rendu HTML -> PDF (Playwright/Chromium prioritaire, repli xhtml2pdf)
    # ------------------------------------------------------------------ #
    def _render_pdf_bytes(self, html: str, page_width: str | None = None) -> bytes:
        """Convertit le HTML en PDF via Chromium (repli xhtml2pdf).

        ``page_width`` : ex. ``"80mm"`` pour le ticket POS (A4 sinon).
        """
        try:
            return self._render_with_chromium(html, page_width)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rendu Chromium impossible (%s) - repli xhtml2pdf", exc)
        from io import BytesIO

        from xhtml2pdf import pisa

        _register_embedded_fonts()  # familles Open Sans pour reportlab
        buf = BytesIO()
        safe_html = self._xhtml2pdf_safe_html(html, page_width)
        status = pisa.CreatePDF(BytesIO(safe_html.encode("utf-8")), dest=buf, encoding="utf-8")
        if getattr(status, "err", False):
            logger.error("xhtml2pdf : erreurs lors de la generation")
        return buf.getvalue()

    @staticmethod
    def _xhtml2pdf_safe_html(html: str, page_width: str | None = None) -> str:
        """Nettoie le HTML pour le moteur de repli xhtml2pdf.

        xhtml2pdf ne gère pas les « margin boxes » CSS (``@bottom``,
        ``@top-left``…) et lève une ``TypeError`` à leur lecture. On les
        retire en conservant le reste de la feuille de style : le repli
        produit un PDF dégradé (mise en page simplifiée) mais exploitable.

        ``page_width`` (ticket POS ``80mm``) : la largeur déclarée dans les
        ``@page`` du template est remplacée par celle du rouleau.
        """
        import re

        html = re.sub(
            r"@(?:top|bottom|left|right)(?:-[a-z]+)?\s*\{[^{}]*\}",
            "",
            html,
            flags=re.IGNORECASE,
        )
        # @font-face : le chargement xhtml2pdf des TTF échoue sous
        # Windows (fichier temporaire verrouillé par reportlab). Les
        # familles sont enregistrées en amont via
        # _register_embedded_fonts() ; les règles data URI ne servent
        # qu'à Chromium et sont retirées ici.
        html = re.sub(r"@font-face\s*\{[^{}]*\}", "", html, flags=re.IGNORECASE)
        # @page :first — le parseur CSS d/xhtml2pdf plante (TypeError)
        # sur les pseudo-pages ; la pagination n'étant pas gérée de toute
        # façon, elles sont retirées comme les margin boxes.
        html = re.sub(r"@page\s*:[^{]*\{[^{}]*\}", "", html, flags=re.IGNORECASE)
        if page_width:
            html = re.sub(r"(?i)(@page\s*\{[^}]*?)\bsize\s*:[^;}]*;?", r"\1", html)
            html = (
                "<style>@page { size: %s 297mm; margin: 0; }</style>" % page_width
            ) + html
        return html

    def _render_with_chromium(self, html: str, page_width: str | None = None) -> bytes:
        """Rendu HTML -> PDF via Chromium headless (fidelite Chrome).

        Aucune URL externe : seul notre HTML local est charge (set_content),
        sans JavaScript. Un verrou global limite a un rendu a la fois.

        Documents A4 : la pagination « Page X / Y » est estampillée après
        coup (``_apply_pagination``), Chromium ignorant les « margin
        boxes » CSS du socle.  Ticket POS (``page_width``) : format
        rouleau, sans pagination.
        """
        from playwright.sync_api import sync_playwright

        with _CHROMIUM_LOCK:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(args=list(_CHROMIUM_LAUNCH_ARGS))
                try:
                    page = browser.new_page(java_script_enabled=False)
                    page.set_content(html, wait_until="load")
                    # Les @font-face data URI font partie du document :
                    # attendre leur résolution avant l'impression
                    # (best-effort — document.fonts reste accessible
                    # même avec le JS désactivé sur la page).
                    try:
                        page.evaluate("async () => { await document.fonts.ready; }")
                    except Exception:  # noqa: BLE001 — jamais bloquant
                        logger.debug("document.fonts.ready indisponible", exc_info=True)
                    kwargs = {
                        "format": "A4",
                        "print_background": True,
                        "prefer_css_page_size": True,
                        "margin": {"top": "0", "bottom": "0", "left": "0", "right": "0"},
                    }
                    if page_width:
                        kwargs.pop("format", None)
                        kwargs["width"] = page_width
                    return bytes(page.pdf(**kwargs))
                finally:
                    browser.close()

    def _watermark_file(self) -> str | None:
        """Chemin de l'image de filigrane chargée (None si absente).

        Convention : ``resources/uploads/watermark.png`` ou ``.jpg`` —
        écrite par les endpoints /core/settings/watermark.
        """
        base = os.path.join(os.path.dirname(self.template_dir), "uploads", "watermark")
        for ext in (".png", ".jpg", ".jpeg"):
            candidate = base + ext
            if os.path.isfile(candidate):
                return candidate
        return None

    def _watermark_opacity(self) -> float:
        """Opacité du filigrane, en facteur 0.01–1.0 (défaut 0.10).

        Lue dans le paramètre ``watermark_opacity`` (pourcentage entier
        1–100, enregistré depuis l'onglet Paramètres → Documents), via la
        même mécanique que ``_cgv_pdf_path`` : session DB ouverte dans le
        thread de rendu (aucune boucle asyncio n'y tourne, ``asyncio.run``
        y est donc licite). Ne lève jamais : en cas de doute, l'opacité
        par défaut de 10 % est conservée.
        """
        pct = 10
        try:
            import asyncio

            from app.core.services.setting_service import SettingService

            async def _get_opacity() -> Any:
                from app.core.database import AsyncSessionLocal

                async with AsyncSessionLocal() as session:
                    return await SettingService(session).get(
                        "watermark_opacity", "10"
                    )

            pct = int(str(asyncio.run(_get_opacity())).strip())
        except Exception:  # noqa: BLE001 — repli silencieux sur 10 %
            logger.warning("Opacité du filigrane illisible — repli à 10 pourcent")
        return min(max(pct, 1), 100) / 100.0

    def _apply_watermark(self, pdf_path: str) -> int:
        """Appose le filigrane par-dessus chaque page du PDF (translucide).

        L'image est dessinée centrée (55 % de la largeur) avec l'opacité
        paramétrée (``watermark_opacity``, 10 % par défaut) via reportlab,
        puis fusionnée AU-DESSUS du contenu de chaque page
        (``merge_page(..., over=True)``) via pypdf. Le dessus est requis car
        les pages ont un fond opaque (blanc/bleu du template) qui masquerait
        tout filigrane placé en dessous. La faible opacité garantit que le
        texte reste lisible. Ne lève jamais d'erreur bloquante : en cas
        d'échec, le PDF est conservé sans filigrane.

        Retourne le nombre de pages filigranées (0 si aucun filigrane) :
        appelée avant la concaténation de l'annexe CGV, seules les pages du
        document — et non l'annexe — sont marquées.
        """
        wm_path = self._watermark_file()
        if wm_path is None:
            return 0
        opacity = self._watermark_opacity()
        try:
            import io

            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas

            reader = PdfReader(pdf_path)
            if not reader.pages:
                return 0
            first = reader.pages[0]
            pw = float(first.mediabox.width)
            ph = float(first.mediabox.height)

            img = ImageReader(wm_path)
            iw, ih = img.getSize()
            scale = (pw * 0.55) / iw
            target_w = iw * scale
            target_h = ih * scale
            max_h = ph * 0.5
            if target_h > max_h:
                scale = max_h / ih
                target_w = iw * scale
                target_h = max_h

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            c.saveState()
            c.setFillAlpha(opacity)
            try:
                c.setStrokeAlpha(opacity)
            except Exception:
                pass
            c.drawImage(
                img,
                (pw - target_w) / 2,
                (ph - target_h) / 2,
                width=target_w,
                height=target_h,
                mask="auto",
            )
            c.restoreState()
            c.showPage()
            c.save()

            wm_page = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
            writer = PdfWriter()
            # Fusion du filigrane PAR-DESSUS chaque page (pypdf : par défaut
            # ``page.merge_page(other)`` place ``other`` au-dessus).  Le fond
            # opaque du template (body ``background: #fff``, bandeaux bleus)
            # masquerait totalement un filigrane placé en dessous — c'était
            # l'origine du bug « filigrane absent ».
            for page in reader.pages:
                page.merge_page(wm_page)
                writer.add_page(page)
            tmp = pdf_path + ".wm"
            with open(tmp, "wb") as fh:
                writer.write(fh)
            os.replace(tmp, pdf_path)
            pages = len(reader.pages)
            logger.info("Filigrane appliqué : %s (%d page(s))",
                        os.path.basename(pdf_path), pages)
            return pages
        except Exception:  # noqa: BLE001 — le filigrane ne doit jamais bloquer
            logger.exception("Échec filigrane — document conservé sans filigrane")
            return 0

    @staticmethod
    def _append_pdf(base_path: str, append_path: str) -> int:
        """Concatène ``append_path`` (ex. CGV) à la fin du PDF ``base_path``.

        Retourne le nombre de pages ajoutées (0 si la fusion n'a pas eu
        lieu).  Ne lève jamais d'erreur bloquante : en cas d'échec, le PDF de
        base est conservé tel quel.
        """
        if not os.path.isfile(append_path):
            logger.warning("PDF à concaténer introuvable : %s", append_path)
            return 0
        if os.path.abspath(append_path) == os.path.abspath(base_path):
            logger.warning("Fusion ignorée : le PDF joint est le document lui-même")
            return 0
        try:
            from pypdf import PdfReader, PdfWriter

            added = len(PdfReader(append_path).pages)
            writer = PdfWriter()
            writer.append(base_path)
            writer.append(append_path)
            tmp_path = base_path + ".tmp"
            with open(tmp_path, "wb") as fh:
                writer.write(fh)
            os.replace(tmp_path, base_path)
            pages = len(PdfReader(base_path).pages)
            logger.info("PDF concaténé (%s) → %s pages au total",
                        os.path.basename(append_path), pages)
            return added
        except ImportError:
            logger.warning("pypdf indisponible — CGV PDF non concaténée")
            return 0
        except Exception:  # noqa: BLE001 — la fusion ne doit jamais bloquer
            logger.exception("Échec de fusion PDF — document de base conservé")
            return 0

    def _apply_pagination(self, pdf_path: str, skip_last: int = 0) -> int:
        """Estampille « Page X / Y » en bas à droite des pages du document.

        Chromium n'implémente pas les « margin boxes » CSS du socle
        (``@page { @bottom { … } }``) : le texte est donc dessiné par
        reportlab dans la bande basse de 12 mm réservée par le CSS
        (``_model_base.html``) puis fusionné sur chaque page via pypdf.

        ``skip_last`` : nombre de pages finales laissées intactes (annexe
        CGV concaténée).  Le total ``Y`` compte l'ensemble des pages du PDF,
        les pages annexes n'étant pas numérotées.  Documents d'une seule
        page : aucune mention (inutile).  Ne lève jamais d'erreur bloquante.
        """
        try:
            import io

            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.colors import HexColor
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas

            reader = PdfReader(pdf_path)
            total = len(reader.pages)
            numbered = total - max(0, skip_last)
            if total <= 1 or numbered <= 0:
                return 0

            footer_font = _footer_font()
            writer = PdfWriter()
            for index, page in enumerate(reader.pages):
                if index < numbered:
                    pw = float(page.mediabox.width)
                    ph = float(page.mediabox.height)
                    label = f"Page {index + 1} / {total}"
                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=(pw, ph))
                    c.setFont(footer_font, _PAGE_FOOTER_FONT_SIZE)
                    c.setFillColor(HexColor(_PAGE_FOOTER_COLOR))
                    x = pw - (_PAGE_FOOTER_RIGHT_MM * mm) - c.stringWidth(
                        label, footer_font, _PAGE_FOOTER_FONT_SIZE
                    )
                    c.drawString(x, _PAGE_FOOTER_BASELINE_MM * mm, label)
                    c.showPage()
                    c.save()
                    stamp = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
                    page.merge_page(stamp)
                writer.add_page(page)

            tmp = pdf_path + ".pg"
            with open(tmp, "wb") as fh:
                writer.write(fh)
            os.replace(tmp, pdf_path)
            logger.info("Pagination ajoutée : %s (%d page(s) numérotée(s) / %d)",
                        os.path.basename(pdf_path), numbered, total)
            return numbered
        except ImportError:
            logger.warning("pypdf/reportlab indisponible — pagination ignorée")
            return 0
        except Exception:  # noqa: BLE001 — la pagination ne doit jamais bloquer
            logger.exception("Échec pagination — document conservé tel quel")
            return 0

    def _apply_metadata(self, pdf_path: str, title: str | None) -> bool:
        """Inscrit le titre du rapport dans la métadonnée ``/Title`` du PDF.

        Chromium reprend la balise ``<title>`` du HTML mais ``_apply_pagination``
        réécrit ensuite le fichier avec un ``PdfWriter`` neuf (métadonnée
        perdue), et le moteur de repli xhtml2pdf n'en pose aucune : le titre
        est donc estampillé ici, à la toute fin du rendu.

        C'est lui qui nomme l'onglet du lecteur PDF et le fichier proposé à
        l'enregistrement (``Devis - DEV-000019.pdf``).  Ne lève jamais
        d'erreur bloquante.
        """
        if not title:
            return False
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            logger.warning("pypdf indisponible — titre du PDF ignoré")
            return False
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata(
                {
                    "/Title": str(title),
                    "/Producer": "ERP Matériaux de construction",
                }
            )
            tmp = pdf_path + ".meta"
            with open(tmp, "wb") as fh:
                writer.write(fh)
            os.replace(tmp, pdf_path)
            logger.info(
                "Titre PDF appliqué : « %s » (%s)", title, os.path.basename(pdf_path)
            )
            return True
        except Exception:  # noqa: BLE001 — un titre manquant ne doit jamais bloquer
            logger.exception("Échec du titre PDF — document conservé tel quel")
            return False

    # ------------------------------------------------------------------ #
    # Rendus spécifiques par type de document
    # ------------------------------------------------------------------ #
    def render_invoice(self, invoice_id: int) -> str:
        """Génère le PDF d'une facture (+ CGV PDF si chargée)."""
        import asyncio
        context = asyncio.run(self.context_builder.build_invoice_context(invoice_id))
        return self.render_to_pdf(
            "invoice.html", context, append_pdf=self._cgv_pdf_path()
        )

    async def arender_invoice(self, invoice_id: int) -> str:
        """Version async de render_invoice (routes FastAPI).

        Le contexte est construit avec ``await`` et le rendu PDF (bloquant)
        est exécuté dans un thread via ``asyncio.to_thread``.
        """
        import asyncio

        context = await self.context_builder.build_invoice_context(invoice_id)
        append = await self._acgv_pdf_path()
        return await asyncio.to_thread(
            self.render_to_pdf, "invoice.html", context, None, append
        )

    async def arender_quote(self, quote_id: int) -> str:
        """Version async de render_quote (routes FastAPI)."""
        import asyncio

        context = await self.context_builder.build_quote_context(quote_id)
        append = await self._acgv_pdf_path()
        return await asyncio.to_thread(
            self.render_to_pdf, "quote.html", context, None, append
        )

    async def arender_delivery(self, delivery_id: int) -> str:
        """Version async de render_delivery (routes FastAPI).

        Le rendu PDF (bloquant, moteur Chromium) est exécuté dans un thread :
        l'API synchrone de Playwright est interdite dans la boucle asyncio.
        """
        import asyncio

        context = await self.context_builder.load_delivery(delivery_id)
        return await asyncio.to_thread(self.render_to_pdf, "delivery.html", context)

    async def arender_payment(self, payment_id: int) -> str:
        """Version async de render_payment (reçu de paiement, routes FastAPI)."""
        import asyncio

        context = await self.context_builder.load_payment(payment_id)
        return await asyncio.to_thread(self.render_to_pdf, "receipt.html", context)

    async def arender_pos_ticket(self, order_id: int) -> str:
        """Version async du ticket POS 80 mm (routes FastAPI)."""
        import asyncio

        context = await self.context_builder.load_pos(order_id)
        return await asyncio.to_thread(
            self.render_to_pdf, "pos_ticket.html", context, None, None
        )

    async def _acgv_pdf_path(self) -> str | None:
        """Version async de _cgv_pdf_path (routes FastAPI).

        Utilise le localisateur du tenant porté par la session courante
        (bypass explicite du filtre auto) plutôt que le contexte de requête.
        """
        from sqlalchemy import select as _select

        from app.core.database import AsyncSessionLocal
        from app.core.models.setting import Setting
        from app.core.services.setting_service import _CACHE

        async with AsyncSessionLocal() as session:
            company_id = getattr(session.sync_session, "info", {}).get("company_id")
            cached = _CACHE.get((company_id, "cgv_pdf_path"))
            rel = cached if cached is not None else ""
            if not rel:
                result = await session.execute(
                    _select(Setting).where(Setting.key == "cgv_pdf_path")
                )
                rows = result.scalars().all()
                for row in rows:
                    if row.company_id == company_id or (row.company_id is None and not rel):
                        rel = (row.value or "").strip()
                if not rel and rows:
                    rel = (rows[0].value or "").strip()
        if not rel:
            return None
        full = os.path.join(os.path.dirname(self.template_dir), rel)
        return full if os.path.isfile(full) else None

    def render_quote(self, quote_id: int) -> str:
        """Génère le PDF d'un devis (+ CGV PDF si chargée)."""
        import asyncio
        context = asyncio.run(self.context_builder.build_quote_context(quote_id))
        return self.render_to_pdf(
            "quote.html", context, append_pdf=self._cgv_pdf_path()
        )

    def _cgv_pdf_path(self) -> str | None:
        """Chemin du PDF CGV chargé par l'utilisateur (None si absent).

        Chemin stocké dans le paramètre ``cgv_pdf_path``, relatif au
        répertoire ``resources/``.
        """
        import asyncio

        from app.core.services.setting_service import SettingService

        async def _get_path() -> str:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                return await SettingService(session).get("cgv_pdf_path", "") or ""

        rel = asyncio.run(_get_path()).strip()
        if not rel:
            return None
        full = os.path.join(os.path.dirname(self.template_dir), rel)
        return full if os.path.isfile(full) else None

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
