"""
Dépendances liées au profil de l'entreprise.

``require_company_profile`` refuse la création d'un document tant que les
informations obligatoires de l'entreprise ne sont pas renseignées : ces
mentions figurent sur les devis et factures remis au client, un document sans
téléphone ni adresse n'a aucune valeur.

L'utilisateur peut ignorer la configuration initiale, mais l'écran revient
alors dès qu'il tente de créer un devis ou une facture — c'est ce refus (409)
que l'interface intercepte pour le ramener au formulaire.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies.auth import get_current_active_user
from app.core.models.company import Company
from app.core.models.user import User
from app.core.services.company_profile import missing_company_fields

#: Code machine du refus, reconnu par le frontend pour déclencher la
#: redirection vers l'écran de configuration de l'entreprise.
COMPANY_INCOMPLETE_CODE = "company_incomplete"


async def require_company_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> Company:
    """Renvoie l'entreprise courante, ou refuse (409) si elle est incomplète.

    Le détail de l'erreur porte les champs manquants, ce qui permet à
    l'interface de les mettre en évidence au retour sur le formulaire.
    """
    company = (
        await session.get(Company, current_user.company_id)
        if current_user.company_id is not None
        else None
    )

    missing = missing_company_fields(company)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": COMPANY_INCOMPLETE_CODE,
                "message": (
                    "Complétez les informations de l'entreprise avant de créer "
                    "un document : elles figurent sur les devis et les factures."
                ),
                "missing_fields": missing,
            },
        )

    assert company is not None  # garanti : sans entreprise, `missing` est non vide
    return company
