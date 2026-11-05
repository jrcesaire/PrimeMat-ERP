/**
 * Page Cash-flow — flux de trésorerie par compte (ouverture, encaissements,
 * décaissements, clôture) sur une période.
 */
"use client";

import { useState } from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { useCashFlow } from "@/hooks/useAccounting";

function Kpi({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <Card>
      <CardDescription>{label}</CardDescription>
      <p className={`mt-1 text-[28px] font-semibold leading-tight tabular-nums ${tone ?? "text-ink"}`}>
        {formatCurrency(value)}
      </p>
    </Card>
  );
}

export default function CashFlowPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const query = useCashFlow({ date_from: dateFrom || undefined, date_to: dateTo || undefined });
  const data = query.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Cash-flow</h1>
          <p className="text-sm text-muted">
            Flux de trésorerie par compte — écritures comptabilisées (classe 5).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-9 rounded-md border border-line px-2 text-sm"
          />
          <span className="text-sm text-faint">→</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-9 rounded-md border border-line px-2 text-sm"
          />
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi label="Solde d'ouverture" value={Number(data?.opening_balance ?? 0)} />
        <Kpi label="Encaissements" value={Number(data?.inflows ?? 0)} tone="text-green-600" />
        <Kpi label="Décaissements" value={Number(data?.outflows ?? 0)} tone="text-red-600" />
        <Kpi label="Flux net" value={Number(data?.net_flow ?? 0)} />
        <Kpi label="Solde de clôture" value={Number(data?.closing_balance ?? 0)} />
      </div>

      <Card className="overflow-x-auto p-0">
        <CardHeader className="px-4 pt-4">
          <CardTitle>Mouvements par compte</CardTitle>
          <CardDescription>
            {data
              ? `Période : ${data.date_from ?? "origine"} → ${data.date_to ?? "aujourd'hui"}`
              : "Chargement…"}
          </CardDescription>
        </CardHeader>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Compte</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2 text-right">Ouverture</th>
              <th className="px-3 py-2 text-right">Encaissements</th>
              <th className="px-3 py-2 text-right">Décaissements</th>
              <th className="px-3 py-2 text-right">Flux net</th>
              <th className="px-3 py-2 text-right">Clôture</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {query.isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-faint">
                  Chargement…
                </td>
              </tr>
            )}
            {!query.isLoading && data && data.by_account.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-faint">
                  Aucun mouvement de trésorerie sur la période.
                </td>
              </tr>
            )}
            {data?.by_account.map((a) => (
              <tr key={a.account_code} className="hover:bg-subtle">
                <td className="px-4 py-2 font-mono text-xs font-semibold text-muted">
                  {a.account_code}
                </td>
                <td className="px-3 py-2 text-muted">{a.account_name}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(a.opening_balance))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-green-600">
                  {formatCurrency(Number(a.inflows))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-red-600">
                  {formatCurrency(Number(a.outflows))}
                </td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums">
                  {formatCurrency(Number(a.net_flow))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(a.closing_balance))}
                </td>
              </tr>
            ))}
            {data && data.by_account.length > 0 && (
              <tr className="border-t border-line bg-subtle font-semibold">
                <td className="px-4 py-2" colSpan={2}>
                  Total
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.opening_balance))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.inflows))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.outflows))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.net_flow))}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.closing_balance))}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
