"""
Endpoints de configuration initiale (premier lancement).

- GET  /setup/status  — état du premier lancement (public, non sensible)
- POST /setup/admin   — crée entreprise + agence + rôles + compte admin
                        (public, refusé dès qu'un utilisateur existe)
- POST /setup/company — complète le profil de l'entreprise (admin connecté)

Sécurité :
- l'endpoint public est atomiquement verrouillé : dès qu'un utilisateur
  existe en base, il renvoie 403 (pas de création de compte fantôme)
- rate-limité en mémoire (même esprit que /auth/login)
- le mot de passe n'est jamais journalisé
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_superuser
from app.core.models.company import Company
from app.core.models.user import User
from app.core.services.company_profile import company_profile
from app.core.services.seed_service import bootstrap_defaults
from app.core.services.setting_service import SettingService

logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Anti brute-force (fenêtre glissante mémoire, même esprit que /auth)
# ------------------------------------------------------------------ #
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 600
_attempts: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return (
        fwd.split(",")[0].strip()
        if fwd
        else (request.client.host if request.client else "?")
    )


def _rate_limit(request: Request) -> None:
    import time

    key = f"setup:{_client_ip(request)}"
    now = time.monotonic()
    stamps = [t for t in _attempts.get(key, []) if now - t < _WINDOW_SECONDS]
    if len(stamps) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez dans quelques minutes.",
        )
    stamps.append(now)
    _attempts[key] = stamps


# ------------------------------------------------------------------ #
# Schémas
# ------------------------------------------------------------------ #
class SetupAdminRequest(BaseModel):
    """Configuration initiale — entreprise + compte administrateur."""

    company_name: str = Field(min_length=2, max_length=200)
    company_code: str = Field(min_length=2, max_length=20)
    currency_code: str = Field(min_length=3, max_length=3, default="XOF")
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(max_length=100, default="")
    last_name: str = Field(max_length=100, default="")


class SetupCompanyRequest(BaseModel):
    """Profil de l'entreprise (étape 2, admin connecté).

    Tous les champs sont facultatifs : l'étape peut être reportée. Seule la
    complétude — nom, téléphone, devise, adresse, ville, pays — conditionne
    ensuite la création des devis et des factures. Les informations fiscales,
    le logo et les CGV sont recommandés mais jamais exigés.
    """

    name: str | None = Field(default=None, max_length=200)
    establishment: str | None = Field(default=None, max_length=120)
    slogan: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=200)
    logo: str | None = Field(default=None, max_length=800_000)
    # Adresse — les clés `address_line1` / `address_city` restent acceptées
    # pour les appels déjà déployés ; elles alimentent les mêmes clés JSON.
    street: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    address_line1: str | None = Field(default=None, max_length=200)
    address_city: str | None = Field(default=None, max_length=100)
    # Informations fiscales et légales — recommandées, non obligatoires.
    ncc: str | None = Field(default=None, max_length=100)
    rccm: str | None = Field(default=None, max_length=100)
    share_capital: str | None = Field(default=None, max_length=100)
    greffe: str | None = Field(default=None, max_length=120)
    importer_code: str | None = Field(default=None, max_length=60)
    social_security_code: str | None = Field(default=None, max_length=60)
    activity_code: str | None = Field(default=None, max_length=60)
    closing_date: str | None = Field(default=None, max_length=32)
    fiscal_year_months: int | None = Field(default=None, ge=1, le=24)
    # Conditions générales de vente — page finale des devis et factures.
    cgv: str | None = None


def _validate_password(password: str) -> None:
    """Politique minimale : 8 caractères, majuscule + minuscule + chiffre."""
    if len(password) < 8:
        raise HTTPException(
            400, "Le mot de passe doit contenir au moins 8 caractères."
        )
    if not any(c.isupper() for c in password):
        raise HTTPException(400, "Le mot de passe doit contenir une majuscule.")
    if not any(c.islower() for c in password):
        raise HTTPException(400, "Le mot de passe doit contenir une minuscule.")
    if not any(c.isdigit() for c in password):
        raise HTTPException(400, "Le mot de passe doit contenir un chiffre.")


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Adresse email invalide.")
    return email


async def _setup_state(session) -> dict:
    """État du premier lancement : admin créé ? entreprise configurée ?"""
    has_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar_one() > 0

    company = (await session.execute(
        select(Company).order_by(Company.id).limit(1)
    )).scalars().first()

    configured = skipped = False
    if company is not None:
        svc = SettingService(session)
        configured = bool(await svc.get("company_configured", False))
        skipped = bool(await svc.get("company_setup_skipped", False))

    return {
        "needs_admin": not has_users,
        # Étape de premier lancement : la connexion y ramène tant qu'elle n'a
        # été ni terminée ni explicitement reportée par l'utilisateur.
        "needs_company": (company is None) or not (configured or skipped),
        # La complétude, elle, conditionne la création des documents. Un report
        # ne la change pas : l'écran revient à la première tentative.
        **company_profile(company),
        "company_name": company.name if company else None,
        "company_code": company.code if company else None,
        "currency_code": company.currency_code if company else None,
    }


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #
@router.get("/status")
async def setup_status(session: SessionDep):
    """État du premier lancement — endpoint public non sensible."""
    return await _setup_state(session)


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def setup_create_admin(
    body: SetupAdminRequest,
    request: Request,
    session: SessionDep,
):
    """Premier lancement : crée entreprise, agence, rôles et compte admin.

    Refusé (403) dès qu'un utilisateur existe — la base n'est plus vierge.
    """
    _rate_limit(request)

    # Garde-fou atomique : seulement si AUCUN utilisateur
    has_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar_one() > 0
    if has_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'instance est déjà configurée : un compte existe.",
        )

    email = _validate_email(body.email)
    _validate_password(body.password)

    from app.core.models.currency import Currency

    curr = (await session.execute(
        select(Currency).where(Currency.code == body.currency_code.upper())
    )).scalar_one_or_none()
    if curr is None or not curr.is_active:
        raise HTTPException(400, f"Devise inconnue : {body.currency_code}")

    try:
        created = await bootstrap_defaults(
            session,
            company_name=body.company_name.strip(),
            company_code=body.company_code.strip().upper(),
            company_currency=body.currency_code.upper(),
            admin_email=email,
            admin_password=body.password,
            admin_first_name=body.first_name.strip() or "Admin",
            admin_last_name=body.last_name.strip() or "Système",
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        logger.exception("Échec du setup initial")
        raise HTTPException(400, f"Configuration impossible : {exc}") from exc

    logger.info(
        "🧭 Setup initial — entreprise=%s admin=%s",
        created.get("companies"), email,
    )
    return {
        "message": "Configuration initiale terminée. Connectez-vous.",
        "email": email,
        "company_code": body.company_code.strip().upper(),
        "created": created,
    }


@router.post("/company")
async def setup_configure_company(
    body: SetupCompanyRequest,
    session: SessionDep,
    user: User = Depends(require_superuser),
):
    """Étape 2 (admin connecté) : complète le profil de l'entreprise."""
    if user.company_id is None:
        raise HTTPException(400, "Aucune entreprise associée au compte.")

    company = await session.get(Company, user.company_id)
    if company is None:
        raise HTTPException(404, "Entreprise introuvable")

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    cgv = updates.pop("cgv", None)

    # Adresse : les clés historiques (`address_line1`, `address_city`) sont
    # retirées dans tous les cas, sinon elles seraient recopiées comme
    # attributs fantômes sur l'instance.
    legacy_street = updates.pop("address_line1", None)
    legacy_city = updates.pop("address_city", None)
    street = updates.pop("street", None) or legacy_street
    city = updates.pop("city", None) or legacy_city
    country = updates.pop("country", None)
    if street or city or country:
        addr = dict(company.address or {})
        if street:
            addr["street"] = street
        if city:
            addr["city"] = city
        if country:
            addr["country"] = country
        company.address = addr

    for field, value in updates.items():
        # Filtre défensif : seules les colonnes réelles sont écrites.
        if hasattr(Company, field):
            setattr(company, field, value)

    settings = SettingService(session)
    await settings.set(
        "company_configured", True, type="boolean", company_id=company.id,
        is_public=True, description="Configuration initiale terminée",
    )
    if cgv is not None:
        await settings.set(
            "cgv_content", cgv, type="string", company_id=company.id,
            is_public=True,
            description="Conditions Générales de Vente (page finale des devis et factures)",
        )
    await session.commit()
    await session.refresh(company)
    return {
        "message": "Entreprise configurée.",
        "company_id": company.id,
        **company_profile(company),
    }


@router.post("/company/skip")
async def setup_skip_company(
    session: SessionDep,
    user: User = Depends(require_superuser),
):
    """Reporte l'étape de configuration initiale.

    L'utilisateur n'est plus ramené à l'écran à la connexion, mais la création
    d'un devis ou d'une facture reste refusée (409) tant que les informations
    obligatoires ne sont pas renseignées.
    """
    if user.company_id is None:
        raise HTTPException(400, "Aucune entreprise associée au compte.")

    await SettingService(session).set(
        "company_setup_skipped", True, type="boolean",
        company_id=user.company_id, is_public=True,
        description="Configuration de l'entreprise reportée à plus tard",
    )
    return {"message": "Configuration reportée.", "company_id": user.company_id}
