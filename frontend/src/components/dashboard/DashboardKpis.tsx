/**
 * Rangée d'indicateurs clés du tableau de bord.
 *
 * Reprend les 4 cartes KPI de la maquette : chiffre d'affaires, encaissements,
 * commandes et restes à recouvrer. Les valeurs proviennent de l'agrégat
 * `GET /reporting/kpis` — aucune donnée fictive : base vide → cartes à zéro.
 */
"use client";

import { StatCard } from "@/components/ui/stat-card";
import { useReportingKpis } from "@/hooks/useReporting";
import { formatCurrency, formatNumber } from "@/lib/utils";

export function DashboardKpis() {
  const { data: kpis, isLoading } = useReportingKpis();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-[122px] animate-pulse rounded-card bg-subtle" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Chiffre d'affaires"
        value={formatCurrency(kpis?.total_invoiced ?? 0)}
        dot="primary"
        hint="facturé au total"
      />
      <StatCard
        label="Encaissements"
        value={formatCurrency(kpis?.total_collected ?? 0)}
        dot="success"
        hint="règlements reçus"
      />
      <StatCard
        label="Commandes"
        value={formatNumber(kpis?.orders_total ?? 0)}
        dot="primary"
        hint={`${formatNumber(kpis?.orders_confirmed ?? 0)} confirmée(s) · ${formatNumber(kpis?.orders_draft ?? 0)} brouillon(s)`}
      />
      <StatCard
        label="Restes à recouvrer"
        value={formatCurrency(kpis?.outstanding ?? 0)}
        dot="warning"
        hint="créances clients ouvertes"
      />
    </div>
  );
}