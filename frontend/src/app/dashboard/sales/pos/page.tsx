/**
 * Page d'accueil du module Point de Vente (PoS).
 *
 * Conforme au PRD §4.2.1 (Mode Immersif) et §4.2.2 (Écran d'Accueil du PoS) :
 * - L'accès au module PoS bascule l'interface en mode plein écran (sidebar masquée),
 *   géré par le composant PosDashboard.
 * - Affiche le dashboard avec les 6 tuiles du module PoS.
 * - Un bouton « Quitter » permet de revenir à l'ERP standard.
 */
"use client";

import { PosDashboard } from "@/components/sales/pos/PosDashboard";

export default function PosPage() {
  return <PosDashboard />;
}
