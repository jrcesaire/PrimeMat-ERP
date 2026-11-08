"""
Test fonctionnel — immobilisations et amortissements (Lot C de la Phase 2).

Vérifie, sur une base SQLite temporaire :

1. **linéaire annuel** : dotation constante, cumul exact jusqu'à la valeur
   résiduelle ;
2. **arrondi** : la dernière échéance absorbe l'écart de centimes ;
3. **linéaire mensuel** : 12 échéances par an ;
4. **dégressif SYSCOHADA** : taux accéléré puis basculement en linéaire sur la
   durée restante, plan soldé exactement ;
5. **comptabilisation** ``D 681 / C 28x`` : écritures équilibrées, soldes
   corrects, **idempotence** (rejouer ne duplique pas) ;
6. **validations** : valeur résiduelle incohérente, dégressif mensuel, code
   dupliqué, suppression après comptabilisation, recalcul du plan.

Usage : ``python backend/test_depreciation.py``
"""
import asyncio
import os
import sys
from datetime import date

DB_FILE = "test_depreciation.db"
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
        print(f"  OK   {label}")
    else:
        FAILURES.append(f"{label} {detail}".strip())
        print(f"  ECHEC {label} {detail}")


def close_to(value: float, expected: float, tol: float = 0.01) -> bool:
    return abs(float(value) - float(expected)) < tol


async def main() -> int:
    from app.core.database import AsyncSessionLocal, Base, engine

    import app.core.models  # noqa: F401
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

    from sqlalchemy import select

    from app.core.models.company import Company
    from app.core.services.seed_service import bootstrap_defaults
    from app.modules.accounting.schemas.fixed_asset import (
        FixedAssetCreate,
        FixedAssetUpdate,
    )
    from app.modules.accounting.schemas.ohada import FiscalYearCreate
    from app.modules.accounting.services.depreciation_service import (
        DepreciationService,
        declining_coefficient,
        derived_depreciation_account,
    )
    from app.modules.accounting.services.journal_service import LedgerService
    from app.modules.accounting.services.ohada import OHADAService

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await bootstrap_defaults(
            session,
            company_name="Test Amortissement SARL",
            company_code="TAM",
            company_currency="XOF",
            agency_name="Siège",
            agency_code="S01",
            admin_email="amort@test.ci",
            admin_password="MotDePasse@123",
        )
        company = (
            await session.execute(select(Company).where(Company.code == "TAM"))
        ).scalar_one()
        company_id = company.id

        service = DepreciationService(session)
        ledger = LedgerService(session)
        ohada = OHADAService(session)
        await ohada.create_fiscal_year(
            FiscalYearCreate(
                name="Exercice 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            company_id,
        )

        def payload(code: str, **overrides):
            base = dict(
                code=code,
                name=f"Immobilisation {code}",
                category="equipment",
                asset_account="245000",
                acquisition_date=date(2026, 1, 1),
                acquisition_cost=1_000_000,
                useful_life_years=5,
                method="linear",
                periodicity="annual",
            )
            base.update(overrides)
            return FixedAssetCreate(**base)

        async def balances_map() -> dict[str, float]:
            rows = await ledger.account_balances(company_id)
            return {b["account_code"]: b["balance"] for b in rows}

        # --- 0. Dérivations ---
        print("[0] Comptes dérivés et coefficients dégressifs")
        check(
            "compte d'amortissement déduit (245 → 284)",
            derived_depreciation_account("245000") == "284000",
        )
        check(
            "compte d'amortissement déduit (213 → 281)",
            derived_depreciation_account("213000") == "281000",
        )
        check("coefficient dégressif 4 ans → 1,5", declining_coefficient(4) == 1.5)
        check("coefficient dégressif 5 ans → 2,0", declining_coefficient(5) == 2.0)
        check("coefficient dégressif 8 ans → 2,5", declining_coefficient(8) == 2.5)

        # --- 1. Linéaire annuel ---
        print("\n[1] Linéaire annuel (1 200 000 sur 5 ans)")
        linear = await service.create_asset(
            company_id,
            payload("IMM-LIN", acquisition_cost=1_200_000, useful_life_years=5),
        )
        check("5 échéances générées", len(linear.depreciations) == 5)
        check(
            "dotation annuelle = 240 000",
            close_to(linear.depreciations[0].amount, 240_000),
            f"({linear.depreciations[0].amount})",
        )
        check(
            "compte d'amortissement dérivé = 284",
            linear.depreciation_account == "284000",
        )
        check(
            "cumul final = 1 200 000",
            close_to(linear.depreciations[-1].accumulated, 1_200_000),
        )
        check("VNC finale = 0", close_to(linear.depreciations[-1].net_value, 0))
        check(
            "1re échéance au 31/12/2026",
            linear.depreciations[0].period_date == date(2026, 12, 31),
            f"({linear.depreciations[0].period_date})",
        )
        # Identifiant figé : les ``rollback()`` de la section 6 expirent
        # l'instance ORM, et relire ``linear.id`` déclencherait une requête.
        linear_id = linear.id

        # --- 2. Valeur résiduelle et arrondi ---
        print("\n[2] Valeur résiduelle et arrondi des centimes")
        residual = await service.create_asset(
            company_id,
            payload(
                "IMM-RES",
                acquisition_cost=1_000_000,
                residual_value=100_000,
                useful_life_years=3,
            ),
        )
        check(
            "base amortissable = 900 000",
            close_to(residual.depreciable_base, 900_000),
        )
        check(
            "dotation annuelle = 300 000",
            close_to(residual.depreciations[0].amount, 300_000),
        )
        check(
            "VNC finale = valeur résiduelle (100 000)",
            close_to(residual.depreciations[-1].net_value, 100_000),
            f"({residual.depreciations[-1].net_value})",
        )

        rounding = await service.create_asset(
            company_id,
            payload("IMM-ARR", acquisition_cost=1_000_000, useful_life_years=3),
        )
        amounts = [float(d.amount) for d in rounding.depreciations]
        check(
            "arrondi : 333 333,33 / 333 333,33 / 333 333,34",
            [round(a, 2) for a in amounts] == [333_333.33, 333_333.33, 333_333.34],
            f"({amounts})",
        )
        check(
            "arrondi : cumul exact = 1 000 000",
            close_to(sum(amounts), 1_000_000),
            f"({sum(amounts)})",
        )

        # --- 3. Linéaire mensuel ---
        print("\n[3] Linéaire mensuel (120 000 sur 1 an)")
        monthly = await service.create_asset(
            company_id,
            payload(
                "IMM-MEN",
                acquisition_cost=120_000,
                useful_life_years=1,
                periodicity="monthly",
            ),
        )
        check("12 échéances", len(monthly.depreciations) == 12)
        check(
            "dotation mensuelle = 10 000",
            close_to(monthly.depreciations[0].amount, 10_000),
        )
        check(
            "cumul final = 120 000",
            close_to(monthly.depreciations[-1].accumulated, 120_000),
        )

        # --- 4. Dégressif SYSCOHADA ---
        print("\n[4] Dégressif SYSCOHADA (1 000 000 sur 5 ans, coefficient 2)")
        declining = await service.create_asset(
            company_id,
            payload(
                "IMM-DEG",
                acquisition_cost=1_000_000,
                useful_life_years=5,
                method="declining",
            ),
        )
        declining_amounts = [
            round(float(d.amount), 2) for d in declining.depreciations
        ]
        # an1 : 40 % × 1 000 000 = 400 000 ; an2 : 40 % × 600 000 = 240 000 ;
        # an3 : 40 % × 360 000 = 144 000 ; le taux linéaire résiduel (1/2 = 50 %)
        # dépasse alors 40 % → basculement : 216 000 / 2 = 108 000 par an.
        check(
            "dotations : 400 000 / 240 000 / 144 000 / 108 000 / 108 000",
            declining_amounts == [400_000, 240_000, 144_000, 108_000, 108_000],
            f"({declining_amounts})",
        )
        check(
            "dégressif : cumul final = 1 000 000",
            close_to(declining.depreciations[-1].accumulated, 1_000_000),
        )
        check(
            "dégressif : VNC finale = 0",
            close_to(declining.depreciations[-1].net_value, 0),
        )
        check(
            "dégressif : 1re dotation supérieure au linéaire (accélération)",
            float(declining.depreciations[0].amount) > 1_000_000 / 5,
        )

        # --- 5. Comptabilisation des dotations ---
        print("\n[5] Comptabilisation D 681 / C 284")
        run = await service.post_due(linear, as_of=date(2026, 12, 31))
        check(
            "1 dotation comptabilisée (échéance 2026)",
            run.posted == 1,
            f"({run.posted})",
        )
        check("montant comptabilisé = 240 000", close_to(run.total_amount, 240_000))
        check("écriture générée", len(run.references) == 1)

        balances = await balances_map()
        check(
            "compte 681 = 240 000 (dotation)",
            close_to(balances.get("681000", 0), 240_000),
            f"({balances.get('681000')})",
        )
        check(
            "compte 284 = -240 000 (amortissement cumulé)",
            close_to(balances.get("284000", 0), -240_000),
            f"({balances.get('284')})",
        )

        linear = await service.get_asset(company_id, linear.id)
        again = await service.post_due(linear, as_of=date(2026, 12, 31))
        check(
            "idempotence : aucune nouvelle écriture au rejeu",
            again.posted == 0,
            f"({again.posted})",
        )
        balances = await balances_map()
        check(
            "solde 681 inchangé après rejeu",
            close_to(balances.get("681000", 0), 240_000),
        )

        linear = await service.get_asset(company_id, linear.id)
        rest = await service.post_due(linear, as_of=date(2040, 12, 31))
        check(
            "4 dotations restantes comptabilisées",
            rest.posted == 4,
            f"({rest.posted})",
        )
        check(
            "montant des 4 échéances = 960 000",
            close_to(rest.total_amount, 960_000),
            f"({rest.total_amount})",
        )
        balances = await balances_map()
        check("solde 681 = 1 200 000", close_to(balances.get("681000", 0), 1_200_000))
        check("solde 284 = -1 200 000", close_to(balances.get("284000", 0), -1_200_000))
        check(
            "somme des soldes de tous les comptes = 0",
            close_to(sum(balances.values()), 0),
            f"({sum(balances.values())})",
        )

        linear = await service.get_asset(company_id, linear.id)
        synth = await service.summary(linear)
        check(
            "synthèse : 5 échéances dont 5 comptabilisées",
            synth.periods_count == 5 and synth.posted_count == 5,
            f"({synth.posted_count}/{synth.periods_count})",
        )
        check("synthèse : VNC = 0", close_to(synth.net_value, 0))
        check(
            "synthèse : reste à comptabiliser = 0",
            close_to(synth.remaining_to_post, 0),
        )

        # --- 6. Validations et garde-fous ---
        print("\n[6] Validations et garde-fous")

        async def expect_error(label: str, coro, needle: str) -> None:
            """Exécute ``coro`` en attendant un ValueError contenant ``needle``."""
            try:
                await coro
                check(label, False, "(aucune erreur levée)")
            except ValueError as exc:
                check(label, needle in str(exc), f"({exc})")
                await session.rollback()

        await expect_error(
            "valeur résiduelle ≥ valeur d'acquisition refusée",
            service.create_asset(
                company_id,
                payload("IMM-BAD", acquisition_cost=100_000, residual_value=100_000),
            ),
            "résiduelle",
        )
        await expect_error(
            "dégressif + périodicité mensuelle refusé",
            service.create_asset(
                company_id, payload("IMM-BAD2", method="declining", periodicity="monthly")
            ),
            "annuelle",
        )
        await expect_error(
            "code dupliqué refusé",
            service.create_asset(company_id, payload("IMM-LIN")),
            "existe déjà",
        )
        await expect_error(
            "compte inexistant dans le plan refusé",
            service.create_asset(company_id, payload("IMM-BAD3", asset_account="9999")),
            "plan comptable",
        )
        await expect_error(
            "suppression refusée après comptabilisation",
            service.delete_asset(company_id, linear_id),
            "comptabilisée",
        )

        draft = await service.create_asset(
            company_id,
            payload("IMM-MAJ", acquisition_cost=600_000, useful_life_years=3),
        )
        check(
            "plan initial : 3 échéances de 200 000",
            len(draft.depreciations) == 3
            and close_to(draft.depreciations[0].amount, 200_000),
            f"({len(draft.depreciations)} × {draft.depreciations[0].amount})",
        )
        updated = await service.update_asset(
            company_id, draft.id, FixedAssetUpdate(useful_life_years=6)
        )
        check(
            "plan recalculé après changement de durée : 6 échéances de 100 000",
            len(updated.depreciations) == 6
            and close_to(updated.depreciations[0].amount, 100_000),
            f"({len(updated.depreciations)} × {updated.depreciations[0].amount})",
        )

        await service.delete_asset(company_id, draft.id)
        remaining = {a.code for a in await service.list_assets(company_id)}
        check("suppression possible sans dotation comptabilisée", "IMM-MAJ" not in remaining)

        # Filtre par statut
        active = await service.list_assets(company_id, status="active")
        check("filtre par statut : toutes actives", len(active) == len(remaining))

    await engine.dispose()
    if os.path.exists(_db_path):
        os.remove(_db_path)

    print("\n" + "=" * 64)
    if FAILURES:
        print(f"{len(FAILURES)} ÉCHEC(S) sur {CHECKS} vérifications :")
        for failure in FAILURES:
            print("  -", failure)
        return 1
    print(f"TOUTES LES VÉRIFICATIONS SONT PASSÉES ({CHECKS}/{CHECKS})")
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
