"""
Endpoints de gestion des paramètres.

- GET  /settings              — liste (avec filtres)
- GET  /settings/{key}        — valeur par clé
- POST /settings              — création / mise à jour (body JSON)
- PUT  /settings/{key}        — mise à jour (body JSON partiel)
- GET  /settings/nomenclature-preview — aperçu de la prochaine référence
- POST /settings/cgv-pdf      — chargement du PDF de CGV (annexé aux devis/factures)
- GET  /settings/cgv-pdf      — métadonnées du PDF de CGV
- GET  /settings/cgv-pdf/download — téléchargement du PDF de CGV
- DELETE /settings/cgv-pdf    — suppression du PDF de CGV
- POST /settings/watermark    — chargement de l'image filigrane (tableau produits)
- GET  /settings/watermark    — métadonnées / aperçu du filigrane
- DELETE /settings/watermark  — suppression du filigrane
- PUT  /settings/watermark/opacity — opacité du filigrane (1–100 %)
"""
from __future__ import annotations

import base64
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.setting import Setting
from app.core.models.user import User

router = APIRouter()

_CGV_REL_PATH = os.path.join("uploads", "cgv.pdf")
_WATERMARK_NAMES = ("watermark.png", "watermark.jpg", "watermark.jpeg")
_WATERMARK_MAX_BYTES = 2 * 1024 * 1024


def _resources_dir() -> str:
    """Répertoire ``backend/resources`` (conteneur des uploads)."""
    from app.core.documents.engine import TEMPLATE_DIR

    return os.path.dirname(TEMPLATE_DIR)


def _watermark_existing(base: str) -> str | None:
    for name in _WATERMARK_NAMES:
        candidate = os.path.join(base, "uploads", name)
        if os.path.isfile(candidate):
            return candidate
    return None


class SettingUpsert(BaseModel):
    """Corps JSON pour la création / mise à jour d'un paramètre."""

    key: str | None = Field(default=None, description="Clé (optionnelle pour PUT dédié)")
    value: str = Field(default="")
    type: str = "string"
    is_public: bool = False
    description: str | None = None
    company_id: int | None = None


@router.get("/")
async def list_settings(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    public_only: bool = False,
    _: User = Depends(get_current_active_user),
):
    """Liste les paramètres."""
    stmt = select(Setting).order_by(Setting.key)
    if public_only:
        stmt = stmt.where(Setting.is_public.is_(True))
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    settings_list = result.scalars().all()
    return [
        {
            "key": s.key,
            "value": s.value,
            "type": s.type,
            "is_public": s.is_public,
            "description": s.description,
            "company_id": s.company_id,
        }
        for s in settings_list
    ]


@router.get("/nomenclature-preview")
async def nomenclature_preview(
    session: SessionDep,
    model: str = "quote",
    _: User = Depends(get_current_active_user),
):
    """Aperçu de la prochaine référence (sans consommer le compteur)."""
    from app.core.services.sequence_service import SequenceService

    return {
        "model": model,
        "preview": await SequenceService(session).preview(model),
    }


@router.post("/cgv-pdf")
async def upload_cgv_pdf(
    session: SessionDep,
    file: UploadFile = File(...),
    _: User = Depends(require_permission("setting", "edit")),
):
    """Charge le PDF de CGV (annexé en dernière page des devis/factures)."""
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF trop volumineux (max 5 Mo)")
    base = _resources_dir()
    os.makedirs(os.path.join(base, "uploads"), exist_ok=True)
    with open(os.path.join(base, _CGV_REL_PATH), "wb") as fh:
        fh.write(data)
    from app.core.services.setting_service import SettingService

    await SettingService(session).set(
        "cgv_pdf_path",
        "uploads/cgv.pdf",
        "string",
        True,
        "PDF des CGV annexé en dernière page des devis et factures",
    )
    return {"status": "ok", "path": "uploads/cgv.pdf", "size": len(data)}


@router.get("/cgv-pdf")
async def cgv_pdf_info(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Métadonnées du PDF de CGV chargé (None si absent)."""
    path = os.path.join(_resources_dir(), _CGV_REL_PATH)
    if not os.path.isfile(path):
        return {"exists": False}
    st = os.stat(path)
    return {
        "exists": True,
        "size": st.st_size,
        "modified": st.st_mtime,
        "path": "uploads/cgv.pdf",
    }


@router.get("/cgv-pdf/download")
async def download_cgv_pdf(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Télécharge le PDF de CGV chargé."""
    path = os.path.join(_resources_dir(), _CGV_REL_PATH)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Aucun PDF de CGV chargé")
    return FileResponse(path, media_type="application/pdf", filename="cgv.pdf")


@router.delete("/cgv-pdf")
async def delete_cgv_pdf(
    session: SessionDep,
    _: User = Depends(require_permission("setting", "edit")),
):
    """Supprime le PDF de CGV (retour au texte CGV)."""
    path = os.path.join(_resources_dir(), _CGV_REL_PATH)
    if os.path.isfile(path):
        os.remove(path)
    from app.core.services.setting_service import SettingService

    await SettingService(session).set("cgv_pdf_path", "", "string", True)
    return {"status": "deleted"}


@router.post("/watermark")
async def upload_watermark(
    session: SessionDep,
    file: UploadFile = File(...),
    _: User = Depends(require_permission("setting", "edit")),
):
    """Charge l'image filigrane (couvre le tableau des produits à l'export).

    PNG ou JPEG, max 2 Mo. Stockée dans ``resources/uploads/``.
    """
    data = await file.read()
    head = bytes(data[:8])
    if head.startswith(b"\x89PNG"):
        ext = ".png"
    elif head.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    else:
        raise HTTPException(
            status_code=400, detail="Le filigrane doit être un PNG ou un JPEG"
        )
    if len(data) > _WATERMARK_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 2 Mo)")
    base = _resources_dir()
    os.makedirs(os.path.join(base, "uploads"), exist_ok=True)
    for name in _WATERMARK_NAMES:
        old = os.path.join(base, "uploads", name)
        if os.path.isfile(old):
            os.remove(old)
    rel = os.path.join("uploads", f"watermark{ext}")
    with open(os.path.join(base, rel), "wb") as fh:
        fh.write(data)
    from app.core.services.setting_service import SettingService

    await SettingService(session).set(
        "watermark_path",
        rel,
        "string",
        True,
        "Image filigrane couvrant le tableau des produits",
    )
    return {"status": "ok", "path": rel, "size": len(data)}


@router.get("/watermark")
async def watermark_info(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Métadonnées + aperçu (data URI) du filigrane chargé (+ opacité)."""
    from app.core.services.setting_service import SettingService

    try:
        opacity = int(await SettingService(session).get("watermark_opacity", "10"))
    except (TypeError, ValueError):
        opacity = 10
    opacity = min(max(opacity, 1), 100)
    existing = _watermark_existing(_resources_dir())
    if not existing:
        return {"exists": False, "opacity": opacity}
    st = os.stat(existing)
    with open(existing, "rb") as fh:
        raw = fh.read()
    mime = "image/png" if existing.endswith(".png") else "image/jpeg"
    return {
        "exists": True,
        "size": st.st_size,
        "modified": st.st_mtime,
        "path": os.path.relpath(existing, _resources_dir()).replace(os.sep, "/"),
        "opacity": opacity,
        "preview": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}",
    }


@router.delete("/watermark")
async def delete_watermark(
    session: SessionDep,
    _: User = Depends(require_permission("setting", "edit")),
):
    """Supprime le filigrane (PDF sans filigrane)."""
    base = _resources_dir()
    existing = _watermark_existing(base)
    if existing and os.path.isfile(existing):
        os.remove(existing)
    from app.core.services.setting_service import SettingService

    await SettingService(session).set("watermark_path", "", "string", True)
    return {"status": "deleted"}


class WatermarkOpacityIn(BaseModel):
    """Corps JSON : opacité du filigrane (pourcentage 1–100)."""

    value: int = Field(..., ge=1, le=100, description="Opacité en % (1–100)")


@router.put("/watermark/opacity")
async def set_watermark_opacity(
    session: SessionDep,
    body: WatermarkOpacityIn,
    _: User = Depends(require_permission("setting", "edit")),
):
    """Réglage de l'opacité du filigrane (appliquée aux prochains PDF)."""
    from app.core.services.setting_service import SettingService

    await SettingService(session).set(
        "watermark_opacity",
        body.value,
        "integer",
        True,
        "Opacité du filigrane des documents A4, en pourcentage (1–100)",
    )
    return {"status": "ok", "opacity": body.value}


@router.get("/{key}")
async def get_setting(
    session: SessionDep,
    key: str,
    _: User = Depends(get_current_active_user),
):
    """Retourne la valeur d'un paramètre par clé."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    value = await svc.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Paramètre '{key}' introuvable")
    return {"key": key, "value": value}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_setting(
    session: SessionDep,
    body: SettingUpsert,
    _: User = Depends(require_permission("setting", "create")),
):
    """Crée ou met à jour un paramètre (body JSON — compatible longues valeurs)."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    setting = await svc.set(
        body.key or "setting",
        body.value,
        body.type,
        body.is_public,
        body.description,
        body.company_id,
    )
    return setting


@router.put("/{key}")
async def update_setting(
    session: SessionDep,
    key: str,
    body: SettingUpsert,
    _: User = Depends(require_permission("setting", "edit")),
):
    """Met à jour un paramètre existant (body JSON partiel)."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    setting = await svc.update(
        key, body.value, body.type, body.is_public, body.description
    )
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Paramètre '{key}' introuvable")
    return setting
