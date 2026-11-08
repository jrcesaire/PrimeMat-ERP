/**
 * Layout du module Comptabilité — une barre d'onglets, une barre de chips.
 *
 * Deux niveaux, sans recouvrement :
 * 1. les **onglets** des quatre états financiers (balance de vérification,
 *    compte de résultat, bilan, écritures) : ce sont les vues d'un même écran,
 *    et chaque onglet est un lien vers sa route — l'URL reste partageable et
 *    un rechargement rouvre le même état ;
 * 2. les **chips** des autres pages du module (lettrage, grand livre, TVA,
 *    immobilisations, clôture…), déduites de `lib/nav-config` — source unique
 *    de vérité — et filtrées par permission comme la sidebar.
 *
 * La page Comptabilité rejouait auparavant sa propre rangée de liens, codée en
 * dur et sans contrôle de permission : chaque entrée apparaissait deux fois, et
 * les onglets ne mettaient pas l'URL à jour.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ModuleNav } from "@/components/layout/module-nav";
import { cn } from "@/lib/utils";
import {
  ACCOUNTING_STATEMENTS,
  ACCOUNTING_STATEMENT_HREFS,
  accountingStatementFromPath,
} from "@/lib/nav-config";

export default function AccountingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const activeStatement = accountingStatementFromPath(pathname);

  return (
    <div className="space-y-6">
      <ModuleNav
        moduleHref="/dashboard/accounting"
        excludeHrefs={ACCOUNTING_STATEMENT_HREFS}
      />

      <div className="flex flex-wrap gap-1 border-b border-line">
        {ACCOUNTING_STATEMENTS.map((statement) => {
          const active = statement.key === activeStatement;
          return (
            <Link
              key={statement.key}
              href={statement.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "px-4 py-2 text-sm font-medium transition-colors",
                active
                  ? "border-b-2 border-ink text-ink"
                  : "text-muted hover:text-ink",
              )}
            >
              {statement.label}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}