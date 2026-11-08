"""API Déclarations de paie — bordereau CNPS et état ITS."""
from __future__ import annotations

import asyncio
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.payroll.services.declaration_service import (
    PayrollDeclarationService,
)

router = APIRouter()


async def _load_cnps(company_id: int, period_id: int) -> dict:
    from app.core.documents.context import ContextBuilder

    return await ContextBuilder().load_cnps(company_id, period_id)


async def _load_its(company_id: int, period_id: int) -> dict:
    from app.core.documents.context import ContextBuilder

    return await ContextBuilder().load_its(company_id, period_id)


async def _pdf(
    template: str, loader, company_id: int, period_id: int
) -> StreamingResponse:
    """Rend un document de déclaration et le renvoie en flux."""
    from app.core.documents.engine import DocumentEngine
    from app.core.documents.naming import content_disposition

    try:
        context = await loader(company_id, period_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    path = await asyncio.to_thread(
        DocumentEngine().render_to_pdf, template, context
    )
    with open(path, "rb") as handle:
        data = handle.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                context.get("doc_filename") or "declaration.pdf"
            )
        },
    )


@router.get("/declarations/cnps")
async def cnps_declaration(
    period_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("report", "view")),
):
    """Bordereau CNPS d'une période (base, part salariale, part patronale)."""
    try:
        return await PayrollDeclarationService(session).cnps_bordereau(
            user.company_id, period_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/declarations/its")
async def its_declaration(
    period_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("report", "view")),
):
    """État ITS d'une période (impôt retenu par salarié)."""
    try:
        return await PayrollDeclarationService(session).its_declaration(
            user.company_id, period_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/declarations/cnps/pdf")
async def cnps_declaration_pdf(
    period_id: int,
    user: User = Depends(require_permission("report", "view")),
):
    """Bordereau CNPS au format PDF."""
    return await _pdf("cnps_return.html", _load_cnps, user.company_id, period_id)


@router.get("/declarations/its/pdf")
async def its_declaration_pdf(
    period_id: int,
    user: User = Depends(require_permission("report", "view")),
):
    """État ITS au format PDF."""
    return await _pdf("its_return.html", _load_its, user.company_id, period_id)
