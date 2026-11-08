"""Plans comptables embarqués et registre des référentiels.

Deux référentiels sont tenus, tous deux issus de l'acte uniforme OHADA et
partageant l'arborescence des classes 1 à 9 :

- ``SYSCOHADA`` — plan commercial (``ohada_chart``), 1 411 comptes ;
- ``SYCEBNL`` — entités à but non lucratif (``sycebnl_chart``), 1 103 comptes.

Les modules de données sont **générés** par
``backend/scripts/build_account_charts.py`` : ne pas les modifier à la main.

Chaque compte est un tuple ``(code, libellé, nom_technique)``. Le code porte
six chiffres — le code SYSCOHADA à quatre chiffres complété de deux zéros —
et ``significant_code()`` en retire le remplissage pour retrouver le code du
plan officiel, ce qui rend les règles de typage indépendantes du référentiel.
"""

from __future__ import annotations

from enum import Enum

from app.modules.accounting.data.ohada_chart import SYSCOHADA_ACCOUNTS
from app.modules.accounting.data.sycebnl_chart import SYCEBNL_ACCOUNTS
from app.shared.enums import CHART_OF_ACCOUNTS_DEFAULT

#: Un compte du plan : ``(code, libellé, nom_technique)``.
AccountRow = tuple[str, str, str]

#: Registre des plans disponibles, indexé par valeur de référentiel.
ACCOUNT_CHARTS: dict[str, list[AccountRow]] = {
    "SYSCOHADA": SYSCOHADA_ACCOUNTS,
    "SYCEBNL": SYCEBNL_ACCOUNTS,
}

#: Libellés des référentiels, pour l'interface (assistant, paramètres).
CHART_LABELS: dict[str, str] = {
    "SYSCOHADA": "SYSCOHADA — plan commercial",
    "SYCEBNL": "SYCEBNL — entités à but non lucratif",
}

#: Compte témoin de chaque référentiel : sa présence dans le plan d'une
#: entreprise prouve que le plan courant y est chargé. Il sert aussi à détecter
#: un plan hérité d'une codification antérieure (comptes à 2 à 4 chiffres),
#: qu'il faut recharger.
PROBE_ACCOUNTS: dict[str, str] = {
    "SYSCOHADA": "411000",
    "SYCEBNL": "410000",
}


#: Clés métier désignant un compte du plan, par référentiel.
#:
#: Ces clés sont le vocabulaire stable du logiciel : le code, lui, change d'un
#: référentiel à l'autre — et le SYSCOHADA Révisé a lui-même renuméroté les
#: classes 1, 5, 6 et 7 (``64`` impôts et taxes, ``66`` charges de personnel,
#: ``77`` revenus financiers…). Aucun code n'est donc codé en dur dans les
#: services : ils passent tous par cette table.
#:
#: Une clé peut manquer dans un référentiel — le SYCEBNL n'a pas de compte de
#: « ventes retournées » distinct, ni de matières premières. ``resolve_account``
#: retourne alors ``None`` et l'appelant choisit son repli.
SEMANTIC_ACCOUNTS: dict[str, dict[str, str]] = {
    "SYSCOHADA": {
        # Tiers
        "customers": "411000",
        "suppliers": "401000",
        # État
        "tax_collected": "443000",
        "tax_deductible": "445000",
        "vat_payable": "444000",
        # Produits et achats
        "sales_revenue": "701000",
        "purchases": "601000",
        "sales_discounts": "701900",
        "purchase_discounts": "601900",
        "raw_materials": "602000",
        "consumables": "604000",
        "office_supplies": "604700",
        "water": "605100",
        "other_purchases": "605000",
        "fuel": "604000",
        # Trésorerie
        "cash": "571000",
        "bank": "521000",
        # Charges d'exploitation
        "transport": "612000",
        "subcontracting": "621000",
        "rent": "622000",
        "repairs": "624000",
        "insurance": "625000",
        "documentation": "626000",
        "advertising": "627000",
        "telecom": "628000",
        "bank_fees": "631000",
        "professional_fees": "632000",
        "taxes": "641000",
        "salaries": "661000",
        "misc_expenses": "658000",
        # Clôture d'exercice — ces quatre comptes portent les mêmes codes dans
        # les deux référentiels.
        "result_profit": "131000",
        "result_loss": "139000",
        "retained_credit": "121000",
        "retained_debit": "129000",
        # Paie (module Payroll)
        "payroll_payable": "422000",
        "social_charges": "431000",
        "income_tax": "447000",
    },
    "SYCEBNL": {
        # Tiers — l'entité non lucrative sert des clients-usagers.
        "customers": "412000",
        "suppliers": "401000",
        # État
        "tax_collected": "443000",
        "tax_deductible": "445000",
        "vat_payable": "444000",
        # Produits et achats
        "sales_revenue": "705000",
        "purchases": "602000",
        "purchase_discounts": "601900",
        "consumables": "604000",
        "office_supplies": "604700",
        "water": "605100",
        "other_purchases": "605000",
        "fuel": "604000",
        # Trésorerie
        "cash": "570000",
        "bank": "521000",
        # Charges d'exploitation
        "transport": "610000",
        "subcontracting": "621000",
        "rent": "622000",
        "repairs": "624000",
        "insurance": "625000",
        "documentation": "626000",
        "advertising": "627000",
        "telecom": "628000",
        "bank_fees": "631000",
        "professional_fees": "632000",
        "taxes": "641000",
        "salaries": "661000",
        "misc_expenses": "658000",
        # Clôture d'exercice : excédent et déficit de l'exercice.
        "result_profit": "131000",
        "result_loss": "139000",
        "retained_credit": "121000",
        "retained_debit": "129000",
        # Paie (module Payroll)
        "payroll_payable": "422000",
        "social_charges": "431000",
        "income_tax": "447000",
    },
}

#: Mode de règlement → nature de trésorerie (clé de ``SEMANTIC_ACCOUNTS``).
TREASURY_KINDS: dict[str, str] = {
    "cash": "cash",
    "bank_transfer": "bank",
    "check": "bank",
    "card": "bank",
    "mobile_money": "bank",
    "other": "bank",
}

#: Nature d'une dépense (catégorie saisie) → clé de ``SEMANTIC_ACCOUNTS``.
EXPENSE_NATURES: dict[str, str] = {
    "achat": "purchases",
    "marchandise": "purchases",
    "stock": "purchases",
    "matiere": "raw_materials",
    "matière": "raw_materials",
    "fourniture": "office_supplies",
    "fournitures": "office_supplies",
    "eau": "water",
    "electricite": "other_purchases",
    "électricité": "other_purchases",
    "electricity": "other_purchases",
    "energie": "other_purchases",
    "énergie": "other_purchases",
    "fuel": "fuel",
    "carburant": "fuel",
    "transport": "transport",
    "livraison": "transport",
    "loyer": "rent",
    "entretien": "repairs",
    "maintenance": "repairs",
    "assurance": "insurance",
    "publicite": "advertising",
    "publicité": "advertising",
    "marketing": "advertising",
    "documentation": "documentation",
    "telecom": "telecom",
    "telephone": "telecom",
    "téléphone": "telecom",
    "internet": "telecom",
    "frais_bancaires": "bank_fees",
    "honoraires": "professional_fees",
    "impots": "taxes",
    "impôts": "taxes",
    "taxes": "taxes",
    "salaire": "salaries",
    "salaires": "salaries",
    "personnel": "salaries",
}

#: Repli lorsque la nature d'une dépense n'est pas reconnue.
DEFAULT_EXPENSE_KEY = "misc_expenses"


def resolve_account(template: str | Enum | None, key: str) -> str | None:
    """Code du compte désigné par ``key``, ou ``None`` s'il n'existe pas.

    L'absence est un cas normal : elle signale que la notion n'a pas
    d'équivalent dans ce référentiel, à charge de l'appelant de replier.
    """
    return SEMANTIC_ACCOUNTS.get(chart_key(template), {}).get(key)


def resolve_accounts(template: str | Enum | None) -> dict[str, str]:
    """Table d'alias complète du référentiel (copie modifiable)."""
    return dict(SEMANTIC_ACCOUNTS.get(chart_key(template), {}))


def treasury_kind(payment_method: str | None) -> str:
    """Nature de trésorerie d'un mode de règlement — banque par défaut."""
    return TREASURY_KINDS.get((payment_method or "").strip().lower(), "bank")


def expense_key(category: str | None) -> str:
    """Clé d'alias du compte de charge d'une catégorie de dépense."""
    return EXPENSE_NATURES.get((category or "").strip().lower(), DEFAULT_EXPENSE_KEY)


def chart_key(template: str | Enum | None) -> str:
    """Normalise un référentiel en clé de registre."""
    if isinstance(template, Enum):
        return str(template.value)
    key = str(template or CHART_OF_ACCOUNTS_DEFAULT).strip().upper()
    return key or CHART_OF_ACCOUNTS_DEFAULT


def get_chart(template: str | Enum | None = None) -> list[AccountRow]:
    """Retourne le plan du référentiel demandé (commercial par défaut)."""
    key = chart_key(template)
    try:
        return ACCOUNT_CHARTS[key]
    except KeyError:
        raise ValueError(
            f"Référentiel comptable inconnu : {key!r} "
            f"(attendu : {', '.join(sorted(ACCOUNT_CHARTS))})"
        ) from None


def probe_account(template: str | Enum | None = None) -> str:
    """Compte témoin permettant de vérifier que le plan est chargé."""
    return PROBE_ACCOUNTS[chart_key(template)]


def significant_code(code: str) -> str:
    """Retire les zéros de remplissage — ``411000`` → ``411``.

    Les subdivisions du SYSCOHADA ne prennent jamais le chiffre 0, sauf le
    compte principal à deux chiffres dont le second caractère est 0 (``10``,
    ``20``… ``90``).
    """
    stripped = code.rstrip("0")
    return stripped if len(stripped) >= 2 else code[:2]


def account_type_for(code: str) -> str:
    """Type comptable d'un compte, déduit de son code significatif.

    Le raisonnement porte sur le code significatif : la règle vaut donc pour
    les deux référentiels, quelle que soit leur largeur de remplissage.

    Repères de la classe 1 du SYSCOHADA Révisé — ``10`` capital · ``11``
    réserves · ``12`` report à nouveau · ``13`` résultat · ``14`` subventions
    d'investissement · ``15`` provisions réglementées, tous capitaux propres ;
    ``16`` à ``19`` sont des dettes.
    """
    key = significant_code(code)
    cls = key[0]

    if cls == "1":
        # 109 : apporteurs, capital souscrit non appelé → actif (contre-valeur).
        if key == "109":
            return "asset"
        if key[:2] in ("10", "11", "12", "13", "14", "15"):
            return "equity"
        return "liability"

    if cls in ("2", "3"):
        return "asset"

    if cls == "4":
        # Clients, TVA déductible, CCA, avances au personnel → actifs.
        if key[:2] == "41":
            return "asset"
        if key[:4] in ("4421", "4422", "4423"):
            return "asset"
        if key[:3] in ("481", "488", "421"):
            return "asset"
        # Dépréciations et comptes transitoires → actifs (contre-valeurs).
        if key[:2] in ("49", "47"):
            return "asset"
        return "liability"

    if cls == "5":
        # Crédits de trésorerie = dettes ; dépréciations = contre-actif.
        if key[:2] == "56":
            return "liability"
        return "asset"

    if cls == "6":
        return "expense"
    if cls == "7":
        return "income"
    if cls == "8":
        # Comptes impairs = charges, comptes pairs = produits.
        if key[:2] in ("81", "83", "85", "87", "89"):
            return "expense"
        return "income"
    return "off_balance"


__all__ = [
    "ACCOUNT_CHARTS",
    "CHART_LABELS",
    "DEFAULT_EXPENSE_KEY",
    "EXPENSE_NATURES",
    "PROBE_ACCOUNTS",
    "SEMANTIC_ACCOUNTS",
    "TREASURY_KINDS",
    "AccountRow",
    "account_type_for",
    "chart_key",
    "expense_key",
    "get_chart",
    "probe_account",
    "resolve_account",
    "resolve_accounts",
    "significant_code",
    "treasury_kind",
]
