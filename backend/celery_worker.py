"""
Configuration de l'application Celery pour les tâches asynchrones.

Broker : Redis (configuré dans app/core/config.py).
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "erp",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.pdf_tasks",
        "app.tasks.backup_tasks",
        "app.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs) -> None:
    """Tâches périodiques programmées."""
    from celery.schedules import crontab

    sender.conf.beat_schedule = {
        "backup-daily": {
            "task": "app.tasks.backup_tasks.daily_backup",
            "schedule": crontab(hour=2, minute=0),  # tous les jours à 02h00
        },
        "reports-morning": {
            "task": "app.tasks.report_tasks.generate_daily_reports",
            "schedule": crontab(hour=6, minute=0),  # tous les jours à 06h00
        },
    }
