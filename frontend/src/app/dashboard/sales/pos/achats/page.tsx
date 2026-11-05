/**
 * Page « Achats » du Point de Vente.
 *
 * Conforme au PRD « Improvements module PoS » §4.2.2.5 et US5 : permet de
 * saisir un achat de fourniture / quincaillerie directement depuis le PoS.
 * L'achat est enregistré dans le module Achats global (facture fournisseur),
 * comptabilisé puis réglé sur la caisse du point de vente.
 */
"use client";

import { PosQuickPurchase } from "@/components/sales/pos/PosQuickPurchase";

export default function PosPurchasesPage() {
  return <PosQuickPurchase />;
}
