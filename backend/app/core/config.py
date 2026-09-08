"""
Configuration centrale de l'application.

Utilise Pydantic Settings pour charger la configuration depuis les variables
d'environnement.  Toutes les sections (Core, modules métier, storage, backup, etc.)
sont centralisées ici.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Capturé par le validator ``environment`` (validé avant ``secret_key``)
settings_env: str = "development"


class Settings(BaseSettings):
    """Paramètres globaux de l'ERP."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    app_name: str = "ERP Matériaux de Construction"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = True
    # Origines autorisées pour le CORS (frontend, site web...). `*` interdit
    # avec credentials — toujours lister explicitement en production.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # ------------------------------------------------------------------ #
    # Base de données
    # ------------------------------------------------------------------ #
    database_url: str = Field(
        default="postgresql+psycopg://erp_user:erp_pass@localhost:5432/erp_db"
    )

    # ------------------------------------------------------------------ #
    # Redis / Celery
    # ------------------------------------------------------------------ #
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ------------------------------------------------------------------ #
    # Auth / JWT
    # ------------------------------------------------------------------ #
    secret_key: str = Field(default="change-this-in-production-use-openssl-rand")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h
    refresh_token_expire_days: int = 30
    jwt_issuer: str = "erp-materiaux"

    # ------------------------------------------------------------------ #
    # Bootstrap — premier compte administrateur (créé si la base est vide)
    # ------------------------------------------------------------------ #
    first_company_name: str = "Entreprise ABC"
    first_company_code: str = "ABC"
    first_company_currency: str = "XOF"
    first_agency_name: str = "Agence principale"
    first_agency_code: str = "AG-01"
    first_admin_email: str = "admin@abc.com"
    first_admin_password: str = "Admin@12345"
    first_admin_first_name: str = "Admin"
    first_admin_last_name: str = "Système"
    bootstrap_on_startup: bool = True

    # ------------------------------------------------------------------ #
    # Storage (S3 / MinIO)
    # ------------------------------------------------------------------ #
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str = "erp-files"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = True

    # ------------------------------------------------------------------ #
    # Sentry
    # ------------------------------------------------------------------ #
    sentry_dsn: str | None = None
    prometheus_enabled: bool = True

    # ------------------------------------------------------------------ #
    # Modules activés par défaut (peuvent être modifiés via la DB)
    # ------------------------------------------------------------------ #
    default_modules: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "core",
            "catalogue",
            "crm",
            "sales",
            "stock",
            "purchases",
            "delivery",
            "invoicing",
            "payments",
            "finance",
            "reporting",
            "accounting",
        ]
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _validate_database_url(cls, v: str | None) -> str | None:
        """Normalise l'URL de la base de données."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+psycopg://")
        return v

    @field_validator("default_modules", mode="before")
    @classmethod
    def _parse_default_modules(cls, v: object) -> object:
        """Accepte soit une liste JSON soit une chaîne séparée par des virgules."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def _check_secret_key(cls, v: str) -> str:
        weak = len(v) < 32 or v.startswith("change-this")
        if weak and settings_env == "production":
            raise RuntimeError(
                "SECRET_KEY faible ou par défaut interdite en production. "
                "Générez-en une : openssl rand -hex 32"
            )
        return v

    @field_validator("environment", mode="before")
    @classmethod
    def _capture_env(cls, v: object) -> object:
        global settings_env
        settings_env = str(v)
        return v


settings = Settings()
