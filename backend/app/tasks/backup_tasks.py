"""Tâches asynchrones pour sauvegarde cloud."""

from celery import shared_task


@shared_task(name="backup.daily")
def daily_backup():
    """Sauvegarde quotidienne programmée."""
    from app.core.backup.engine import BackupEngine

    engine = BackupEngine()
    return engine.run_incremental()


@shared_task(name="backup.full")
def full_backup():
    """Sauvegarde complète manuelle."""
    from app.core.backup.engine import BackupEngine

    engine = BackupEngine()
    return engine.run_full()
