/**
 * Page Chéancier — échéances à venir et retards.
 *
 * Liste les factures clients (à encaisser) ou fournisseurs (à décaisser) non
 * soldées dont l'échéance tombe dans l'horizon choisi, triées par date
 * d'échéance. Chaque ligne indique les **jours restants** (négatif = en
 * retard) et sa tranche : en retard, 0-30, 31-60, 61-90, plus de 90 jours.
 */
"use client";

import { useState } from "react";
import { Card, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatDate } from "@/lib/utils";
import { usePaymentSchedule } from "@/hooks/useAccounting";

const BUCKETS: { key: string; label: string }[] = [
  { key: "overdue", label: "En retard" },
  { key: "d0_30", label: "0-30 j" },
  { key: "d31_60", label: "31-60 j" },
  { key: "d61_90", label: "61-90 j" },
  { key: "d90_plus", label: "Plus de 90 j" },
];

const HORIZONS = [30, 60, 90, 180, 365];

const todayISO = () => {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
};

export default function PaymentSchedulePage() {
  const [partnerType, setPartnerType] = useState<"customer" | "supplier">(
    "customer",
  );
  const [asOf, setAsOf] = useState(todayISO());
  const [horizon, setHorizon] = useState(90);

  const query = usePaymentSchedule(partnerType, asOf, horizon);
  const data = query.data ?? null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chéancier</h1>
          <p className="text-sm text-gray-600">
            Échéances à venir et retards —{" "}
            {partnerType === "customer"
              ? "créances clients à encaisser"
              : "dettes fournisseurs à décaisser"}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex rounded-md border border-gray-200">
            {(["customer", "supplier"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setPartnerType(t)}
                className={`px-3 py-1.5 text-sm font-medium ${
                  partnerType === t
                    ? "rounded bg-gray-900 text-white"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {t === "customer" ? "Clients" : "Fournisseurs"}
              </button>
            ))}
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">
              Situation au
            </label>
            <Input
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              className="w-40"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Horizon</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="h-10 w-32 rounded-md border border-gray-300 bg-white px-2 text-sm"
            >
              {HORIZONS.map((h) => (
                <option key={h} value={h}>
                  {h} jours
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardDescription>Total échéancé</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.total) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data ? `${data.lines.length} facture(s)` : "Chargement…"}
          </p>
        </Card>
        <Card>
          <CardDescription>En retard</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-red-600">
            {data ? formatCurrency(data.totals.overdue ?? 0) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Échéance dépassée au {data ? formatDate(data.as_of) : "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>À échoir sous 30 jours</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-amber-600">
            {data ? formatCurrency(data.totals.d0_30 ?? 0) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Échéances les plus proches
          </p>
        </Card>
        <Card>
          <CardDescription>Au-delà de 90 jours</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.totals.d90_plus ?? 0) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Horizon de {data?.horizon_days ?? horizon} jours
          </p>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="font-semibold text-gray-900">
            Échéances par date
          </h2>
          <p className="text-xs text-gray-500">
            Factures non soldées, triées par date d&apos;échéance.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-2">Échéance</th>
              <th className="px-3 py-2 text-right">Jours</th>
              <th className="px-3 py-2">Tiers</th>
              <th className="px-3 py-2">Référence</th>
              <th className="px-3 py-2">Facture</th>
              <th className="px-3 py-2 text-right">Montant dû</th>
              <th className="px-4 py-2">Tranche</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {query.isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                  Chargement…
                </td>
              </tr>
            )}
            {!query.isLoading && (data?.lines.length ?? 0) === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                  Aucune échéance dans l&apos;horizon de {horizon} jours — les
                  factures sont soldées ou échues au-delà.
                </td>
              </tr>
            )}
            {data?.lines.map((l) => (
              <tr key={`${l.partner_id}-${l.reference}`} className="hover:bg-gray-50">
                <td className="px-4 py-2 tabular-nums text-gray-700">
                  {formatDate(l.due_date)}
                </td>
                <td
                  className={`px-3 py-2 text-right tabular-nums ${
                    l.days_remaining < 0 ? "font-semibold text-red-600" : "text-gray-600"
                  }`}
                >
                  {l.days_remaining < 0
                    ? `${-l.days_remaining} j de retard`
                    : `${l.days_remaining} j`}
                </td>
                <td className="px-3 py-2 text-gray-900">{l.partner_name}</td>
                <td className="px-3 py-2 font-mono text-xs text-gray-600">
                  {l.reference}
                </td>
                <td className="px-3 py-2 tabular-nums text-gray-500">
                  {formatDate(l.invoice_date)}
                </td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums text-gray-900">
                  {formatCurrency(l.amount_due)}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      l.bucket === "overdue"
                        ? "bg-red-100 text-red-700"
                        : l.bucket === "d0_30"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {BUCKETS.find((b) => b.key === l.bucket)?.label ?? l.bucket}
                  </span>
                </td>
              </tr>
            ))}
            {data && data.lines.length > 0 && (
              <tr className="border-t border-gray-200 bg-gray-50 font-semibold">
                <td className="px-4 py-2" colSpan={5}>
                  Total
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(data.total)}
                </td>
                <td className="px-4 py-2" />
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
