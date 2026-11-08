"""
Test fonctionnel — configuration initiale de l'entreprise.

Vérifie, sur une base SQLite temporaire et via l'API réelle (ASGITransport) :

1. **état initial** : base vierge → ``needs_admin`` et les six champs
   obligatoires manquants ;
2. **report** : ``/setup/company/skip`` évite de ramener l'écran à chaque
   connexion ;
3. **garde-fou** : un devis reste refusé (409) tant que les informations
   obligatoires manquent — un report ne lève pas l'interdiction ;
4. **progression** : compléter le téléphone seul ne suffit pas, l'adresse, la
   ville et le pays sont exigés de la même façon ;
5. **déblocage** : une fois les six champs renseignés, le devis se crée (201) ;
6. **facultatifs** : information fiscale, logo, CGV et renseignements d'entité
   n'entrent jamais dans la complétude — les documents les accueillent sans
   les exiger.

Usage : ``python backend/test_company_setup.py``
"""
import asyncio
import os
import sys

DB_FILE = "test_company_setup.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_FILE}"
os.environ["BOOTSTRAP_ON_STARTUP"] = "false"

BACKEND = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

_db_path = os.path.join(BACKEND, DB_FILE)
if os.path.exists(_db_path):
    os.remove(_db_path)

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


def labels(payload: dict) -> list[str]:
    """Libellés des champs manquants d'une réponse d'erreur ou d'état."""
    return sorted(item["label"] for item in payload.get("missing_fields", []))


def missing_body(response) -> dict:
    """Détail structuré d'un 409, ou dictionnaire vide."""
    try:
        detail = response.json().get("detail")
    except Exception:  # noqa: BLE001
        return {}
    return detail if isinstance(detail, dict) else {}


async def main() -> int:
    from httpx import ASGITransport, AsyncClient

    from app.core.database import Base, engine
    from app.core.services.seed_service import seed_reference_data

    import app.core.models  # noqa: F401  (enregistre les tables du socle)
    import app.modules.accounting.models  # noqa: F401
    import app.modules.catalogue.models  # noqa: F401
    import app.modules.crm.models  # noqa: F401
    import app.modules.delivery.models  # noqa: F401
    import app.modules.finance.models  # noqa: F401
    import app.modules.invoicing.models  # noqa: F401
    import app.modules.payments.models  # noqa: F401
    import app.modules.purchases.models  # noqa: F401
    import app.modules.sales.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Devises de référence — ce que fait le lifespan au démarrage. Sans elles,
    # `/setup/admin` refuse la devise choisie : c'est exactement la situation
    # d'une installation neuve en production (BOOTSTRAP_ON_STARTUP=false).
    from app.core.data.countries_currencies import CURRENCIES as CATALOGUE

    seeded = await seed_reference_data()
    check("devises de référence disponibles au démarrage", bool(seeded),
          f"(semées : {seeded})")
    check("le catalogue ISO complet est peuplé",
          len(seeded) == len(CATALOGUE),
          f"({len(seeded)} semées pour {len(CATALOGUE)} au catalogue)")
    check("le franc CFA fait partie du catalogue", "XOF" in seeded)
    check("l'euro fait partie du catalogue", "EUR" in seeded)

    # Le catalogue est contrôlé contre CLDR à la génération : les devises
    # remplacées depuis 2019 (lev bulgare, kuna, ancien leone, dollar
    # zimbabwéen…) ne doivent jamais réapparaître dans la base.
    obsolete = {"ANG", "BGN", "HRK", "SLL", "VEF", "ZWL"}
    check(
        "les devises sans territoire ne sont pas semées",
        not obsolete & set(seeded),
        f"(semées à tort : {sorted(obsolete & set(seeded))})",
    )
    check(
        "le florin caribéen et le nouveau leone sont semés",
        {"XCG", "SLE"} <= set(seeded),
    )

    from app.main import app as fastapi_app

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # --- 1. État initial : base vierge ---------------------------------
        status = await client.get("/api/v1/core/setup/status")
        body = status.json()
        check("status initial : 200", status.status_code == 200)
        check("status initial : administrateur requis", body["needs_admin"] is True)
        check("status initial : entreprise à configurer", body["needs_company"] is True)
        check("status initial : profil incomplet", body["company_complete"] is False)
        check(
            "status initial : les six champs obligatoires sont signalés",
            labels(body) == [
                "Adresse", "Devise", "Nom de l'entreprise",
                "N° de téléphone", "Pays", "Ville",
            ],
            f"(obtenu : {labels(body)})",
        )

        # --- 2. Création de l'entreprise et du compte administrateur -------
        created = await client.post(
            "/api/v1/core/setup/admin",
            json={
                "company_name": "Matériaux Test SARL",
                "company_code": "MTS",
                "currency_code": "XOF",
                "email": "admin@mts.test",
                "password": "Admin@12345",
                "first_name": "Awa",
                "last_name": "Traoré",
            },
        )
        check("création du compte administrateur : 201",
              created.status_code == 201,
              f"({created.status_code} {created.text[:200]})")

        # Le endpoint public est verrouillé dès qu'un utilisateur existe.
        replay = await client.post(
            "/api/v1/core/setup/admin",
            json={
                "company_name": "Intrus",
                "company_code": "INT",
                "currency_code": "XOF",
                "email": "intrus@mts.test",
                "password": "Admin@12345",
            },
        )
        check("seconde configuration refusée : 403", replay.status_code == 403,
              f"({replay.status_code})")

        # --- 3. Connexion ---------------------------------------------------
        login = await client.post(
            "/api/v1/core/auth/login",
            json={
                "email": "admin@mts.test",
                "password": "Admin@12345",
                "company_code": "MTS",
            },
        )
        check("connexion : 200", login.status_code == 200,
              f"({login.status_code} {login.text[:200]})")
        token = login.json().get("access_token")
        check("jeton reçu", bool(token))
        auth = {"Authorization": f"Bearer {token}"}

        # --- 4. État après création ----------------------------------------
        status = await client.get("/api/v1/core/setup/status", headers=auth)
        body = status.json()
        check("après création : étape entreprise proposée",
              body["needs_company"] is True)
        check(
            "après création : le nom et la devise sont déjà renseignés",
            labels(body) == ["Adresse", "N° de téléphone", "Pays", "Ville"],
            f"(obtenu : {labels(body)})",
        )

        # --- 5. Report de la configuration ---------------------------------
        skip = await client.post("/api/v1/core/setup/company/skip", headers=auth)
        check("report de la configuration : 200", skip.status_code == 200,
              f"({skip.status_code})")

        status = await client.get("/api/v1/core/setup/status", headers=auth)
        body = status.json()
        check("le report ne ramène plus l'étape à la connexion",
              body["needs_company"] is False)
        check("le report laisse le profil incomplet",
              body["company_complete"] is False)

        # --- 6. Garde-fou : le report ne lève pas l'interdiction -----------
        partner_id = await _create_partner("Client Test")
        quote = await client.post(
            "/api/v1/sales/quotes",
            headers=auth,
            json={"partner_id": partner_id, "lines": []},
        )
        check("devis refusé tant que le profil est incomplet : 409",
              quote.status_code == 409,
              f"({quote.status_code} {quote.text[:200]})")
        detail = missing_body(quote)
        check("le refus est identifiable par l'interface",
              detail.get("code") == "company_incomplete",
              f"(obtenu : {detail.get('code')})")
        check(
            "le refus liste les quatre champs manquants",
            labels(detail) == ["Adresse", "N° de téléphone", "Pays", "Ville"],
            f"(obtenu : {labels(detail)})",
        )

        # --- 7. Configuration partielle : le téléphone seul ne suffit pas ---
        partial = await client.post(
            "/api/v1/core/setup/company",
            headers=auth,
            json={"phone": "+225 07 07 07 07"},
        )
        body = partial.json()
        check("enregistrement partiel : 200", partial.status_code == 200)
        check("le téléphone est enregistré, le profil reste incomplet",
              body["company_complete"] is False)
        check(
            "il ne manque plus que l'adresse, la ville et le pays",
            sorted(body["missing_labels"]) == ["Adresse", "Pays", "Ville"],
            f"(obtenu : {sorted(body['missing_labels'])})",
        )

        quote = await client.post(
            "/api/v1/sales/quotes",
            headers=auth,
            json={"partner_id": partner_id, "lines": []},
        )
        check("devis toujours refusé : 409", quote.status_code == 409,
              f"({quote.status_code})")
        check("le refus ne liste plus que trois champs",
              labels(missing_body(quote)) == ["Adresse", "Pays", "Ville"],
              f"(obtenu : {labels(missing_body(quote))})")

        # --- 8. Complétude obtenue sans aucune information fiscale ---------
        # Le NCC, le RCCM, le greffe, le code importateur et la caisse sociale
        # ne sont jamais fournis : ils sont recommandés, pas exigés.
        complete = await client.post(
            "/api/v1/core/setup/company",
            headers=auth,
            json={
                "street": "Zone industrielle de Yopougon, lot 42",
                "city": "Abidjan",
                "country": "Côte d'Ivoire",
            },
        )
        body = complete.json()
        check("profil déclaré complet : 200", complete.status_code == 200)
        check("profil complet sans aucune information fiscale",
              body["company_complete"] is True,
              f"(manquants : {body.get('missing_fields')})")
        check("plus aucun champ manquant", body["missing_fields"] == [])

        # --- 9. Le document se crée enfin ----------------------------------
        quote = await client.post(
            "/api/v1/sales/quotes",
            headers=auth,
            json={"partner_id": partner_id, "lines": []},
        )
        check("devis accepté une fois le profil complet : 201",
              quote.status_code == 201,
              f"({quote.status_code} {quote.text[:250]})")

        status = await client.get("/api/v1/core/setup/status", headers=auth)
        body = status.json()
        check("status final : plus d'étape à proposer",
              body["needs_company"] is False)
        check("status final : profil complet", body["company_complete"] is True)

        # --- 10. Renseignements d'entité et pièces facultatives ------------
        entity = await client.post(
            "/api/v1/core/setup/company",
            headers=auth,
            json={
                "activity_code": "12345",
                "closing_date": "31/12",
                "fiscal_year_months": 12,
                "greffe": "Tribunal de commerce d'Abidjan",
                "importer_code": "CI-IMP-0042",
                "social_security_code": "CNPS-778899",
                "ncc": "1234567A",
                "rccm": "CI-ABJ-2026-B-00042",
                "share_capital": "1 000 000",
                "logo": "data:image/png;base64,iVBORw0KGgo=",
                "cgv": "Les marchandises vendues ne sont ni reprises ni échangées.",
            },
        )
        body = entity.json()
        check("renseignements d'entité enregistrés : 200",
              entity.status_code == 200, f"({entity.status_code})")
        check("le profil reste complet", body["company_complete"] is True)
        check("aucun champ manquant", body["missing_fields"] == [])

        stored = await _stored_company()
        check("code d'activité principale persisté",
              stored["activity_code"] == "12345",
              f"(obtenu : {stored['activity_code']!r})")
        check("durée de l'exercice persistée",
              stored["fiscal_year_months"] == 12,
              f"(obtenu : {stored['fiscal_year_months']!r})")
        check("date d'arrêté des comptes persistée",
              stored["closing_date"] == "31/12",
              f"(obtenu : {stored['closing_date']!r})")
        check("greffe persisté",
              stored["greffe"] == "Tribunal de commerce d'Abidjan")
        check("code importateur persisté", stored["importer_code"] == "CI-IMP-0042")
        check("caisse sociale persistée",
              stored["social_security_code"] == "CNPS-778899")
        check("NCC persisté", stored["ncc"] == "1234567A")
        check("RCCM persisté", stored["rccm"] == "CI-ABJ-2026-B-00042")
        check(
            "les renseignements d'entité n'ont pas écrasé l'adresse",
            stored["address"].get("street") == "Zone industrielle de Yopougon, lot 42"
            and stored["address"].get("city") == "Abidjan"
            and stored["address"].get("country") == "Côte d'Ivoire",
            f"(obtenu : {stored['address']})",
        )
        check("le téléphone saisi à l'étape précédente est conservé",
              stored["phone"] == "+225 07 07 07 07",
              f"(obtenu : {stored['phone']!r})")
        check("le logo est enregistré", bool(stored["logo"]))
        check("les CGV sont enregistrées",
              "reprises ni échangées" in await _stored_cgv())

    await engine.dispose()
    if os.path.exists(_db_path):
        os.remove(_db_path)
    return 0


async def _create_partner(name: str) -> int:
    """Crée un client minimal et renvoie son identifiant.

    Un devis exige un partenaire : le garde-fou du profil s'exerce avant toute
    validation métier, il faut donc un client valide pour qu'un refus ne puisse
    venir que du profil (409) et non d'un client manquant (400).
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.models.company import Company
    from app.modules.crm.models.partner import Partner

    async with AsyncSessionLocal() as session:
        company = (await session.execute(
            select(Company).order_by(Company.id).limit(1)
        )).scalars().first()
        partner = Partner(
            name=name, role="client", company_id=company.id, is_active=True,
        )
        session.add(partner)
        await session.commit()
        await session.refresh(partner)
        return partner.id


async def _stored_company() -> dict:
    """Relit l'entreprise en base (hors requête HTTP).

    Renvoie un dictionnaire plutôt que l'instance ORM : la session est fermée
    au retour et un objet détaché exposerait des attributs non chargés.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.models.company import Company

    async with AsyncSessionLocal() as session:
        company = (await session.execute(
            select(Company).order_by(Company.id).limit(1)
        )).scalars().first()
        return {
            "name": company.name,
            "phone": company.phone,
            "currency_code": company.currency_code,
            "address": dict(company.address or {}),
            "ncc": company.ncc,
            "rccm": company.rccm,
            "share_capital": company.share_capital,
            "greffe": company.greffe,
            "importer_code": company.importer_code,
            "social_security_code": company.social_security_code,
            "activity_code": company.activity_code,
            "closing_date": company.closing_date,
            "fiscal_year_months": company.fiscal_year_months,
            "logo": company.logo,
        }


async def _stored_cgv() -> str:
    """Relit le texte des CGV enregistré dans les paramètres."""
    from app.core.database import AsyncSessionLocal
    from app.core.services.setting_service import SettingService

    async with AsyncSessionLocal() as session:
        return await SettingService(session).get("cgv_content", "") or ""


if __name__ == "__main__":
    asyncio.run(main())
    print()
    if FAILURES:
        print(f"{len(FAILURES)} échec(s) sur {CHECKS} vérifications :")
        for failure in FAILURES:
            print(f"  - {failure}")
        sys.exit(1)
    print(f"TOUTES LES VÉRIFICATIONS SONT PASSÉES ({CHECKS} contrôles)")
    sys.exit(0)
