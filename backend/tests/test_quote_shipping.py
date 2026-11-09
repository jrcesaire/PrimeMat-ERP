"""Non-régressions — frais d'expédition du devis.

L'expédition est un forfait saisi sur le devis. Elle s'ajoute **après** la
remise globale (elle n'est donc jamais remisée) et n'entre pas dans l'assiette
de TVA ; elle apparaît juste avant le total sur le document. Ce test verrouille
la formule de ``QuoteService._recompute_totals``.
"""

from __future__ import annotations

from app.modules.sales.models.quote import Quote, QuoteLine
from app.modules.sales.services.quote_service import QuoteService


def _quote(*, subtotal: float) -> Quote:
    quote = Quote(partner_id=1, company_id=1)
    quote.lines = [
        QuoteLine(
            quantity=1,
            unit_price=subtotal,
            discount_percent=0,
            subtotal=subtotal,
        )
    ]
    return quote


def test_expedition_ajoutee_apres_la_remise_globale() -> None:
    service = QuoteService(session=None)  # type: ignore[arg-type]
    quote = _quote(subtotal=200)

    service._recompute_totals(
        quote, tax_percent=10, global_discount=50, shipping=5000
    )

    assert float(quote.amount_untaxed) == 200
    assert float(quote.discount_amount) == 50
    # TVA sur (HT − remise) uniquement : l'expédition n'est pas taxée.
    assert float(quote.tax_amount) == 15
    assert float(quote.shipping_amount) == 5000
    # 200 − 50 + 15 + 5000 — la remise ne mord pas sur l'expédition.
    assert float(quote.amount_total) == 5165


def test_expedition_survit_a_une_remise_superieure_au_sous_total() -> None:
    service = QuoteService(session=None)  # type: ignore[arg-type]
    quote = _quote(subtotal=100)

    service._recompute_totals(
        quote, tax_percent=20, global_discount=500, shipping=7500
    )

    assert float(quote.amount_total) == 7500


def test_expedition_conservee_quand_seuls_la_remise_ou_la_tva_changent() -> None:
    service = QuoteService(session=None)  # type: ignore[arg-type]
    quote = _quote(subtotal=1000)

    service._recompute_totals(quote, tax_percent=0, global_discount=0, shipping=2500)
    # Aucun montant d'expédition transmis → la valeur portée par le devis reste.
    service._recompute_totals(quote, tax_percent=10, global_discount=100)

    assert float(quote.shipping_amount) == 2500
    assert float(quote.amount_total) == 1000 - 100 + 90 + 2500
