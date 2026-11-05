"""
Service TVA déclarative — calcul, liquidation et règlement (Phase 2 PRD).

Les comptes de TVA sont identifiés par leur ``technical_name`` du plan OHADA
(``tax_collected`` pour la TVA facturée, ``tax_deductible`` pour la TVA
récupérable) : aucun préfixe de compte n'est codé en dur.

Les écritures générées par le module lui-même (``source_type`` ``vat_return``
et ``vat_payment``) sont **exclues** du calcul. Sans cela, la liquidation
d'une période la ramènerait à zéro et l'aperçu ne serait plus stable.

Déroulé : ``draft`` (calcul) → ``submitted`` (liquidation : soldage des
comptes de TVA, position nette sur le compte de l'État) → ``paid``
(règlement : ``D 441 / C 521``).
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.sequence_service import SequenceService
from app.modules.accounting.models.journal_entry import (
    JournalEntry,
    JournalEntryLine,
)
from app.modules.accounting.models.vat_return import VATLine, VATReturn
from app.modules.accounting.schemas.vat import VATPayRequest, VATReturnCreate
from app.modules.accounting.services.account_service import AccountService
from app.modules.accounting.services.journal_service import LedgerService

logger = logging.getLogger(__name__)

__all__ = ["VATService"]

#: Sources d'écritures exclues du calcul (générées par le module TVA).
GENERATED_SOURCES = ("vat_return", "vat_payment")

#: Noms techniques des comptes de TVA du plan OHADA.
COLLECTED_TECHNICAL = "tax_collected"
DEDUCTIBLE_TECHNICAL = "tax_deductible"

MOIS_FR = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)


def round2(value: float | Decimal) -> float:
    """Arrondit à 2 décimales (arrondi commercial)."""
    return float(
        Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def last_day_of_month(value: date) -> date:
    """Dernier jour du mois de ``value``."""
    return date(
        value.year, value.month, calendar.monthrange(value.year, value.month)[1]
    )


class VATService:
    """Déclarations de TVA : calcul, liquidation et règlement."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger = LedgerService(session)

    # ------------------------------------------------------------------ #
    # Calcul
    # ------------------------------------------------------------------ #
    async def compute_lines(
        self, company_id: int, period_start: date, period_end: date
    ) -> list[dict]:
        """TVA par compte sur la période (écritures publiées uniquement).

        - **collectée** = ``crédit − débit`` des comptes ``tax_collected`` ;
        - **déductible** = ``débit − crédit`` des comptes ``tax_deductible``.
        """
        accounts = {
            a.code: a
            for a in await AccountService(self.session).list_accounts(
                company_id, active_only=False, limit=2000
            )
        }
        stmt = (
            select(
                JournalEntryLine.account_code,
                func.coalesce(func.sum(JournalEntryLine.debit), 0.0),
                func.coalesce(func.sum(JournalEntryLine.credit), 0.0),
                func.count(JournalEntryLine.id),
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= period_start,
                JournalEntry.entry_date <= period_end,
                # ``source_type`` peut être NULL sur d'anciennes écritures :
                # ``NOT IN`` seul exclurait alors la ligne (logique SQL à trois
                # états).
                or_(
                    JournalEntry.source_type.is_(None),
                    JournalEntry.source_type.notin_(GENERATED_SOURCES),
                ),
            )
            .group_by(JournalEntryLine.account_code)
        )
        rows = (await self.session.execute(stmt)).all()

        lines: list[dict] = []
        for code, debit, credit, count in rows:
            account = accounts.get(code)
            if account is None:
                continue
            technical = (account.technical_name or "").strip().lower()
            if technical == COLLECTED_TECHNICAL:
                amount = round2(float(credit) - float(debit))
                kind = "collected"
            elif technical == DEDUCTIBLE_TECHNICAL:
                amount = round2(float(debit) - float(credit))
                kind = "deductible"
            else:
                continue
            if amount == 0:
                continue
            lines.append(
                {
                    "account_code": code,
                    "account_name": account.name,
                    "kind": kind,
                    "amount": amount,
                    "entry_count": int(count),
                }
            )
        lines.sort(key=lambda line: (line["kind"], line["account_code"]))
        return lines

    @staticmethod
    def totals(lines: list[dict]) -> dict:
        """Totaux : collectée, déductible, TVA à payer, crédit reportable."""
        collected = round2(
            sum(l["amount"] for l in lines if l["kind"] == "collected")
        )
        deductible = round2(
            sum(l["amount"] for l in lines if l["kind"] == "deductible")
        )
        net = round2(collected - deductible)
        return {
            "collected_amount": collected,
            "deductible_amount": deductible,
            "net_due": net if net > 0 else 0.0,
            "credit_carry": -net if net < 0 else 0.0,
        }

    @staticmethod
    def default_label(period_start: date, period_end: date) -> str:
        """Libellé par défaut : « Octobre 2026 » ou « Du 01/01 au 15/01 »."""
        if (
            period_start.day == 1
            and period_end == last_day_of_month(period_start)
            and period_start.year == period_end.year
            and period_start.month == period_end.month
        ):
            return f"{MOIS_FR[period_start.month - 1]} {period_start.year}"
        return (
            f"Du {period_start.strftime('%d/%m/%Y')} "
            f"au {period_end.strftime('%d/%m/%Y')}"
        )

    async def preview(
        self, company_id: int, period_start: date, period_end: date
    ) -> dict:
        """Aperçu non enregistré : lignes par compte et totaux."""
        if period_end < period_start:
            raise ValueError("La fin de période doit suivre le début de période.")
        lines = await self.compute_lines(company_id, period_start, period_end)
        return {
            "period_start": period_start,
            "period_end": period_end,
            "label": self.default_label(period_start, period_end),
            "lines": lines,
            **self.totals(lines),
        }

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_returns(
        self, company_id: int, status: str | None = None
    ) -> list[VATReturn]:
        """Déclarations de l'entreprise, de la plus récente à la plus ancienne."""
        stmt = (
            select(VATReturn)
            .where(VATReturn.company_id == company_id)
            .order_by(VATReturn.period_start.desc(), VATReturn.id.desc())
        )
        if status:
            stmt = stmt.where(VATReturn.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_return(self, company_id: int, return_id: int) -> VATReturn:
        """Déclaration (le détail par compte est chargé en selectin)."""
        result = await self.session.execute(
            select(VATReturn).where(
                VATReturn.company_id == company_id, VATReturn.id == return_id
            )
        )
        vat_return = result.scalar_one_or_none()
        if vat_return is None:
            raise ValueError(f"Déclaration de TVA {return_id} introuvable.")
        return vat_return

    async def _replace_lines(self, vat_return: VATReturn, lines: list[dict]) -> None:
        """Remplace le détail par compte (lecture explicite : sur un objet
        fraîchement créé, la collection déclencherait un lazy load interdit
        en contexte async)."""
        existing = await self.session.execute(
            select(VATLine).where(VATLine.vat_return_id == vat_return.id)
        )
        for row in existing.scalars().all():
            await self.session.delete(row)
        await self.session.flush()
        for line in lines:
            self.session.add(
                VATLine(
                    vat_return_id=vat_return.id,
                    company_id=vat_return.company_id,
                    **line,
                )
            )
        await self.session.flush()
        self.session.expire(vat_return, ["lines"])

    def _apply_totals(self, vat_return: VATReturn, totals: dict) -> None:
        """Recopie les totaux calculés sur la déclaration."""
        vat_return.collected_amount = totals["collected_amount"]
        vat_return.deductible_amount = totals["deductible_amount"]
        vat_return.net_due = totals["net_due"]
        vat_return.credit_carry = totals["credit_carry"]

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    async def create_return(
        self, company_id: int, data: VATReturnCreate
    ) -> VATReturn:
        """Crée une déclaration en brouillon (montants calculés sur la période)."""
        if data.period_end < data.period_start:
            raise ValueError("La fin de période doit suivre le début de période.")

        duplicate = await self.session.execute(
            select(VATReturn.id).where(
                VATReturn.company_id == company_id,
                VATReturn.period_start == data.period_start,
                VATReturn.period_end == data.period_end,
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise ValueError("Une déclaration existe déjà pour cette période.")

        preview = await self.preview(
            company_id, data.period_start, data.period_end
        )
        reference = await SequenceService(self.session).next_value(
            "vat_return", "TVA", company_id=company_id
        )

        vat_return = VATReturn(
            company_id=company_id,
            reference=reference,
            label=(data.label or preview["label"]).strip(),
            period_start=data.period_start,
            period_end=data.period_end,
            status="draft",
            counterpart_account=data.counterpart_account.strip() or "441",
            payment_account=data.payment_account.strip() or "521",
            journal_code=data.journal_code.strip() or "OD",
            notes=data.notes,
        )
        self._apply_totals(vat_return, preview)
        self.session.add(vat_return)
        await self.session.flush()
        await self._replace_lines(vat_return, preview["lines"])
        await self.session.commit()
        logger.info(
            "Déclaration TVA %s créée : collectée %s, déductible %s, due %s",
            reference, vat_return.collected_amount,
            vat_return.deductible_amount, vat_return.net_due,
        )
        return await self.get_return(company_id, vat_return.id)

    async def recompute(self, company_id: int, return_id: int) -> VATReturn:
        """Recalcule une déclaration en brouillon (après de nouvelles écritures)."""
        vat_return = await self.get_return(company_id, return_id)
        if vat_return.status != "draft":
            raise ValueError(
                "Seule une déclaration en brouillon peut être recalculée."
            )
        preview = await self.preview(
            company_id, vat_return.period_start, vat_return.period_end
        )
        self._apply_totals(vat_return, preview)
        await self._replace_lines(vat_return, preview["lines"])
        await self.session.commit()
        return await self.get_return(company_id, vat_return.id)

    async def delete_return(self, company_id: int, return_id: int) -> None:
        """Supprime une déclaration en brouillon."""
        vat_return = await self.get_return(company_id, return_id)
        if vat_return.status != "draft":
            raise ValueError(
                "Seule une déclaration en brouillon peut être supprimée."
            )
        await self.session.delete(vat_return)
        await self.session.commit()

    async def submit(self, company_id: int, return_id: int) -> VATReturn:
        """Soumet la déclaration : écriture de **liquidation** de la TVA.

        Solde les comptes de TVA de la période et constate la position nette
        sur le compte de l'État (``441`` par défaut) : crédit si TVA à payer,
        débit s'il s'agit d'un crédit de TVA reportable.
        """
        from app.modules.accounting.schemas import (
            JournalEntryCreate,
            JournalEntryLineCreate,
        )

        vat_return = await self.get_return(company_id, return_id)
        if vat_return.status != "draft":
            raise ValueError(
                f"La déclaration {vat_return.reference} a déjà été soumise."
            )

        entry_lines: list[JournalEntryLineCreate] = []
        for line in vat_return.lines:
            amount = round2(float(line.amount))
            if amount <= 0:
                continue
            collected = line.kind == "collected"
            entry_lines.append(
                JournalEntryLineCreate(
                    account_code=line.account_code,
                    label=(
                        f"{'TVA collectée' if collected else 'TVA déductible'}"
                        f" — {vat_return.reference}"
                    ),
                    debit=amount if collected else 0,
                    credit=0 if collected else amount,
                )
            )

        net = round2(
            float(vat_return.collected_amount) - float(vat_return.deductible_amount)
        )
        if net > 0:
            entry_lines.append(
                JournalEntryLineCreate(
                    account_code=vat_return.counterpart_account,
                    label=f"TVA due — {vat_return.reference}",
                    debit=0,
                    credit=net,
                )
            )
        elif net < 0:
            entry_lines.append(
                JournalEntryLineCreate(
                    account_code=vat_return.counterpart_account,
                    label=f"Crédit de TVA reportable — {vat_return.reference}",
                    debit=-net,
                    credit=0,
                )
            )

        if entry_lines:
            entry = await self.ledger.create_entry(
                company_id,
                JournalEntryCreate(
                    entry_date=vat_return.period_end,
                    journal_code=vat_return.journal_code or "OD",
                    source_type="vat_return",
                    source_id=vat_return.id,
                    description=f"Liquidation de la TVA — {vat_return.label}",
                    lines=entry_lines,
                ),
                post=True,
            )
            vat_return.journal_entry_id = entry.id

        vat_return.status = "submitted"
        vat_return.submitted_at = datetime.utcnow()
        await self.session.commit()
        logger.info(
            "Déclaration TVA %s soumise (due %s, crédit %s)",
            vat_return.reference, vat_return.net_due, vat_return.credit_carry,
        )
        return await self.get_return(company_id, vat_return.id)

    async def pay(
        self, company_id: int, return_id: int, data: VATPayRequest
    ) -> VATReturn:
        """Règle la TVA due : ``D 441 / C 521`` (décaissement)."""
        from app.modules.accounting.schemas import (
            JournalEntryCreate,
            JournalEntryLineCreate,
        )

        vat_return = await self.get_return(company_id, return_id)
        if vat_return.status != "submitted":
            raise ValueError(
                "Seule une déclaration soumise peut être réglée."
            )

        due = round2(float(vat_return.net_due))
        if due <= 0:
            raise ValueError(
                "Cette déclaration ne dégage aucune TVA à payer (crédit reportable)."
            )
        amount = round2(data.amount) if data.amount else due
        if amount <= 0:
            raise ValueError("Le montant du règlement doit être positif.")
        if amount > due + 0.01:
            raise ValueError(
                f"Le montant réglé ({amount:.2f}) dépasse la TVA due ({due:.2f})."
            )

        entry = await self.ledger.create_entry(
            company_id,
            JournalEntryCreate(
                entry_date=data.payment_date or date.today(),
                journal_code=vat_return.journal_code or "OD",
                source_type="vat_payment",
                source_id=vat_return.id,
                description=f"Règlement de la TVA — {vat_return.label}",
                lines=[
                    JournalEntryLineCreate(
                        account_code=vat_return.counterpart_account,
                        label=f"TVA due — {vat_return.reference}",
                        debit=amount,
                        credit=0,
                    ),
                    JournalEntryLineCreate(
                        account_code=vat_return.payment_account,
                        label=f"Règlement TVA — {vat_return.reference}",
                        debit=0,
                        credit=amount,
                    ),
                ],
            ),
            post=True,
        )
        vat_return.payment_entry_id = entry.id
        vat_return.status = "paid"
        vat_return.paid_at = datetime.utcnow()
        await self.session.commit()
        logger.info(
            "Déclaration TVA %s réglée pour %s", vat_return.reference, amount
        )
        return await self.get_return(company_id, vat_return.id)

