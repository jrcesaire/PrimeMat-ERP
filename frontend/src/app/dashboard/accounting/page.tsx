/**
 * Page Comptabilité — états financiers SYSCOHADA.
 *
 * Onglets : Balance de vérification, Compte de résultat, Bilan,
 * Écritures du journal. Bouton de rattrapage pour comptabiliser
 * en masse les flux métier non encore traités.
 */
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import {
  useTrialBalance,
  useIncomeStatement,
  useBalanceSheet,
  useJournalEntries,
  useBackfill,
} from "@/hooks/useAccounting";

type Tab = "balance" | "income" | "sheet" | "entries";

const TABS: { key: Tab; label: string }[] = [
  { key: "balance", label: "Balance de vérification" },
  { key: "income", label: "Compte de résultat" },
  { key: "sheet", label: "Bilan" },
  { key: "entries", label: "Écritures" },
];

export default function AccountingPage() {
  const [tab, setTab] = useState<Tab>("balance");
  const trial = useTrialBalance();
  const income = useIncomeStatement();
  const sheet = useBalanceSheet();
  const entries = useJournalEntries();
  const backfill = useBackfill();

  const loading = trial.isLoading || income.isLoading || sheet.isLoading;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Comptabilité</h1>
          <p className="text-sm text-gray-600">
            États financiers SYSCOHADA (référentiel OHADA)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => {
              window.location.href = "/dashboard/accounting/setup";
            }}
          >
            Assistant de configuration
          </Button>
          <Button
            onClick={() => backfill.mutate()}
            disabled={backfill.isPending}
            className="bg-gray-900 text-white hover:bg-gray-700"
          >
            {backfill.isPending
              ? "Comptabilisation…"
              : "Rattrapage des flux non comptabilisés"}
          </Button>
        </div>
      </div>

      {backfill.isSuccess && (
        <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          {backfill.data.message}
        </div>
      )}
      {backfill.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Erreur lors du rattrapage : {(backfill.error as Error)?.message}
        </div>
      )}

      <div className="flex flex-wrap gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-b-2 border-gray-900 text-gray-900"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="py-10 text-center text-sm text-gray-400">Chargement…</p>
      ) : (
        <>
          {tab === "balance" && trial.data && (
            <Card className="overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-100 bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Compte</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Libellé</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Débit</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Crédit</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Solde</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {trial.data.lines.map((l) => (
                    <tr key={l.account_code} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-mono text-xs">{l.account_code}</td>
                      <td className="px-4 py-2.5">{l.account_name}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(l.debit)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(l.credit)}</td>
                      <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${l.balance >= 0 ? "text-gray-900" : "text-red-600"}`}>
                        {formatCurrency(l.balance)}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 font-semibold">
                    <td colSpan={2} className="px-4 py-2.5">Totaux</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(trial.data.total_debit)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(trial.data.total_credit)}</td>
                    <td className="px-4 py-2.5 text-right">
                      {trial.data.balanced ? (
                        <span className="text-green-700">✓ Équilibrée</span>
                      ) : (
                        <span className="text-red-600">✗ Déséquilibrée</span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>
          )}

          {tab === "income" && income.data && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-green-700">Produits</h2>
                <ul className="divide-y divide-gray-50">
                  {income.data.income.map((l) => (
                    <li key={l.label} className="flex justify-between py-2 text-sm">
                      <span className="text-gray-600">{l.label}</span>
                      <span className="tabular-nums font-medium">
                        {formatCurrency(l.amount)}
                      </span>
                    </li>
                  ))}
                  <li className="flex justify-between py-2 text-sm font-semibold">
                    <span>Total produits</span>
                    <span className="tabular-nums">
                      {formatCurrency(income.data.total_income)}
                    </span>
                  </li>
                </ul>
              </Card>
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-red-600">Charges</h2>
                <ul className="divide-y divide-gray-50">
                  {income.data.expenses.map((l) => (
                    <li key={l.label} className="flex justify-between py-2 text-sm">
                      <span className="text-gray-600">{l.label}</span>
                      <span className="tabular-nums font-medium">
                        {formatCurrency(l.amount)}
                      </span>
                    </li>
                  ))}
                  <li className="flex justify-between py-2 text-sm font-semibold">
                    <span>Total charges</span>
                    <span className="tabular-nums">
                      {formatCurrency(income.data.total_expenses)}
                    </span>
                  </li>
                </ul>
              </Card>
              <Card className="p-4 lg:col-span-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">
                    Résultat net de l&apos;exercice
                  </p>
                  <p
                    className={`text-2xl font-bold tabular-nums ${
                      income.data.net_income >= 0 ? "text-green-700" : "text-red-600"
                    }`}
                  >
                    {formatCurrency(income.data.net_income)}
                    {income.data.net_income < 0 && " (perte)"}
                  </p>
                </div>
              </Card>
            </div>
          )}

          {tab === "sheet" && sheet.data && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-gray-900">Actif</h2>
                <ul className="divide-y divide-gray-50">
                  {sheet.data.assets.map((l) => (
                    <li key={l.label} className="flex justify-between gap-4 py-2 text-sm">
                      <span className="text-gray-600">{l.label}</span>
                      <span className="tabular-nums font-medium">
                        {formatCurrency(l.amount)}
                      </span>
                    </li>
                  ))}
                  <li className="flex justify-between py-2 text-sm font-semibold">
                    <span>Total actif</span>
                    <span className="tabular-nums">
                      {formatCurrency(sheet.data.total_assets)}
                    </span>
                  </li>
                </ul>
              </Card>
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-gray-900">Passif</h2>
                <ul className="divide-y divide-gray-50">
                  {sheet.data.liabilities.map((l) => (
                    <li key={l.label} className="flex justify-between gap-4 py-2 text-sm">
                      <span className="text-gray-600">{l.label}</span>
                      <span className="tabular-nums font-medium">
                        {formatCurrency(l.amount)}
                      </span>
                    </li>
                  ))}
                  <li className="flex justify-between py-2 text-sm font-semibold">
                    <span>Total passif</span>
                    <span className="tabular-nums">
                      {formatCurrency(sheet.data.total_liabilities)}
                    </span>
                  </li>
                </ul>
              </Card>
              <Card
                className={`p-4 lg:col-span-2 ${
                  Math.abs(sheet.data.total_assets - sheet.data.total_liabilities) < 0.01
                    ? "border-green-200 bg-green-50"
                    : "border-red-200 bg-red-50"
                }`}
              >
                <p className="text-sm font-medium">
                  {Math.abs(sheet.data.total_assets - sheet.data.total_liabilities) < 0.01
                    ? "✓ Bilan équilibré"
                    : "✗ Bilan déséquilibré — vérifiez les écritures"}
                </p>
              </Card>
            </div>
          )}

          {tab === "entries" && entries.data && (
            <div className="space-y-4">
              {entries.data.map((e) => (
                <Card key={e.id} className="overflow-hidden p-0">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-mono text-xs font-semibold text-gray-700">
                        {e.reference}
                      </span>
                      <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
                        {e.journal_code}
                      </span>
                      <span className="text-sm text-gray-600">
                        {e.entry_date} — {e.description ?? ""}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {e.source_type && (
                        <span className="text-xs text-gray-400">
                          {e.source_type}#{e.source_id}
                        </span>
                      )}
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          e.status === "posted"
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {e.status === "posted" ? "publiée" : "brouillon"}
                      </span>
                      <span className="tabular-nums text-sm font-semibold">
                        {formatCurrency(Number(e.total_debit))}
                      </span>
                    </div>
                  </div>
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-gray-50">
                      {e.lines.map((l, i) => (
                        <tr key={i}>
                          <td className="w-20 px-4 py-2 font-mono text-xs">
                            {l.account_code}
                          </td>
                          <td className="px-4 py-2 text-gray-600">{l.label ?? ""}</td>
                          <td className="w-36 px-4 py-2 text-right tabular-nums">
                            {l.debit ? formatCurrency(Number(l.debit)) : ""}
                          </td>
                          <td className="w-36 px-4 py-2 text-right tabular-nums">
                            {l.credit ? formatCurrency(Number(l.credit)) : ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              ))}
              {entries.data.length === 0 && (
                <p className="py-10 text-center text-sm text-gray-400">
                  Aucune écriture — lancez le rattrapage des flux.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}