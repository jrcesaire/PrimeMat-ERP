"""
Profil de l'entreprise — complétude et configuration initiale.

Source unique de vérité : les mêmes règles alimentent l'interface (bandeau
« configuration incomplète », champs signalés dans le formulaire) et le
serveur (refus de créer un devis ou une facture tant que les informations
obligatoires manquent).

Règle métier : ces informations figurent sur les documents remis au client,
elles conditionnent donc la création d'un document — un devis ou une facture
sans téléphone ni adresse n'a aucune valeur légale.

Ne sont **pas** obligatoires (recommandés seulement) : les informations
fiscales (NCC, RCCM, greffe, code importateur, caisse sociale), le logo et
les conditions générales de vente.
"""
from __future__ import annotations

from typing import Any

from app.core.models.company import Company

#: Champs obligatoires portés directement par ``Company`` :
#: ``(attribut, libellé présenté à l'utilisateur)``.
DIRECT_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "Nom de l'entreprise"),
    ("phone", "N° de téléphone"),
    ("currency_code", "Devise"),
)

#: Champs obligatoires logés dans la colonne JSON ``Company.address``.
ADDRESS_FIELDS: tuple[tuple[str, str], ...] = (
    ("street", "Adresse"),
    ("city", "Ville"),
    ("country", "Pays"),
)

#: Clés de ``Company.address`` tenant lieu d'adresse. L'assistant comptable
#: historique écrit ``line1`` là où le présent module écrit ``street`` : les
#: deux sont acceptés, l'utilisateur n'a donc pas à ressaisir son adresse.
_STREET_KEYS: tuple[str, ...] = ("street", "line1", "address")


def _filled(value: Any) -> bool:
    """Vrai si la valeur porte un contenu réel (ni ``None``, ni blanc)."""
    return value is not None and str(value).strip() != ""


def _address_of(company: Company | None) -> dict[str, Any]:
    address = getattr(company, "address", None)
    return address if isinstance(address, dict) else {}


def missing_company_fields(company: Company | None) -> list[dict[str, str]]:
    """Champs obligatoires absents, libellés prêts pour l'interface.

    Renvoie ``[{"field": "phone", "label": "N° de téléphone"}, ...]``.
    ``field`` reprend la clé attendue par le formulaire : les champs
    d'adresse sont préfixés ``address_`` (``address_street``, ``address_city``,
    ``address_country``).

    Une entreprise absente (``None``) est traitée comme entièrement vide, ce
    qui permet d'appeler la fonction avant tout chargement.
    """
    direct = [
        {"field": field, "label": label}
        for field, label in DIRECT_FIELDS
        if not _filled(getattr(company, field, None))
    ]

    address = _address_of(company)
    from_address: list[dict[str, str]] = []
    for field, label in ADDRESS_FIELDS:
        if field == "street":
            present = any(_filled(address.get(key)) for key in _STREET_KEYS)
        else:
            present = _filled(address.get(field))
        if not present:
            from_address.append({"field": f"address_{field}", "label": label})

    return [*direct, *from_address]


def is_company_complete(company: Company | None) -> bool:
    """Vrai si tous les champs obligatoires sont renseignés."""
    return not missing_company_fields(company)


def company_profile(company: Company | None) -> dict[str, Any]:
    """État du profil, tel qu'exposé par l'API de configuration initiale."""
    missing = missing_company_fields(company)
    return {
        "company_complete": not missing,
        "missing_fields": missing,
        "missing_labels": [item["label"] for item in missing],
    }
