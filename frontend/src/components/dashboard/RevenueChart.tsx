/**
 * Graphique d'évolution du chiffre d'affaires.
 *
 * Reprend la carte « Évolution du chiffre d'affaires » de la maquette : deux
 * séries (facturé / encaissé) sur les 12 derniers mois, alimentées par
 * `GET /reporting/sales-trend`. Base vide → état vide explicite.
 */
"use client";

import { BarChart3 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { useSalesTrend } from "@/hooks/useReporting";
import { formatCurrency } from "@/lib/utils";

/** Couleurs des séries — alignées sur les jetons du thème. */
const SERIES = {
  invoiced: "hsl(var(--primary-hue))",
  collected: "hsl(var(--primary-hue) / 0.30)",
};

export function RevenueChart() {
  const { data: trend = [], isLoading } = useSalesTrend(12);
  const hasData = trend.some((point) => point.invoiced > 0 || point.collected > 0);

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[17px] font-semibold text-ink">
            Évolution du chiffre d&apos;affaires
          </h2>
          <p className="mt-0.5 text-[13px] text-muted">
            Facturé et encaissé sur les 12 derniers mois
          </p>
        </div>
        <div className="flex items-center gap-4 text-[11px] text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: SERIES.invoiced }} />
            Facturé
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: SERIES.collected }} />
            Encaissé
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="mt-5 h-[260px] animate-pulse rounded-control bg-subtle" />
      ) : !hasData ? (
        <EmptyState
          icon={BarChart3}
          title="Aucune donnée de vente"
          description="Le graphique s'affichera dès les premières factures émises."
        />
      ) : (
        <div className="mt-5 h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trend} barGap={2} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="hsl(var(--line))"
              />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 10, fill: "hsl(var(--faint))" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "hsl(var(--faint))" }}
                axisLine={false}
                tickLine={false}
                width={72}
                tickFormatter={(value: number) => formatCurrency(value)}
              />
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
                contentStyle={{
                  borderRadius: 7,
                  border: "1px solid hsl(var(--line))",
                  background: "hsl(var(--surface))",
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--muted))", fontSize: 11 }}
              />
              <Bar
                dataKey="invoiced"
                name="Facturé"
                fill={SERIES.invoiced}
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="collected"
                name="Encaissé"
                fill={SERIES.collected}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}