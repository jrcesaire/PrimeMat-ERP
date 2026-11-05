/**
 * Page Journal d'audit comptable — traçabilité des écritures.
 *
 * Liste les opérations tracées sur les écritures comptables
 * (``journal_entry.created`` à la création, ``journal_entry.posted`` à la
 * publication), avec leur auteur, leur horodatage et les valeurs de
 * l'écriture. Le journal est **immuable** : l'écran est en lecture seule.
 */
"use client";

import { Fragment, useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatDate } from "@/lib/utils";
import { useAccountingAuditLogs } from "@/hooks/useAccounting";

const ACTION_LABELS: Record<string, { label: string; className: string }> = {
  "journal_entry.created": {
    label: "Création",
    className: "bg-blue-100 text-blue-800",
  },
  "journal_entry.posted": {
    label: "Publication",
    className: "bg-green-100 text-green-800",
  },
};

/** Valeur d'un champ des ``new_values`` d'une entrée d'audit. */
function field(values: Record<string, unknown> | null, key: string): string {
  const value = values?.[key];
  return value === null || value === undefined ? "—" : String(value);
}

export default function AccountingAuditPage() {
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: logs = [], isLoading } = useAccountingAuditLogs(
    action,
    dateFrom,
    dateTo,
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Journal d&apos;audit comptable
          </h1>
          <p className="text-sm text-gray-600">
            Traçabilité des écritures — qui a créé ou publié quoi, et quand
            (lecture seule)
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-xs text-gray-500">
              Opération
            </label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="h-10 w-52 rounded-md border border-gray-300 bg-white px-2 text-sm"
            >
              <option value="">Toutes</option>
              <option value="journal_entry.created">Créations</option>
              <option value="journal_entry.posted">Publications</option>
            </select>
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

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="font-semibold text-gray-900">Opérations tracées</h2>
          <p className="text-xs text-gray-500">
            {logs.length} entrée(s) — du plus récent au plus ancien.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-2">Horodatage</th>
              <th className="px-3 py-2">Opération</th>
              <th className="px-3 py-2">Écriture</th>
              <th className="px-3 py-2">Date comptable</th>
              <th className="px-3 py-2">Journal</th>
              <th className="px-3 py-2 text-right">Montant</th>
              <th className="px-3 py-2">Utilisateur</th>
              <th className="px-4 py-2 text-right">Détail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Chargement…
                </td>
              </tr>
            )}
            {!isLoading && logs.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Aucune opération tracée sur la période — les écritures créées
                  ou publiées apparaissent ici automatiquement.
                </td>
              </tr>
            )}
            {logs.map((log) => {
              const meta = ACTION_LABELS[log.action] ?? {
                label: log.action,
                className: "bg-gray-100 text-gray-700",
              };
              return (
                <Fragment key={log.id}>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-2 tabular-nums text-gray-700">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${meta.className}`}
                      >
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs font-semibold text-gray-700">
                      {field(log.new_values, "reference")}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-gray-600">
                      {field(log.new_values, "entry_date")}
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {field(log.new_values, "journal_code")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                      {formatCurrency(Number(log.new_values?.total_debit ?? 0))}
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {log.user_id ? `utilisateur #${log.user_id}` : "système"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedId(expandedId === log.id ? null : log.id)
                        }
                        className="text-sm text-gray-600 hover:underline"
                      >
                        {expandedId === log.id ? "Masquer" : "Voir"}
                      </button>
                    </td>
                  </tr>
                  {expandedId === log.id && (
                    <tr>
                      <td colSpan={8} className="bg-gray-50 px-4 py-3">
                        <p className="mb-2 text-xs font-medium text-gray-600">
                          Description : {field(log.new_values, "description")} ·
                          source : {field(log.new_values, "source_type")}#
                          {field(log.new_values, "source_id")} · exercice :{" "}
                          {field(log.new_values, "fiscal_year_id")}
                        </p>
                        <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-3 text-xs text-gray-700">
                          {JSON.stringify(log.new_values, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
