"""API Paramètres de paie — taux, barèmes et plafonds configurables."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.seed.payroll_ci import build_default_structure
from app.modules.payroll.services.settings_service import PayrollSettingsService

router = APIRouter()


class PayrollSettingsIn(BaseModel):
    """Surcharges partielles des paramètres de paie (les absents sont conservés)."""

    currency: str | None = None
    smig: float | None = None
    cnps_salary_rate: float | None = None
    cnps_employer_rate: float | None = None
    cnps_ceiling_multiple: float | None = None
    ricf_per_half_part: float | None = None
    transport_exempt: float | None = None
    its_brackets: list[dict] | None = None


@router.get("/settings")
async def get_payroll_settings(
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "view")),
):
    """Paramètres de paie effectifs (défauts + surcharges de l'entreprise)."""
    return await PayrollSettingsService(session).get(user.company_id)


@router.put("/settings")
async def update_payroll_settings(
    body: PayrollSettingsIn,
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "edit")),
):
    """Enregistre les paramètres de paie (fusion partielle)."""
    return await PayrollSettingsService(session).update(
        body.model_dump(exclude_unset=True), user.company_id
    )


@router.post("/settings/apply")
async def apply_payroll_settings(
    session: SessionDep,
    user: User = Depends(require_permission("payroll_structure", "edit")),
):
    """Applique les paramètres courants à la structure de paie (règles).

    Recalcule les rubriques (barème ITS, taux CNPS, plafond, RICF) à partir des
    paramètres — indispensable après un changement de taux.
    """
    settings = await PayrollSettingsService(session).get(user.company_id)
    created = await build_default_structure(session, user.company_id, settings)
    await session.commit()
    return {"status": "ok", "applied": created}
