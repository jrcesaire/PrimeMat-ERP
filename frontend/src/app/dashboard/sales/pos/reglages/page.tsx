/**
 * Page Réglages du Point de Vente (PoS).
 *
 * Conforme au PRD « Improvements module PoS » :
 * - §4.2.2.6 : la tuile « Réglages » du dashboard PoS ouvre cet écran, qui ne
 *   regroupe que les paramètres du Point de Vente.
 * - §4.2.1 : mode immersif (sidebar + header masqués) — géré par le composant
 *   PosSettings, avec un bouton « Retour » vers le menu du PoS.
 * - §7 : écran réservé aux rôles Administrateur / Gérant.
 */
"use client";

import { PosSettings } from "@/components/sales/pos/PosSettings";

export default function PosSettingsPage() {
  return <PosSettings />;
}
