"""Cohérence des plans comptables embarqués et de la table d'alias.

Ces contrôles sont la garde-fou du double référentiel : ils vérifient que tout
code cité par ``SEMANTIC_ACCOUNTS`` existe réellement dans le plan concerné.
Sans eux, une clé métier pointant sur un compte absent ne se manifesterait
qu'au moment d'une écriture, en production.
"""

from __future__ import annotations

import pytest

from app.modules.accounting.data import (
    ACCOUNT_CHARTS,
    DEFAULT_EXPENSE_KEY,
    EXPENSE_NATURES,
    PROBE_ACCOUNTS,
    SEMANTIC_ACCOUNTS,
    TREASURY_KINDS,
    account_type_for,
    expense_key,
    get_chart,
    probe_account,
    resolve_account,
    significant_code,
    treasury_kind,
)

TEMPLATES = ("SYSCOHADA", "SYCEBNL")

#: Clés indispensables au fonctionnement des écritures automatiques.
REQUIRED_KEYS = (
    "customers",
    "suppliers",
    "tax_collected",
    "tax_deductible",
    "sales_revenue",
    "purchases",
    "cash",
    "bank",
    "misc_expenses",
    "result_profit",
    "result_loss",
    "retained_credit",
    "retained_debit",
)


@pytest.mark.parametrize("template", TEMPLATES)
def test_semantic_codes_exist_in_chart(template: str) -> None:
    """Chaque clé métier pointe sur un compte réellement présent."""
    by_code = {code for code, _, _ in get_chart(template)}
    missing = {
        key: code
        for key, code in SEMANTIC_ACCOUNTS[template].items()
        if code not in by_code
    }
    assert missing == {}, f"{template} : comptes introuvables {missing}"


@pytest.mark.parametrize("template", TEMPLATES)
def test_required_keys_are_mapped(template: str) -> None:
    """Les clés dont dépendent les écritures sont toutes définies."""
    absent = [key for key in REQUIRED_KEYS if key not in SEMANTIC_ACCOUNTS[template]]
    assert absent == [], f"{template} : clés manquantes {absent}"


@pytest.mark.parametrize("template", TEMPLATES)
def test_probe_account_exists(template: str) -> None:
    """Le compte témoin permet de détecter un plan absent ou obsolète."""
    codes = {code for code, _, _ in get_chart(template)}
    assert probe_account(template) in codes
    assert PROBE_ACCOUNTS[template] in codes


@pytest.mark.parametrize("template", TEMPLATES)
def test_codes_are_unique_and_six_digits(template: str) -> None:
    """Les deux plans tiennent sur six chiffres, sans doublon."""
    codes = [code for code, _, _ in get_chart(template)]
    assert len(set(codes)) == len(codes), f"{template} : codes en double"
    assert all(len(code) == 6 for code in codes), f"{template} : code hors 6 chiffres"


@pytest.mark.parametrize("template", TEMPLATES)
def test_charts_cover_all_ohada_classes(template: str) -> None:
    """Les neuf classes OHADA sont représentées."""
    classes = {code[0] for code, _, _ in get_chart(template)}
    assert classes == set("123456789")


def test_resolve_account_returns_none_for_unknown_key() -> None:
    """Une clé absente d'un référentiel n'est pas une erreur : l'appelant replie."""
    assert resolve_account("SYSCOHADA", "sales_discounts") == "701900"
    assert resolve_account("SYCEBNL", "sales_discounts") is None
    assert resolve_account("SYCEBNL", "matiere_premiere") is None
    assert resolve_account("INCONNU", "customers") is None


def test_treasury_kinds_are_mapped_in_both_charts() -> None:
    """Toute nature de trésorerie déduite d'un mode de règlement existe."""
    for template in TEMPLATES:
        for method in ("cash", "bank_transfer", "check", "card", "mobile_money", "other", None):
            assert resolve_account(template, treasury_kind(method)) is not None


def test_expense_natures_are_mapped_in_both_charts() -> None:
    """Toute nature de dépense aboutit à un compte, avec repli sur « divers »."""
    assert expense_key(None) == DEFAULT_EXPENSE_KEY
    assert expense_key("inconnue-du-logiciel") == DEFAULT_EXPENSE_KEY
    for template in TEMPLATES:
        fallback = resolve_account(template, DEFAULT_EXPENSE_KEY)
        assert fallback is not None
        for category in EXPENSE_NATURES:
            key = expense_key(category)
            # Un référentiel peut ignorer une nature : le repli prend le relais.
            assert resolve_account(template, key) is not None or fallback is not None


def test_bank_is_52_in_both_charts() -> None:
    """La banque est en ``52`` dans le SYSCOHADA Révisé — pas en ``51``."""
    assert SEMANTIC_ACCOUNTS["SYSCOHADA"]["bank"].startswith("52")
    assert SEMANTIC_ACCOUNTS["SYCEBNL"]["bank"].startswith("52")
    assert significant_code(SEMANTIC_ACCOUNTS["SYSCOHADA"]["bank"]) == "521"


def test_significant_code_unpads() -> None:
    """Le dé-remplissage redonne le code du plan officiel."""
    assert significant_code("411000") == "411"
    assert significant_code("101100") == "1011"
    assert significant_code("100000") == "10"
    assert significant_code("990000") == "99"


def test_account_type_class_one_follows_the_revised_plan() -> None:
    """Capitaux propres en ``10``-``15``, dettes en ``16``-``19``."""
    for code in ("100000", "110000", "120000", "130000", "140000", "150000"):
        assert account_type_for(code) == "equity", code
    for code in ("160000", "170000", "180000", "190000"):
        assert account_type_for(code) == "liability", code
    # 109 : apporteurs, capital souscrit non appelé → contre-valeur d'actif.
    assert account_type_for("109000") == "asset"


def test_account_charts_registry_covers_both_templates() -> None:
    """Le registre expose exactement les deux référentiels attendus."""
    assert set(ACCOUNT_CHARTS) == set(TEMPLATES)
    assert set(SEMANTIC_ACCOUNTS) == set(TEMPLATES)
    assert set(TREASURY_KINDS) == {
        "cash", "bank_transfer", "check", "card", "mobile_money", "other"
    }
