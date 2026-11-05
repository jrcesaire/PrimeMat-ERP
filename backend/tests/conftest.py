"""
Fixtures partagées des tests backend (pytest).

Les suites de la phase 2 comptable sont des **scripts autonomes**
(``backend/test_<domaine>.py``) : chacun crée sa propre base SQLite temporaire,
fixe ``DATABASE_URL`` et change de répertoire courant au moment de l'import.
Les importer dans le processus pytest provoquerait des interférences (variable
d'environnement globale, base partagée). Le harnais les exécute donc dans un
**sous-processus dédié**, via ``run_suite``, et valide le code de sortie ainsi
que le marqueur de succès affiché par la suite.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

#: Racine du backend (le dossier qui contient ``pytest.ini``).
BACKEND_DIR = Path(__file__).resolve().parents[1]

#: Dernière ligne affichée par une suite lorsque toutes les vérifications passent.
SUCCESS_MARKER = "TOUTES LES VÉRIFICATIONS SONT PASSÉES"

#: Délai maximal accordé à une suite (secondes).
DEFAULT_TIMEOUT = 900


def run_suite(name: str, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess[str]:
    """Exécute la suite ``backend/<name>.py`` et retourne le résultat du process.

    Lève ``pytest.fail`` si le script est introuvable et
    ``subprocess.TimeoutExpired`` s'il dépasse ``timeout``.
    """
    script = BACKEND_DIR / f"{name}.py"
    if not script.exists():
        pytest.fail(f"Suite introuvable : {script}")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    # Une suite lancée depuis pytest ne doit pas hériter du contexte de test.
    env.pop("PYTEST_CURRENT_TEST", None)

    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


@pytest.fixture(scope="session")
def backend_dir() -> Path:
    """Chemin absolu de la racine du backend."""
    return BACKEND_DIR
