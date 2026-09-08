"""Tâches asynchrones pour les rapports programmés."""

from celery import shared_task


@shared_task(name="reports.daily")
def generate_daily_reports():
    """Génère les rapports quotidiens."""
    from app.modules.reporting.services.report_service import ReportService

    svc = ReportService()
    return svc.generate_daily_reports()
