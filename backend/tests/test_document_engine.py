"""Non-régressions du moteur de documents (rendu Chromium).

Le mode ``reload`` d'Uvicorn impose une boucle ``Selector`` sous Windows.
Playwright synchrone créait alors lui-même une boucle Selector dans le thread
de rendu et ne pouvait pas lancer Chromium (``NotImplementedError`` sur
``create_subprocess_exec``). Le moteur basculait silencieusement vers
xhtml2pdf et produisait des factures déformées sur deux pages.

Le test reproduit exactement cette combinaison : boucle Selector principale,
rendu délégué à un thread, comme dans les endpoints FastAPI.
"""

from __future__ import annotations

import asyncio
import sys

import pytest

from app.core.documents.engine import DocumentEngine

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Politique Selector imposée par Uvicorn --reload : correctif Windows",
)


def test_rendu_chromium_disponible_sous_une_boucle_selector() -> None:
    """Chromium doit démarrer même si la boucle principale est Selector."""
    previous_policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:

        async def render() -> bytes:
            engine = DocumentEngine()
            html = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<style>@page { size: A4; margin: 15mm; }</style></head>"
                "<body><h1>Contrôle du moteur PDF</h1></body></html>"
            )
            # Même chemin que les endpoints : le rendu bloquant s'exécute dans
            # un thread pour ne pas bloquer la boucle asyncio.
            return await asyncio.to_thread(engine._render_with_chromium, html)

        pdf = asyncio.run(render())
    finally:
        asyncio.set_event_loop_policy(previous_policy)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000
