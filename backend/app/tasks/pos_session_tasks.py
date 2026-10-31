"""
Tâches asynchrones pour les sessions de caisse (Point de Vente).

    auto-close-pos-sessions : ferme toutes les sessions dont l'heure de
    clôture automatique est atteinte (exécuté par Celery Beat).
"""

from celery import shared_task

from app.modules.sales.services.pos_session_service import PosSessionService
from app.core.deps import get_session

from . import SessionDep

__all__ = [
    "auto_close_pos_sessions",
]


@shared_task(name="pos.auto_close_sessions")
def auto_close_pos_sessions():
    """Ferme les sessions dont l'heure de clôture est atteinte."""
    from app.core.deps import get_session

    async def _run() -> list[str]:
        async for session in get_session():
            service = PosSessionService(session)
            closed_refs = await service.auto_close_sessions()
            await session.close()
        return []

    import asyncio

    asyncio.run(_run())
    return []
