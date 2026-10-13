"""Endpoints API du module Reporting — tableaux de bord BI.

- GET /reporting/kpis                — indicateurs consolidés
- GET /reporting/sales-trend         — CA / encaissements / dépenses par mois
- GET /reporting/top-products        — top produits par CA
- GET /reporting/top-partners        — top clients par CA
- GET /reporting/invoice-status      — répartition factures par statut
- GET /reporting/payments-by-method  — encaissements par mode de paiement
- GET /reporting/expenses-by-category — dépenses par catégorie

Lecture seule, accessible à tout utilisateur authentifié (le filtrage
multi-tenant est appliqué automatiquement par le listener).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.models.user import User
from app.modules.reporting.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/kpis")
async def reporting_kpis(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Indicateurs consolidés (CA, encaissements, dépenses, impayés...)."""
    return await AnalyticsService(session).kpis()


@router.get("/sales-trend")
async def reporting_sales_trend(
    session: SessionDep,
    months: int = Query(6, ge=1, le=24),
    _: User = Depends(get_current_active_user),
):
    """CA facturé / encaissé / dépenses, par mois (n derniers mois)."""
    return await AnalyticsService(session).sales_trend(months)


@router.get("/top-products")
async def reporting_top_products(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=50),
    _: User = Depends(get_current_active_user),
):
    """Top produits par chiffre d'affaires facturé."""
    return await AnalyticsService(session).top_products(limit)


@router.get("/top-partners")
async def reporting_top_partners(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=50),
    _: User = Depends(get_current_active_user),
):
    """Top clients par chiffre d'affaires facturé."""
    return await AnalyticsService(session).top_partners(limit)


@router.get("/invoice-status")
async def reporting_invoice_status(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Répartition des factures par statut (montants + nombre)."""
    return await AnalyticsService(session).invoice_status()


@router.get("/payments-by-method")
async def reporting_payments_by_method(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Encaissements par mode de paiement."""
    return await AnalyticsService(session).payments_by_method()


@router.get("/expenses-by-category")
async def reporting_expenses_by_category(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Dépenses par catégorie."""
    return await AnalyticsService(session).expenses_by_category()


# Point d'entrée du loader dynamique (app/api/api.py)
routers = [router]

