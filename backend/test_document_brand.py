"""
Test fonctionnel — entête des documents : logo et miniature de substitution.

Vérifie, en **rendant réellement** le fragment Jinja des gabarits :

1. **initiales** : un mot → deux lettres, plusieurs mots → une par mot, nom
   vide ou entreprise absente → repli sûr ;
2. **avec logo** : l'image de l'entreprise est insérée et la miniature non ;
3. **sans logo** : la miniature prend le relais et aucune image n'est insérée ;
4. les six gabarits (cinq A4 + ticket de caisse) portent bien le repli.

Usage : ``python backend/test_document_brand.py``
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_document_brand.db"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

import logging  # noqa: E402

logging.disable(logging.INFO)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    """Vérifie une assertion et journalise le résultat."""
    global CHECKS
    CHECKS += 1
    if condition:
        print(f"  OK    {label}")
    else:
        FAILURES.append(f"{label} {detail}".strip())
        print(f"  ECHEC {label} {detail}")


class FakeCompany:
    """Entreprise minimale suffisante pour le fragment d'entête."""

    def __init__(self, name: str, logo: str | None = None) -> None:
        self.name = name
        self.logo = logo


#: Fragment d'entête, repris à l'identique des gabarits A4.
BRAND_SNIPPET = (
    '{% if company and company.logo %}<img src="{{ company.logo }}" alt=""/>'
    '{% elif company %}<span class="mark">{{ company_monogram(company) }}</span>'
    "{% endif %}"
)

#: Gabarits qui doivent porter le repli.
DOC_TEMPLATES = (
    "invoice.html",
    "quote.html",
    "delivery.html",
    "purchase_order.html",
    "receipt.html",
    "pos_ticket.html",
)


def main() -> int:
    from app.core.documents.engine import DocumentEngine, _company_monogram

    # --- 1. Initiales ---------------------------------------------------
    check("un mot → deux lettres",
          _company_monogram(FakeCompany("Matériaux")) == "MA",
          f"(obtenu : {_company_monogram(FakeCompany('Matériaux'))})")
    check("deux mots → une lettre chacun",
          _company_monogram(FakeCompany("Groupe AKA")) == "GA")
    check("trois mots → les deux premiers",
          _company_monogram(FakeCompany("Société de Matériaux")) == "SD")
    check("espaces seuls → repli sûr",
          _company_monogram(FakeCompany("   ")) == "?")
    check("entreprise absente → repli sûr", _company_monogram(None) == "?")

    # --- 2. Rendu du fragment, avec et sans logo ------------------------
    engine = DocumentEngine()
    brand = engine.jinja_env.from_string(BRAND_SNIPPET)

    with_logo = brand.render(
        company=FakeCompany("Groupe AKA", logo="data:image/png;base64,AAA")
    )
    check("avec logo : l'image est insérée", "<img" in with_logo,
          f"(obtenu : {with_logo})")
    check("avec logo : la miniature est absente", 'class="mark"' not in with_logo)
    check("avec logo : l'image porte les données",
          "data:image/png;base64,AAA" in with_logo)

    without_logo = brand.render(company=FakeCompany("Groupe AKA"))
    check("sans logo : la miniature s'affiche", ">GA<" in without_logo,
          f"(obtenu : {without_logo})")
    check("sans logo : aucune image n'est insérée", "<img" not in without_logo)

    empty = brand.render(company=None)
    check("entreprise absente : entête vide, sans erreur", empty.strip() == "",
          f"(obtenu : {empty!r})")

    # --- 3. Les gabarits portent bien le repli --------------------------
    for name in DOC_TEMPLATES:
        path = os.path.join(engine.template_dir, name)
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        check(f"{name} : miniature câblée",
              "company_monogram(company)" in source,
              "(repli absent du gabarit)")

    return 0


if __name__ == "__main__":
    main()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} échec(s) sur {CHECKS} vérifications :")
        for failure in FAILURES:
            print(f"  - {failure}")
        sys.exit(1)
    print(f"TOUTES LES VÉRIFICATIONS SONT PASSÉES ({CHECKS} contrôles)")
    sys.exit(0)
