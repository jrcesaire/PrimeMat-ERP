/**
 * Layout du module Achats — sous-navigation en chips.
 *
 * Permet de passer d'une vue à l'autre (demandes, bons de commande,
 * réceptions, factures fournisseur, fournisseurs, suggestions, besoins) sans
 * revenir au hub ni déplier le menu latéral. Les entrées viennent de
 * `lib/nav-config`, filtrées par permission.
 */
"use client";

import { ModuleNav } from "@/components/layout/module-nav";

export default function PurchasesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <ModuleNav moduleHref="/dashboard/purchases" />
      {children}
    </div>
  );
}