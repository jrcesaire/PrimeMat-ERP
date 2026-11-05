/**
 * Page Grand livre auxiliaire — mouvements comptables d'un tiers.
 *
 * Affiche, pour un client ou un fournisseur, les lignes d'écriture publiées qui
 * le portent (``JournalEntryLine.partner_id``), avec le solde progressif. C'est
 * le pendant analytique de la balance âgée : ici on voit *comment* le solde du
 * tiers s'est construit (factures, règlements, avoirs, lettrages).
 */
"use client";

import { useState } from "react";
import { Card, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatDate } from "@/lib/utils";
import { usePartnerLedger } from "@/hooks/useAccounting";
import { useClients, useSuppliers } from "@/hooks/useCRM";

export default function PartnerLedgerPage() {
  const [partnerType, setPartnerType] = useState<"customer" | "supplier">(
    "customer",
  );
  const [partnerId, setPartnerId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: clients = [] } = useClients();
  const { data: suppliers = [] } = useSuppliers();
  const partners = partnerType === "customer" ? clients : suppliers;

  const query = usePartnerLedger(
    partnerId ? Number(partnerId) : null,
    dateFrom,
    dateTo,
  );
  const data = query.data ?? null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Grand livre auxiliaire
          </h1>
          <p className="text-sm text-gray-600">
            Mouvements comptables d&apos;un tiers, avec solde progressif
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex rounded-md border border-gray-200">
            {(["customer", "supplier"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  setPartnerType(t);
                  setPartnerId("");
                }}
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
            <label className="mb-1 block text-xs text-gray-500">Tiers</label>
            <select
              value={partnerId}
              onChange={(e) => setPartnerId(e.target.value)}
              className="h-10 w-64 rounded-md border border-gray-300 bg-white px-2 text-sm"
            >
              <option value="">— sélectionner un tiers —</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
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

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardDescription>Solde d&apos;ouverture</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.opening_balance) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data ? data.partner_name : "Sélectionnez un tiers"}
          </p>
        </Card>
        <Card>
          <CardDescription>Débit de la période</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.total_debit) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Factures et débits du tiers
          </p>
        </Card>
        <Card>
          <CardDescription>Crédit de la période</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {data ? formatCurrency(data.total_credit) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Règlements et avoirs
          </p>
        </Card>
        <Card>
          <CardDescription>Solde de clôture</CardDescription>
          <p
            className={`mt-1 text-2xl font-bold tabular-nums ${
              data && data.closing_balance > 0
                ? "text-amber-600"
                : "text-gray-900"
            }`}
          >
            {data ? formatCurrency(data.closing_balance) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {data
              ? data.closing_balance > 0
                ? partnerType === "customer"
                  ? "Créance à recouvrer"
                  : "Dette fournisseur"
                : data.closing_balance < 0
                ? "Solde créditeur (avance)"
                : "Solde soldé"
              : "Ouverture + débit − crédit"}
          </p>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="font-semibold text-gray-900">Mouvements</h2>
          <p className="text-xs text-gray-500">
            Écritures publiées portant ce tiers, du plus ancien au plus récent.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-2">Date</th>
              <th className="px-3 py-2">Référence</th>
              <th className="px-3 py-2">Journal</th>
              <th className="px-3 py-2">Compte</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2 text-right">Débit</th>
              <th className="px-3 py-2 text-right">Crédit</th>
              <th className="px-4 py-2 text-right">Solde</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {!partnerId && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Sélectionnez un tiers pour afficher son grand livre.
                </td>
              </tr>
            )}
            {partnerId && query.isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Chargement…
                </td>
              </tr>
            )}
            {partnerId && !query.isLoading && (data?.lines.length ?? 0) === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Aucun mouvement comptable pour ce tiers sur la période —
                  vérifiez que ses factures et règlements sont comptabilisés.
                </td>
              </tr>
            )}
            {data?.lines.map((l) => (
              <tr key={`${l.entry_id}-${l.account_code}`} className="hover:bg-gray-50">
                <td className="px-4 py-2 tabular-nums text-gray-700">
                  {formatDate(l.entry_date)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-600">
                  {l.reference}
                </td>
                <td className="px-3 py-2">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {l.journal_code}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-600">
                  {l.account_code}
                </td>
                <td className="px-3 py-2 text-gray-600">{l.label ?? "—"}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                  {l.debit ? formatCurrency(l.debit) : ""}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                  {l.credit ? formatCurrency(l.credit) : ""}
                </td>
                <td className="px-4 py-2 text-right font-semibold tabular-nums text-gray-900">
                  {formatCurrency(l.balance)}
                </td>
              </tr>
            ))}
            {data && data.lines.length > 0 && (
              <tr className="border-t border-gray-200 bg-gray-50 font-semibold">
                <td className="px-4 py-2" colSpan={5}>
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
