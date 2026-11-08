/**
 * Page Comptabilité — états financiers SYSCOHADA.
 *
 * Rend l'état financier sélectionné : balance de vérification, compte de
 * résultat, bilan ou écritures du journal. **La navigation est fournie par
 * `layout.tsx`** (onglets des états + chips des pages du module) : la page ne
 * rejoue plus sa propre rangée de liens, qui dupliquait chaque entrée. L'onglet
 * actif est déduit de l'URL, ce qui rend l'adresse partageable.
 *
 * Reste ici ce qui est propre à l'écran : son titre et le bouton de rattrapage
 * qui comptabilise en masse les flux métier non encore traités.
 */
"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { accountingStatementFromPath } from "@/lib/nav-config";
import { usePathname } from "next/navigation";
import {
  useTrialBalance,
  useIncomeStatement,
  useBalanceSheet,
  useJournalEntries,
  useBackfill,
} from "@/hooks/useAccounting";

export default function AccountingPage() {
  const pathname = usePathname();
  const tab = accountingStatementFromPath(pathname);
  const trial = useTrialBalance();
  const income = useIncomeStatement();
  const sheet = useBalanceSheet();
  const entries = useJournalEntries();
  const backfill = useBackfill();

  const loading = trial.isLoading || income.isLoading || sheet.isLoading;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Comptabilité</h1>
          <p className="text-sm text-muted">
            États financiers SYSCOHADA (référentiel OHADA)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* « Assistant de configuration » n'est plus répété ici : l'entrée
              figure déjà dans la barre de chips du module, avec sa permission
              (`account:edit`). */}
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
        <div className="rounded-md border border-success/30 bg-success-soft px-4 py-3 text-sm text-success">
          {backfill.data.message}
        </div>
      )}
      {backfill.isError && (
        <div className="rounded-md border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
          Erreur lors du rattrapage : {(backfill.error as Error)?.message}
        </div>
      )}

      {loading ? (
        <p className="py-10 text-center text-sm text-faint">Chargement…</p>
      ) : (
        <>
          {tab === "balance" && trial.data && (
            <Card className="overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead className="border-b border-line bg-subtle">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Compte</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Libellé</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">Débit</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">Crédit</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">Solde</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {trial.data.lines.map((l) => (
                    <tr key={l.account_code} className="hover:bg-subtle">
                      <td className="px-4 py-2.5 font-mono text-xs">{l.account_code}</td>
                      <td className="px-4 py-2.5">{l.account_name}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(l.debit)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(l.credit)}</td>
                      <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${l.balance >= 0 ? "text-ink" : "text-danger"}`}>
                        {formatCurrency(l.balance)}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-subtle font-semibold">
                    <td colSpan={2} className="px-4 py-2.5">Totaux</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(trial.data.total_debit)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{formatCurrency(trial.data.total_credit)}</td>
                    <td className="px-4 py-2.5 text-right">
                      {trial.data.balanced ? (
                        <span className="text-success">✓ Équilibrée</span>
                      ) : (
                        <span className="text-danger">✗ Déséquilibrée</span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>
          )}

          {tab === "income" && income.data && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-success">Produits</h2>
                <ul className="divide-y divide-gray-50">
                  {income.data.income.map((l) => (
                    <li key={l.label} className="flex justify-between py-2 text-sm">
                      <span className="text-muted">{l.label}</span>
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
                <h2 className="mb-3 font-semibold text-danger">Charges</h2>
                <ul className="divide-y divide-gray-50">
                  {income.data.expenses.map((l) => (
                    <li key={l.label} className="flex justify-between py-2 text-sm">
                      <span className="text-muted">{l.label}</span>
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
                  <p className="text-sm font-semibold uppercase tracking-wide text-muted">
                    Résultat net de l&apos;exercice
                  </p>
                  <p
                    className={`text-[28px] font-semibold leading-tight tabular-nums ${
                      income.data.net_income >= 0 ? "text-success" : "text-danger"
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
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="p-4">
                <h2 className="mb-3 font-semibold text-ink">Actif</h2>
                <ul className="divide-y divide-gray-50">
                  {sheet.data.assets.map((l) => (
                    <li key={l.label} className="flex justify-between gap-4 py-2 text-sm">
                      <span className="text-muted">{l.label}</span>
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
                <h2 className="mb-3 font-semibold text-ink">Passif</h2>
                <ul className="divide-y divide-gray-50">
                  {sheet.data.liabilities.map((l) => (
                    <li key={l.label} className="flex justify-between gap-4 py-2 text-sm">
                      <span className="text-muted">{l.label}</span>
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
                    ? "border-success/30 bg-success-soft"
                    : "border-danger/30 bg-danger-soft"
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
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-subtle px-4 py-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-mono text-xs font-semibold text-muted">
                        {e.reference}
                      </span>
                      <span className="rounded bg-neutral-soft px-2 py-0.5 text-xs font-medium text-muted">
                        {e.journal_code}
                      </span>
                      <span className="text-sm text-muted">
                        {e.entry_date} — {e.description ?? ""}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {e.source_type && (
                        <span className="text-xs text-faint">
                          {e.source_type}#{e.source_id}
                        </span>
                      )}
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          e.status === "posted"
                            ? "bg-success-soft text-success"
                            : "bg-warning-soft text-warning"
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
                          <td className="px-4 py-2 text-muted">{l.label ?? ""}</td>
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
                <p className="py-10 text-center text-sm text-faint">
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