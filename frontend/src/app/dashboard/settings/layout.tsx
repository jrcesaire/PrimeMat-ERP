/**
 * Layout des paramètres.
 *
 * Disposition maître-détail : le rail de navigation (même design que la sidebar
 * du tableau de bord) à gauche, la section courante à droite. Le rail liste les
 * réglages transverses **et** un groupe par module, cf.
 * `lib/settings-config.ts` — remplace l'ancienne barre d'onglets horizontale,
 * qui dupliquait le sous-menu de la sidebar et ne laissait aucune place aux
 * réglages métier.
 */
"use client";

import { SettingsSidebar } from "@/components/settings/settings-sidebar";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
      <SettingsSidebar />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
