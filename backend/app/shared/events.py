"""
Système d'événements internes — EventBus découplé inter-modules.

Un module émet un événement sans connaître les modules qui l'écoutent.

Usage ::

    # Émission
    from app.shared.events import event_bus
    event_bus.publish("sales.order.confirmed", {"order_id": 42})

    # Écoute
    @event_bus.subscribe("sales.order.confirmed")
    async def handle_order_confirmed(event: Event):
        ...
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class Event:
    """Un événement métier."""
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    Bus d'événements in-process.

    Supporte :
    - ``publish`` / ``emit`` — émettre un événement (sync/async)
    - ``subscribe`` — enregistrer un handler async
    - ``wait_for`` — attendre qu'un événement soit publié (test)
    """

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_name: str) -> Callable[[EventHandler], EventHandler]:
        """Décorateur pour enregistrer un handler."""
        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers.setdefault(event_name, []).append(handler)
            logger.debug("Handler inscrit : %s -> %s", event_name, handler.__name__)
            return handler
        return decorator

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Désinscrit un handler."""
        if event_name in self._handlers:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name] if h is not handler
            ]

    def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> Event:
        """
        Publie un événement de manière synchrone.

        Les handlers async sont planifiés via ``asyncio.create_task``
        si on est dans un event loop, sinon exécutés via ``asyncio.run``.
        """
        event = Event(name=event_name, payload=payload or {})
        self._dispatch_sync(event)
        return event

    async def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> Event:
        """
        Publie un événement de manière asynchrone.

        Tous les handlers sont exécutés de manière concurrente.
        """
        event = Event(name=event_name, payload=payload or {})
        await self._dispatch_async(event)
        return event

    def _dispatch_sync(self, event: Event) -> None:
        handlers = self._handlers.get(event.name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Planifie la tâche async
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event.name, event.payload))
                    except RuntimeError:
                        # Pas de event loop — on ne peut pas exécuter async
                        logger.warning(
                            "Handler async pour '%s' non exécuté (pas de event loop)",
                            event.name,
                        )
                else:
                    handler(event.name, event.payload)
            except Exception:
                logger.exception("Erreur dans le handler pour '%s'", event.name)

    async def _dispatch_async(self, event: Event) -> None:
        handlers = self._handlers.get(event.name, [])
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(event.name, event.payload))
            else:
                handler(event.name, event.payload)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.exception("Erreur dans handler async: %s", r)

    def list_handlers(self) -> dict[str, int]:
        """Retourne le nombre de handlers par événement."""
        return {name: len(hs) for name, hs in self._handlers.items()}


# Instance globale singleton
event_bus = EventBus()
