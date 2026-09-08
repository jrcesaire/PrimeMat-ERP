"""
Service de bootstrap — crée les données de démarrage au premier lancement.

Idempotent et sûr :
- Ne crée rien si les données existent déjà
- Ne réinitialise JAMAIS un mot de passe existant
- Log uniquement l'email du compte créé, jamais le mot de passe

Crée :
- les devises de référence (XOF, EUR, USD)
- l'entreprise par défaut (+ agence principale)
- les permissions système
- les rôles système (admin, manager, vendeur, comptable, magasinier)
- le premier compte super-administrateur (config FIRST_ADMIN_*)
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Référentiels
# ------------------------------------------------------------------ #
BASE_CURRENCIES: dict[str, tuple[str, str, int]] = {
    "XOF": ("Franc CFA (BCEAO)", "FCFA", 0),
    "EUR": ("Euro", "€", 2),
    "USD": ("Dollar US", "$", 2),
    "NGN": ("Naira", "₦", 2),
}

# Ressources → actions ouvertes aux rôles métier
SYSTEM_PERMISSIONS: dict[str, list[str]] = {
    "company": ["view", "create", "edit"],
    "agency": ["view", "create", "edit"],
    "user": ["view", "create", "edit", "delete"],
    "role": ["view", "create", "edit", "delete"],
    "permission": ["view"],
    "setting": ["view", "edit"],
    "module": ["view", "install", "activate", "deactivate"],
    "currency": ["view", "edit"],
    "tax": ["view", "create", "edit"],
    "sequence": ["view", "edit"],
    "audit_log": ["view"],
    "product": ["view", "create", "edit", "delete"],
    "category": ["view", "create", "edit"],
    "unit": ["view", "create", "edit"],
    "partner": ["view", "create", "edit", "delete"],
    "site": ["view", "create", "edit"],
    "quote": ["view", "create", "edit", "confirm", "delete"],
    "order": ["view", "create", "edit", "confirm", "delete"],
    "warehouse": ["view", "create", "edit"],
    "stock_level": ["view", "edit"],
    "stock_movement": ["view", "create"],
    "invoice": ["view", "create", "edit", "cancel"],
    "payment": ["view", "create", "edit", "cancel"],
    "purchase": ["view", "create", "edit", "confirm"],
    "delivery": ["view", "create", "edit", "confirm"],
    "expense": ["view", "create", "edit", "delete"],
    "report": ["view"],
    "account": ["view", "create", "edit"],
    "journal_entry": ["view", "create", "edit", "post"],
    "fiscal_year": ["view", "create", "edit", "close"],
}
ROLES: list[dict] = [
    {
        "code": "admin",
        "name": "Administrateur",
        "description": "Accès total au système.",
        "is_system": True,
        "is_global": True,
        "permissions": None,  # toutes
    },
    {
        "code": "manager",
        "name": "Manager",
        "description": "Gère l'activité courante : ventes, stock, clients, rapports.",
        "is_system": True,
        "is_global": False,
        "permissions": {
            "product": ["view", "create", "edit"],
            "partner": ["view", "create", "edit"],
            "quote": ["view", "create", "edit", "confirm"],
            "order": ["view", "create", "edit", "confirm"],
            "stock_level": ["view"],
            "stock_movement": ["view", "create"],
            "invoice": ["view", "create"],
            "payment": ["view", "create"],
            "purchase": ["view", "create"],
            "delivery": ["view", "create", "confirm"],
            "expense": ["view", "create"],
            "report": ["view"],
        },
    },
    {
        "code": "sales",
        "name": "Vendeur",
        "description": "Création de devis et commandes, consultation du catalogue.",
        "is_system": True,
        "is_global": False,
        "permissions": {
            "product": ["view"],
            "partner": ["view", "create"],
            "quote": ["view", "create", "edit"],
            "order": ["view", "create"],
            "stock_level": ["view"],
            "payment": ["view", "create"],
            "site": ["view", "create"],
        },
    },
    {
        "code": "accountant",
        "name": "Comptable",
        "description": "Facturation, paiements, suivi financier.",
        "is_system": True,
        "is_global": False,
        "permissions": {
            "partner": ["view"],
            "quote": ["view"],
            "order": ["view"],
            "invoice": ["view", "create", "edit", "cancel"],
            "payment": ["view", "create", "edit"],
            "expense": ["view", "create", "edit"],
            "tax": ["view"],
            "currency": ["view"],
            "report": ["view"],
        },
    },
    {
        "code": "warehouse",
        "name": "Magasinier",
        "description": "Gestion des entrepôts et mouvements de stock.",
        "is_system": True,
        "is_global": False,
        "permissions": {
            "product": ["view"],
            "warehouse": ["view", "create", "edit"],
            "stock_level": ["view", "edit"],
            "stock_movement": ["view", "create"],
            "delivery": ["view", "create", "confirm"],
        },
    },
]
# ------------------------------------------------------------------ #
# Bootstrap
# ------------------------------------------------------------------ #
async def bootstrap_defaults(session: AsyncSession) -> dict[str, list[str]]:
    """Crée les données de démarrage si nécessaire. Retourne les créations."""
    from app.core.models.company import Agency, Company, company_currencies
    from app.core.models.currency import Currency
    from app.core.models.role import Permission, Role, RolePermission
    from app.core.models.user import User, UserRole

    created: dict[str, list[str]] = {
        "currencies": [], "companies": [], "agencies": [],
        "perms": [], "roles": [], "users": [], "categories": [],
    }

    # 1. Devises
    for code, (name, symbol, decimals) in BASE_CURRENCIES.items():
        existing = (await session.execute(
            select(Currency).where(Currency.code == code)
        )).scalar_one_or_none()
        if existing:
            continue
        session.add(Currency(
            code=code, name=name, symbol=symbol,
            decimal_places=decimals, is_active=True,
        ))
        created["currencies"].append(code)
    if created["currencies"]:
        await session.flush()

    # 2. Entreprise par défaut
    company = (await session.execute(
        select(Company).where(Company.code == settings.first_company_code)
    )).scalar_one_or_none()
    if company is None:
        company = Company(
            name=settings.first_company_name,
            code=settings.first_company_code,
            currency_code=settings.first_company_currency,
            tax_country="CI",
            is_active=True,
        )
        session.add(company)
        await session.flush()
        created["companies"].append(company.name)
        # + devise autorisée
        await session.execute(
            company_currencies.insert().values(
                company_id=company.id, currency_code=settings.first_company_currency
            )
        )

    # 3. Agence principale
    agency = (await session.execute(
        select(Agency).where(Agency.company_id == company.id).limit(1)
    )).scalar_one_or_none()
    if agency is None:
        agency = Agency(
            company_id=company.id,
            name=settings.first_agency_name,
            code=settings.first_agency_code,
            is_active=True,
        )
        session.add(agency)
        await session.flush()
        created["agencies"].append(agency.name)
# 4. Permissions système
    perm_map: dict[str, Permission] = {}
    for resource, actions in SYSTEM_PERMISSIONS.items():
        for action in actions:
            perm = (await session.execute(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == action,
                    Permission.company_id == company.id,
                )
            )).scalar_one_or_none()
            if perm is None:
                perm = Permission(
                    resource=resource,
                    action=action,
                    description=f"{action} {resource}",
                    company_id=company.id,
                )
                session.add(perm)
                await session.flush()
                created["perms"].append(f"{resource}:{action}")
            perm_map[f"{resource}:{action}"] = perm

    # 5. Rôles système
    role_map: dict[str, Role] = {}
    for role_def in ROLES:
        role = (await session.execute(
            select(Role).where(
                Role.code == role_def["code"], Role.company_id == company.id
            )
        )).scalar_one_or_none()
        if role is None:
            role = Role(
                name=role_def["name"],
                code=role_def["code"],
                description=role_def["description"],
                is_system=role_def["is_system"],
                is_global=role_def["is_global"],
                company_id=company.id,
            )
            session.add(role)
            await session.flush()

            # Permissions du rôle
            if role_def["permissions"] is None:
                # Admin → toutes les permissions
                for key, perm in perm_map.items():
                    session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            else:
                for res, actions in role_def["permissions"].items():
                    for action in actions:
                        perm = perm_map.get(f"{res}:{action}")
                        if perm:
                            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            await session.flush()
            created["roles"].append(role_def["code"])
        role_map[role_def["code"]] = role
# 6. Compte super-administrateur initial
    admin_email = settings.first_admin_email.lower()
    admin_user = (await session.execute(
        select(User).where(User.email == admin_email)
    )).scalar_one_or_none()

    if admin_user is None:
        admin_user = User(
            email=admin_email,
            first_name=settings.first_admin_first_name,
            last_name=settings.first_admin_last_name,
            password_hash=hash_password(settings.first_admin_password),
            company_id=company.id,
            agency_id=agency.id,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        session.add(admin_user)
        await session.flush()
        # Attache le rôle admin
        if "admin" in role_map:
            session.add(UserRole(user_id=admin_user.id, role_id=role_map["admin"].id))
        created["users"].append(admin_user.email)

    # 7. Arborescence standard des catégories de produits
    from app.modules.catalogue.services.category_seed import seed_categories

    cat_created = await seed_categories(session, company.id)
    if cat_created:
        created["categories"] = cat_created

    # 8. Plan comptable OHADA + journaux standards
    from app.modules.accounting.services.account_service import AccountService

    acct_service = AccountService(session)
    accounts_created = await acct_service.seed_ohada_chart(company.id)
    journals_created = await acct_service.seed_default_journals(company.id)
    if accounts_created or journals_created:
        created["accounts"] = accounts_created
        created["journals"] = journals_created

    await session.commit()
    return created


async def run_bootstrap_if_needed() -> dict[str, list[str]] | None:
    """Exécute le bootstrap au démarrage (dev uniquement) si la base est vide."""
    if not settings.bootstrap_on_startup:
        return None

    from app.core.database import AsyncSessionLocal
    from app.core.models.user import User

    async with AsyncSessionLocal() as session:
        count = (await session.execute(
            select(User.id)
        )).scalars().first()
        if count is not None:
            logger.info("Bootstrap ignoré : des utilisateurs existent déjà.")
            return None

        created = await bootstrap_defaults(session)
        if created["users"]:
            logger.info(
                "🚀 Premier démarrage — comptes créés : "
                "entreprise=%s, admin=%s",
                created["companies"], created["users"],
            )
        return created