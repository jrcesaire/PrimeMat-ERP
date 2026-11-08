"""
Harnais pytest — parcours d'installation et configuration de l'entreprise.

``test_company_setup`` est un script autonome qui pilote l'API réelle
(ASGITransport) et affiche « TOUTES LES VÉRIFICATIONS SONT PASSÉES (n/n) ».
Ce module le rejoue en sous-processus pour l'intégrer au rapport pytest :

    cd backend
    python -m pytest -k company_setup

Suite couverte :

- ``test_company_setup`` — complétude du profil d'entreprise, report de
  l'étape initiale et garde-fou sur la création des documents ;
- ``test_document_brand`` — logo d'entreprise et miniature de substitution
  dans l'entête des documents.
"""
from __future__ import annotations

import pytest

from conftest import SUCCESS_MARKER, run_suite

#: Suites autonomes pilotées par ce harnais.
SUITES: dict[str, str] = {
    "test_company_setup": (
        "Configuration initiale de l'entreprise et garde-fou documentaire"
    ),
    "test_document_brand": (
        "Logo d'entreprise et miniature de substitution dans les documents"
    ),
}


@pytest.mark.slow
@pytest.mark.parametrize("suite", sorted(SUITES), ids=sorted(SUITES))
def test_suite_autonome(suite: str) -> None:
    """Rejoue une suite autonome et exige un succès complet."""
    result = run_suite(suite)

    assert result.returncode == 0, (
        f"La suite {suite} ({SUITES[suite]}) a échoué "
        f"(code {result.returncode}).\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert SUCCESS_MARKER in result.stdout, (
        f"La suite {suite} s'est terminée sans afficher son marqueur de succès.\n"
        f"--- stdout ---\n{result.stdout}"
    )
