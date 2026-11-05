/**
 * Layout du module Comptabilité — sous-navigation en chips.
 *
 * Les chips proviennent de `lib/nav-config` (source unique de vérité) : chaque
 * sous-page du module — grand livre, TVA, immobilisations, clôture… — reste
 * ainsi accessible depuis n'importe quelle autre, sans remonter au hub ni
 * déplier la sidebar. C'est la seconde moitié du modèle de navigation de la
 * maquette (sidebar à sous-menus + chips en page).
 */
"use client";

import { ModuleNav } from "@/components/layout/module-nav";

export default function AccountingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <ModuleNav moduleHref="/dashboard/accounting" />
      {children}
    </div>
  );
}