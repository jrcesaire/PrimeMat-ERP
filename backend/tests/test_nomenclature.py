"""Non-régressions : nomenclature tolérante et synchronisation des modules."""

from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import database
from app.core.api.settings import SettingUpsert, list_sequences
from app.core.database import Base
from app.core.models.company import Company
from app.core.models.module_info import ModuleInfo
from app.core.models.sequence import Sequence
from app.core.models.setting import Setting
from app.core.modules import AVAILABLE_MODULES, ModuleRegistry
from app.core.modules import settings as module_settings
from app.core.services.setting_service import _CACHE, SettingService, as_mapping


@pytest.fixture(autouse=True)
def clear_setting_cache():
    """Isole le cache module-level entre les scénarios."""
    _CACHE.clear()
    yield
    _CACHE.clear()


def test_as_mapping_decode_objet_et_json_doublement_encode() -> None:
    expected = {"quote": {"prefix": "DEV", "padding": 6}}
    assert as_mapping(expected) == expected
    assert as_mapping(json.dumps(expected)) == expected
    assert as_mapping(json.dumps(json.dumps(expected))) == expected


@pytest.mark.parametrize(
    "value",
    [None, 42, [], "{invalide", "texte", {"0": "{", "1": '"'}],
)
def test_as_mapping_ignore_les_valeurs_inexploitables(value: object) -> None:
    assert as_mapping(value) == {}


def test_setting_upsert_accepte_un_objet_json_natif() -> None:
    body = SettingUpsert(
        key="doc_nomenclature",
        value={"quote": {"prefix": "DEV"}},
        type="json",
    )
    assert body.value == {"quote": {"prefix": "DEV"}}


async def _check_nomenclature(raw: str, expected_prefix: str) -> None:
    """Exerce la lecture et l'endpoint contre une vraie session SQLAlchemy."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        tables = [Company.__table__, Setting.__table__, Sequence.__table__]
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                Setting(
                    key="doc_nomenclature",
                    value=raw,
                    type="json",
                    is_public=True,
                    company_id=None,
                )
            )
            session.add(
                Sequence(
                    company_id=1,
                    model="quote",
                    name="Devis",
                    prefix="DEV",
                    number_padding=6,
                    number_increment=1,
                    last_number=52,
                    reset="never",
                    is_active=True,
                    date_ranges={"last_period": str(date.today().year)},
                )
            )
            await session.commit()

            service = SettingService(session)
            normalized = await service.get("doc_nomenclature")
            assert isinstance(normalized, dict)
            assert not normalized or not all(str(key).isdigit() for key in normalized)

            payload = await list_sequences(session, None)
            sequences = {row["model"]: row for row in payload["sequences"]}
            assert "employee" in sequences
            assert sequences["quote"]["last_number"] == 52
            assert sequences["quote"]["next_reference"] == (f"{expected_prefix}-000053")

            # L'écriture d'un objet ne produit qu'un seul encodage JSON.
            new_config = {"quote": {"prefix": "NEW", "padding": 6}}
            await service.set("doc_nomenclature", new_config, "json", True)
            stored = (
                await session.execute(select(Setting).where(Setting.key == "doc_nomenclature"))
            ).scalar_one()
            assert json.loads(stored.value) == new_config
            assert await service.get("doc_nomenclature") == new_config
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("raw", "expected_prefix"),
    [
        (json.dumps(json.dumps({"0": "{", "1": '"'})), "DEV"),
        ("{json-cassé", "DEV"),
        (
            json.dumps(json.dumps({"quote": {"prefix": "PERSO", "padding": 6}})),
            "PERSO",
        ),
    ],
    ids=["map-corrompue", "json-invalide", "double-encodage-personnalise"],
)
def test_sequences_ne_echouent_pas_sur_nomenclature_stockee(raw: str, expected_prefix: str) -> None:
    asyncio.run(_check_nomenclature(raw, expected_prefix))


def test_registre_synchronise_payroll_sans_reactiver_un_module_desactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(ModuleInfo.__table__.create)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                session.add(
                    ModuleInfo(
                        name="sales",
                        version="0.1.0",
                        status="installed",
                        is_active=False,
                    )
                )
                await session.commit()

            monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
            monkeypatch.setattr(module_settings, "default_modules", ["core", "payroll"])
            registry = ModuleRegistry()
            await registry.load_modules()

            assert set(registry.modules) == set(AVAILABLE_MODULES) | {"core"}
            assert registry.is_module_active("payroll")
            assert registry.modules["payroll"].status == "active"
            assert not registry.is_module_active("sales")
            assert registry.modules["sales"].status == "installed"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
