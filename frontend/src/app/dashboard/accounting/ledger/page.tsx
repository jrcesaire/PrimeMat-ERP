/**
 * Page Grand livre — mouvements d'un compte du plan comptable.
 *
 * Complète la balance (soldes par compte) : ici on suit le détail des
 * mouvements d'un compte, avec le solde progressif et les soldes d'ouverture
 * et de clôture de la période. Le code du compte est saisi librement (411,
 * 4431, 601…) — l'endpoint ``/financial/ledger/{account_code}`` existait déjà
 * côté API, cette page le rend accessible.
 */
"use client";

import { useState } from "react";
import { Card, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatDate } from "@/lib/utils";
import { useAccountLedger } from "@/hooks/useAccounting";

export default function AccountLedgerPage() {
  const [accountCode, setAccountCode] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const query = useAccountLedger(accountCode.trim(), dateFrom, dateTo);
  const data = query.data ?? null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grand livre</h1>
          <p className="text-sm text-gray-600">
            Mouvements d&apos;un compte du plan comptable, avec solde progressif
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-xs text-gray-500">
              Compte
            </label>
            <Input
              value={accountCode}
              onChange={(e) => setAccountCode(e.target.value)}
              placeholder="ex. 411, 4431, 601"
              className="w-40"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Du</label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-40"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Au</label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-40"
            />
          </div>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardDescription>Solde d&apos;ouverture</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.opening_balance) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data ? `${data.account_code} — ${data.account_name}` : "Saisissez un compte"}
          </p>
        </Card>
        <Card>
          <CardDescription>Débit de la période</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.total_debit) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data ? `${data.movements.length} mouvement(s)` : "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>Crédit de la période</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.total_credit) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Écritures publiées uniquement
          </p>
        </Card>
        <Card>
          <CardDescription>Solde de clôture</CardDescription>
          <p
            className={`mt-1 text-2xl font-bold tabular-nums ${
              data && data.closing_balance < 0 ? "text-blue-600" : "text-gray-900"
            }`}
          >
            {data ? formatCurrency(data.closing_balance) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data && data.closing_balance < 0
              ? "Solde créditeur"
              : "Solde débiteur"}
          </p>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="font-semibold text-gray-900">Mouvements</h2>
          <p className="text-xs text-gray-500">
            Écritures publiées, du plus ancien au plus récent.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-2">Date</th>
              <th className="px-3 py-2">Référence</th>
              <th className="px-3 py-2">Journal</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2 text-right">Débit</th>
              <th className="px-3 py-2 text-right">Crédit</th>
              <th className="px-4 py-2 text-right">Solde</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {!accountCode.trim() && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                  Saisissez un code de compte (411, 4431, 601…) pour afficher
                  son grand livre.
                </td>
              </tr>
            )}
            {accountCode.trim() && query.isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                  Chargement…
                </td>
              </tr>
            )}
            {accountCode.trim() &&
              !query.isLoading &&
              (data?.movements.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                    Aucun mouvement sur ce compte pour la période.
                  </td>
                </tr>
              )}
            {data?.movements.map((m, index) => (
              <tr key={`${m.entry_id}-${index}`} className="hover:bg-gray-50">
                <td className="px-4 py-2 tabular-nums text-gray-700">
                  {formatDate(m.entry_date)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-600">
                  {m.reference}
                </td>
                <td className="px-3 py-2">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {m.journal_code}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-600">{m.label ?? "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                  {m.debit ? formatCurrency(m.debit) : ""}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                  {m.credit ? formatCurrency(m.credit) : ""}
                </td>
                <td className="px-4 py-2 text-right font-semibold tabular-nums text-gray-900">
                  {formatCurrency(m.balance)}
                </td>
              </tr>
            ))}
            {data && data.movements.length > 0 && (
              <tr className="border-t border-gray-200 bg-gray-50 font-semibold">
                <td className="px-4 py-2" colSpan={4}>
                  Total de la période
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(data.total_debit)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatCurrency(data.total_credit)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {formatCurrency(data.closing_balance)}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
