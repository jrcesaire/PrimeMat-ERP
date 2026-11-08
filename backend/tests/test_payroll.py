"""
Harnais pytest — module Paie (barème 2026, moteur, bulletins, déclarations).

``test_payroll`` est un script autonome qui crée sa base SQLite temporaire,
peuple une entreprise (plan comptable + structure de paie) puis exerce le
service de paie de bout en bout. Il affiche
« TOUTES LES VÉRIFICATIONS SONT PASSÉES (n/n) ». Ce module le rejoue en
sous-processus pour l'intégrer au rapport pytest :

    cd backend
    python -m pytest -k payroll

Suite couverte — ``test_payroll`` : DSL de calcul sûr, barème ITS 2026
(1 800 000 / 2 parts → 373 000), CNPS plafonnée (45 × SMIG), paramètres de
paie configurables, salarié + contrat, calcul du bulletin (brut/retenues/net/
coût employeur), workflow et lot de paie, comptabilisation idempotente,
bordereau CNPS et état ITS.
"""
from __future__ import annotations

import pytest

from conftest import SUCCESS_MARKER, run_suite

#: Suites autonomes pilotées par ce harnais.
SUITES: dict[str, str] = {
    "test_payroll": (
        "Paie : barème 2026, moteur de calcul, bulletins, comptabilisation "
        "et déclarations CNPS / ITS"
    ),
}


@pytest.mark.slow
@pytest.mark.parametrize("suite", sorted(SUITES), ids=sorted(SUITES))
def test_suite_autonome(suite: str) -> None:
    """Rejoue la suite autonome et exige un succès complet."""
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
