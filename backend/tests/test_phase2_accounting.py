"""
Harnais pytest des suites fonctionnelles de la Phase 2 comptable.

Chaque suite est un script autonome qui affiche « TOUTES LES VÉRIFICATIONS SONT
PASSÉES (n/n) » et retourne 0 en cas de succès. Ce module les rejoue en
sous-processus pour obtenir un rapport pytest unifié :

    cd backend
    python -m pytest              # toutes les suites
    python -m pytest -k pos       # seulement l'achat de quincaillerie du PoS
    python -m pytest -m slow      # suites longues uniquement

Suites couvertes :

- ``test_fiscal_closing``     — clôture d'exercice (Lot B) ;
- ``test_depreciation``       — amortissements (Lot C) ;
- ``test_vat_return``         — déclarations de TVA (Lot D) ;
- ``test_auxiliary_reports``  — grand livre auxiliaire, échéancier (Lot E) ;
- ``test_accounting_audit``   — journal d'audit comptable (Lot F) ;
- ``test_pos_purchase``       — achat de quincaillerie depuis le PoS (US5).
"""
from __future__ import annotations

import pytest

from conftest import SUCCESS_MARKER, run_suite

#: Suites autonomes pilotées par ce harnais.
SUITES: dict[str, str] = {
    "test_fiscal_closing": "Clôture d'exercice et à-nouveaux (Lot B)",
    "test_depreciation": "Amortissements linéaires et SYSCOHADA (Lot C)",
    "test_vat_return": "Déclarations de TVA (Lot D)",
    "test_auxiliary_reports": "Grand livre auxiliaire et échéancier (Lot E)",
    "test_accounting_audit": "Journal d'audit comptable (Lot F)",
    "test_pos_purchase": "Achat de quincaillerie depuis le PoS (US5)",
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
