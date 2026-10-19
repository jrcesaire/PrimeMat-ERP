"""
Service Demande d'Achat (DA) — workflow de validation.

Règles (PRD Module Achats V1) :
- création par tout utilisateur ``purchase:create`` ;
- ``submitted`` → ``approved`` / ``rejected`` (permission ``purchase:approve``) ;
- le montant estimé au-dessus du seuil ``purchase_approval_threshold``
  (paramètre réglable, défaut 500 000 FCFA) est signalé ``above_threshold``
  pour les circuits de validation hiérarchique ;
- ``approved`` → convertible en Bon de commande.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.core.services.setting_service import SettingService
from app.modules.purchases.models import (
    PurchaseRequest,
    PurchaseRequestLine,
)
from app.modules.purchases.schemas import (
    PurchaseRequestCreate,
    PurchaseRequestUpdate,
)
from app.shared.enums import PurchaseRequestStatus

logger = logging.getLogger(__name__)

DEFAULT_APPROVAL_THRESHOLD = 500_000  # FCFA


class RequestService:
    """Workflow des demandes d'achat."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    # ------------------------------------------------------------------ #
    # Paramètres
    # ------------------------------------------------------------------ #
    async def approval_threshold(self) -> int:
        """Seuil de validation hiérarchique (réglable dans Settings)."""
        raw = await SettingService(self.session).get(
            "purchase_approval_threshold", None
        )
        try:
            return int(raw) if raw is not None else DEFAULT_APPROVAL_THRESHOLD
        except (TypeError, ValueError):
            return DEFAULT_APPROVAL_THRESHOLD

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_requests(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        requester_id: int | None = None,
    ) -> list[PurchaseRequest]:
        stmt = select(PurchaseRequest).options(
            selectinload(PurchaseRequest.lines),
            selectinload(PurchaseRequest.supplier),
            selectinload(PurchaseRequest.requester),
        )
        if status:
            stmt = stmt.where(PurchaseRequest.status == status)
        if requester_id:
            stmt = stmt.where(PurchaseRequest.requester_id == requester_id)
        stmt = stmt.order_by(PurchaseRequest.id.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_request(self, request_id: int) -> PurchaseRequest | None:
        stmt = (
            select(PurchaseRequest)
            .options(
                selectinload(PurchaseRequest.lines),
                selectinload(PurchaseRequest.supplier),
                selectinload(PurchaseRequest.requester),
                selectinload(PurchaseRequest.validator),
            )
            .where(PurchaseRequest.id == request_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_request(
        self, data: PurchaseRequestCreate, company_id: int, user_id: int
    ) -> PurchaseRequest:
        if not data.lines:
            raise ValueError("La demande d'achat doit comporter au moins une ligne.")

        number = await self.sequences.next_value("purchase_request", "DA")
        request = PurchaseRequest(
            number=number,
            requester_id=user_id,
            supplier_id=data.supplier_id,
            status=PurchaseRequestStatus.DRAFT.value,
            priority=data.priority,
            request_date=data.request_date,
            needed_by=data.needed_by,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(request)

        for line_data in data.lines:
            request.lines.append(
                PurchaseRequestLine(
                    product_id=line_data.product_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit=line_data.unit,
                    estimated_unit_price=line_data.estimated_unit_price,
                    company_id=company_id,
                )
            )

        await self._refresh_totals(request)
        await self.session.commit()
        await self.session.refresh(request)
        logger.info("Demande d'achat %s créée (%s)", number, request.status)
        return request


    async def update_request(
        self, request_id: int, data: PurchaseRequestUpdate
    ) -> PurchaseRequest | None:
        request = await self.get_request(request_id)
        if request is None:
            return None
        if request.status not in (
            PurchaseRequestStatus.DRAFT.value,
            PurchaseRequestStatus.SUBMITTED.value,
        ):
            raise ValueError(
                "Seule une demande brouillon ou soumise peut être modifiée."
            )

        for field in ("supplier_id", "priority", "needed_by", "notes"):
            value = getattr(data, field, None)
            if value is not None:
                setattr(request, field, value)

        if data.lines is not None:
            if not data.lines:
                raise ValueError("La demande d'achat doit comporter au moins une ligne.")
            request.lines.clear()
            await self.session.flush()
            for line_data in data.lines:
                request.lines.append(
                    PurchaseRequestLine(
                        product_id=line_data.product_id,
                        description=line_data.description,
                        quantity=line_data.quantity,
                        unit=line_data.unit,
                        estimated_unit_price=line_data.estimated_unit_price,
                        company_id=request.company_id,
                    )
                )

        await self._refresh_totals(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def submit(self, request_id: int) -> PurchaseRequest | None:
        """Brouillon → soumise (en attente de validation)."""
        request = await self.get_request(request_id)
        if request is None:
            return None
        if request.status != PurchaseRequestStatus.DRAFT.value:
            raise ValueError("Seule une demande brouillon peut être soumise.")
        request.status = PurchaseRequestStatus.SUBMITTED.value
        request.submitted_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(request)
        logger.info("Demande %s soumise", request.number)
        return request

    async def approve(
        self, request_id: int, validator_id: int
    ) -> PurchaseRequest | None:
        request = await self.get_request(request_id)
        if request is None:
            return None
        if request.status != PurchaseRequestStatus.SUBMITTED.value:
            raise ValueError("Seule une demande soumise peut être validée.")
        request.status = PurchaseRequestStatus.APPROVED.value
        request.validator_id = validator_id
        request.validated_at = datetime.utcnow()
        request.rejection_reason = None
        await self.session.commit()
        await self.session.refresh(request)
        logger.info("Demande %s validée", request.number)
        return request

    async def reject(
        self, request_id: int, validator_id: int, reason: str | None = None
    ) -> PurchaseRequest | None:
        request = await self.get_request(request_id)
        if request is None:
            return None
        if request.status != PurchaseRequestStatus.SUBMITTED.value:
            raise ValueError("Seule une demande soumise peut être rejetée.")
        request.status = PurchaseRequestStatus.REJECTED.value
        request.validator_id = validator_id
        request.validated_at = datetime.utcnow()
        request.rejection_reason = reason
        await self.session.commit()
        await self.session.refresh(request)
        logger.info("Demande %s rejetée", request.number)
        return request

    async def delete_request(self, request_id: int) -> bool:
        """Suppression — brouillon ou rejetée uniquement."""
        request = await self.get_request(request_id)
        if request is None:
            return False
        if request.status not in (
            PurchaseRequestStatus.DRAFT.value,
            PurchaseRequestStatus.REJECTED.value,
        ):
            raise ValueError(
                "Seule une demande brouillon ou rejetée peut être supprimée."
            )
        await self.session.delete(request)
        await self.session.commit()
        return True

    # ------------------------------------------------------------------ #
    # Internes
    # ------------------------------------------------------------------ #
    async def _refresh_totals(self, request: PurchaseRequest) -> None:
        await self.session.flush()
        total = sum(
            float(line.quantity) * float(line.estimated_unit_price)
            for line in request.lines
        )
        request.estimated_total = total

