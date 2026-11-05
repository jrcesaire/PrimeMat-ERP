/**
 * Page Balance âgée — créances clients / dettes fournisseurs par tranche
 * d'échéance (non échues, 0-30, 31-60, 61-90, 90+ jours).
 */
"use client";

import { useState } from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { useAgedBalance } from "@/hooks/useAccounting";

const BUCKETS: { key: "not_due" | "d0_30" | "d31_60" | "d61_90" | "d90_plus"; label: string }[] = [
  { key: "not_due", label: "Non échues" },
  { key: "d0_30", label: "0-30 j" },
  { key: "d31_60", label: "31-60 j" },
  { key: "d61_90", label: "61-90 j" },
  { key: "d90_plus", label: "90+ j" },
];

export default function AgedBalancePage() {
  const [partnerType, setPartnerType] = useState<"customer" | "supplier">("customer");
  const [asOf, setAsOf] = useState("");
  const query = useAgedBalance({ partner_type: partnerType, as_of: asOf || undefined });
  const data = query.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Balance âgée</h1>
          <p className="text-sm text-muted">
            Encours par partenaire et tranche d&apos;échéance —{" "}
            {partnerType === "customer" ? "créances clients" : "dettes fournisseurs"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-md border border-line">
            {(["customer", "supplier"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setPartnerType(t)}
                className={`px-3 py-1.5 text-sm font-medium ${
                  partnerType === t
                    ? "rounded bg-gray-900 text-white"
                    : "text-muted hover:text-ink"
                }`}
              >
                {t === "customer" ? "Clients" : "Fournisseurs"}
              </button>
            ))}
          </div>
          <input
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="h-9 rounded-md border border-line px-2 text-sm"
          />
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-3">
        <Card>
          <CardDescription>Encours total</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {formatCurrency(Number(data?.total_due ?? 0))}
          </p>
        </Card>
        <Card>
          <CardDescription>Partenaires</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {data?.lines.length ?? "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>Retard &gt; 90 jours</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-red-600">
            {formatCurrency(Number(data?.totals.d90_plus ?? 0))}
          </p>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <CardHeader className="px-4 pt-4">
          <CardTitle>Encours par tranche</CardTitle>
          <CardDescription>
            {data ? `Situation au ${data.as_of}` : "Chargement…"}
          </CardDescription>
        </CardHeader>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Partenaire</th>
              <th className="px-3 py-2 text-right">Factures</th>
              <th className="px-3 py-2 text-right">Total dû</th>
              {BUCKETS.map((b) => (
                <th key={b.key} className="px-3 py-2 text-right">
                  {b.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {query.isLoading && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-faint">
                  Chargement…
                </td>
              </tr>
            )}
            {!query.isLoading && data && data.lines.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-faint">
                  Aucun encours — aucune facture non soldée à cette date.
                </td>
              </tr>
            )}
            {data?.lines.map((l) => (
              <tr key={l.partner_id} className="hover:bg-subtle">
                <td className="px-4 py-2 font-medium text-ink">{l.partner_name}</td>
                <td className="px-3 py-2 text-right tabular-nums">{l.invoice_count}</td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums">
                  {formatCurrency(Number(l.total_due))}
                </td>
                {BUCKETS.map((b) => (
                  <td key={b.key} className="px-3 py-2 text-right tabular-nums text-muted">
                    {formatCurrency(Number(l[b.key]))}
                  </td>
                ))}
              </tr>
            ))}
            {data && data.lines.length > 0 && (
              <tr className="border-t border-line bg-subtle font-semibold">
                <td className="px-4 py-2">Total</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {data.lines.reduce((s, l) => s + l.invoice_count, 0)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(Number(data.totals.total_due))}
                </td>
                {BUCKETS.map((b) => (
                  <td key={b.key} className="px-3 py-2 text-right tabular-nums">
                    {formatCurrency(Number(data.totals[b.key]))}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

