"""
Nommage des documents générés — « <Titre du rapport> - <Référence>.pdf ».

Source unique de vérité pour les trois surfaces qui doivent porter le même
nom (ex. ``Devis - DEV-000019.pdf``) :

1. le titre affiché — balise ``<title>`` des templates (onglet navigateur,
   impression navigateur) ;
2. la métadonnée ``/Title`` du PDF (onglet du lecteur PDF, nom proposé à
   l'enregistrement) ;
3. l'en-tête HTTP ``Content-Disposition`` (téléchargement direct).

Les accents sont conservés (les systèmes de fichiers modernes les gèrent) ;
l'en-tête HTTP les déclare en RFC 5987 (``filename*=UTF-8''…``) car la forme
``filename="…"`` doit rester de l'ASCII pur.
"""
from __future__ import annotations

import unicodedata
from typing import Any
from urllib.parse import quote

#: Titres de rapport par type de document (alignés sur les templates).
DOC_TITLES: dict[str, str] = {
    "quote": "Devis",
    "invoice": "Facture",
    "delivery": "Bon de Livraison",
    "receipt": "Reçu de Paiement",
    "pos_ticket": "Ticket de caisse",
    "purchase_order": "Bon de Commande",
}

#: Caractères interdits dans un nom de fichier (Windows) + séparateurs de chemin.
_FORBIDDEN = '<>:"/\\|?*'

#: Séparateur entre le titre du rapport et la référence du document.
_SEPARATOR = " - "


def _clean(value: Any) -> str:
    """Normalise un fragment de nom : espaces réduits, caractères interdits neutralisés."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return "".join("_" if char in _FORBIDDEN else char for char in text)


def document_title(kind: str, reference: Any | None = None) -> str:
    """Titre du rapport : ``"Devis - DEV-000019"``.

    ``kind`` : clé de :data:`DOC_TITLES` (``"quote"``, ``"invoice"``,
    ``"delivery"``, ``"receipt"``, ``"pos_ticket"``, ``"purchase_order"``).
    Sans référence exploitable, seul le titre est retourné.
    """
    label = DOC_TITLES.get(str(kind), str(kind).replace("_", " ").capitalize())
    ref = _clean(reference)
    return f"{label}{_SEPARATOR}{ref}" if ref else label


def document_filename(kind: str, reference: Any | None = None, extension: str = "pdf") -> str:
    """Nom de fichier du document : ``"Devis - DEV-000019.pdf"``."""
    name = _clean(document_title(kind, reference)).strip(" .")
    return f"{name}.{extension}" if name else f"document.{extension}"


def ascii_fallback(filename: str) -> str:
    """Version ASCII du nom de fichier (repli ``filename="…"`` de l'en-tête HTTP).

    ``"Reçu de Paiement - REC-000001.pdf"`` → ``"Recu de Paiement - REC-000001.pdf"``.
    """
    decomposed = unicodedata.normalize("NFKD", filename)
    ascii_name = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")
    return _clean(ascii_name) or "document.pdf"


def content_disposition(filename: str, inline: bool = True) -> str:
    """En-tête ``Content-Disposition`` portant le nom du rapport.

    ``inline`` : aperçu dans l'onglet du navigateur (comportement des routes
    d'impression/aperçu) ; ``attachment`` : téléchargement direct.

    Un nom purement ASCII est déclaré une seule fois ; dès qu'il contient un
    caractère non ASCII (« Reçu »), la forme RFC 5987 ``filename*=UTF-8''…``
    est ajoutée en complément du repli ASCII.
    """
    disposition = "inline" if inline else "attachment"
    fallback = ascii_fallback(filename)
    if fallback == filename:
        return f'{disposition}; filename="{fallback}"'
    encoded = quote(filename, safe="")
    return f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'
