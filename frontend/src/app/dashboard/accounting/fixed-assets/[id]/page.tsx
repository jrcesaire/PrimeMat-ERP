/**
 * Page détail d'une immobilisation — plan d'amortissement et dotations.
 *
 * Affiche la synthèse comptable (valeur d'acquisition, amortissements cumulés,
 * VNC, prochaine échéance), le tableau du plan d'amortissement et permet de
 * **comptabiliser les dotations échues** (``D 681 / C 28x``) jusqu'à une date
 * donnée — opération idempotente : rejouer ne duplique aucune écriture.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmDeleteOptions, useConfirm } from "@/components/ui/confirm";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  useDeleteFixedAsset,
  useFixedAsset,
  useFixedAssetSummary,
  useGenerateDepreciation,
} from "@/hooks/useFixedAssets";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const CATEGORY_LABELS: Record<string, string> = {
  incorporeal: "Immobilisation incorporelle",
  land: "Terrain",
  building: "Bâtiment et installations",
  equipment: "Matériel et mobilier",
  financial: "Immobilisation financière",
  other: "Autre immobilisation",
};

const METHOD_LABELS: Record<string, string> = {
  linear: "Linéaire",
  declining: "Dégressif",
};

const PERIODICITY_LABELS: Record<string, string> = {
  annual: "Annuelle",
  monthly: "Mensuelle",
};

const todayISO = () => new Date().toISOString().slice(0, 10);

export default function FixedAssetDetailPage() {
  const params = useParams<{ id: string }>();
  const assetId = Number(params?.id) || null;

  const assetQuery = useFixedAsset(assetId);
  const asset = assetQuery.data ?? null;
  const summaryQuery = useFixedAssetSummary(assetId);
  const summary = summaryQuery.data ?? null;

  const generate = useGenerateDepreciation();
  const deleteAsset = useDeleteFixedAsset();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [asOf, setAsOf] = useState(todayISO());

  const handleGenerate = async () => {
    if (!assetId) return;
    setError(null);
    setNotice(null);
    try {
      const result = await generate.mutateAsync({ assetId, asOf });
      setNotice(result.message);
    } catch (err: unknown) {
      setError(errMsg(err, "Comptabilisation des dotations impossible."));
    }
  };

  const handleDelete = async () => {
    if (!asset) return;
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm(confirmDeleteOptions(asset.name));
    if (!confirmed) return;
    try {
      await deleteAsset.mutateAsync(asset.id);
      window.location.href = "/dashboard/accounting/fixed-assets";
    } catch (err: unknown) {
      setError(errMsg(err, "Suppression impossible."));
    }
  };

  const pending = asset
    ? asset.depreciations.filter((d) => d.status === "planned")
    : [];

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/dashboard/accounting/fixed-assets"
          className="text-sm text-gray-500 hover:text-gray-800"
        >
          ← Immobilisations
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">
          {asset ? asset.name : `Immobilisation #${assetId ?? "?"}`}
        </h1>
        <p className="text-sm text-gray-600">
          {asset
            ? `${asset.code} · ${
                CATEGORY_LABELS[asset.category] ?? asset.category
              } · ${METHOD_LABELS[asset.method] ?? asset.method} ${
                PERIODICITY_LABELS[asset.periodicity] ?? ""
              } sur ${asset.useful_life_years} an(s)`
            : "Chargement…"}
        </p>
        {asset && (
          <p className="mt-1 font-mono text-xs text-gray-500">
            Comptes {asset.asset_account} (immobilisation) /{" "}
            {asset.depreciation_account} (amortissements) /{" "}
            {asset.expense_account} (dotation) · journal {asset.journal_code} ·
            mise en service le {formatDate(asset.in_service_date)}
          </p>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}
      {notice && (
        <div
          role="status"
          className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
        >
          {notice}
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardDescription>Valeur d&apos;acquisition</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {summary ? formatCurrency(summary.acquisition_cost) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Base amortissable :{" "}
            {summary ? formatCurrency(summary.depreciable_base) : "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>Amortissements cumulés</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {summary ? formatCurrency(summary.accumulated) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {summary
              ? `${summary.posted_count}/${summary.periods_count} échéance(s) comptabilisée(s)`
              : "Chargement…"}
          </p>
        </Card>
        <Card>
          <CardDescription>Valeur nette comptable</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {summary ? formatCurrency(summary.net_value) : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Reste à comptabiliser :{" "}
            {summary ? formatCurrency(summary.remaining_to_post) : "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>Prochaine dotation</CardDescription>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
            {summary?.next_amount != null
              ? formatCurrency(summary.next_amount)
              : "—"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {summary?.next_period_date
              ? `Échéance du ${formatDate(summary.next_period_date)}`
              : "Plan entièrement comptabilisé"}
          </p>
        </Card>
      </div>

      {asset && (
        <Card className="border border-gray-200">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-semibold text-gray-900">
                Comptabiliser les dotations échues
              </h2>
              <p className="text-xs text-gray-500">
                Génère une écriture par échéance arrivée à terme (D{" "}
                {asset.expense_account} / C {asset.depreciation_account}) —
                opération idempotente, les dotations déjà comptabilisées sont
                ignorées. {pending.length} échéance(s) en attente.
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label className="mb-1 block text-xs text-gray-500">
                  Échues jusqu&apos;au
                </label>
                <Input
                  type="date"
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                  className="w-40"
                />
              </div>
              <Button
                onClick={handleGenerate}
                disabled={generate.isPending || pending.length === 0}
                className="bg-gray-900 text-white hover:bg-gray-700"
              >
                {generate.isPending ? "Comptabilisation…" : "Comptabiliser"}
              </Button>
              <Button
                variant="outline"
                onClick={handleDelete}
                disabled={deleteAsset.isPending}
              >
                Supprimer
              </Button>
            </div>
          </div>
        </Card>
      )}

      {asset && (
        <Card className="overflow-x-auto p-0">
          <div className="border-b border-gray-100 px-4 py-3">
            <h2 className="font-semibold text-gray-900">
              Plan d&apos;amortissement
            </h2>
            <p className="text-xs text-gray-500">
              {asset.method === "declining"
                ? "Taux dégressif SYSCOHADA appliqué à la valeur nette comptable, puis basculement en linéaire sur la durée restante."
                : "Dotation constante sur la base amortissable."}{" "}
              La dernière échéance absorbe l&apos;écart d&apos;arrondi.
            </p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-4 py-2">#</th>
                <th className="px-3 py-2">Échéance</th>
                <th className="px-3 py-2 text-right">VNC début</th>
                <th className="px-3 py-2 text-right">Dotation</th>
                <th className="px-3 py-2 text-right">Cumul</th>
                <th className="px-3 py-2 text-right">VNC fin</th>
                <th className="px-3 py-2">État</th>
                <th className="px-4 py-2">Écriture</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {assetQuery.isLoading && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-10 text-center text-gray-400"
                  >
                    Chargement…
                  </td>
                </tr>
              )}
              {!assetQuery.isLoading && asset.depreciations.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-10 text-center text-gray-400"
                  >
                    Aucune échéance au plan d&apos;amortissement.
                  </td>
                </tr>
              )}
              {asset.depreciations.map((d) => (
                <tr
                  key={d.id}
                  className={
                    d.status === "posted" ? "bg-green-50/40" : "hover:bg-gray-50"
                  }
                >
                  <td className="px-4 py-2 tabular-nums text-gray-500">
                    {d.period_index}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-gray-700">
                    {formatDate(d.period_date)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">
                    {formatCurrency(d.opening_value)}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold tabular-nums text-gray-900">
                    {formatCurrency(d.amount)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">
                    {formatCurrency(d.accumulated)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">
                    {formatCurrency(d.net_value)}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        d.status === "posted"
                          ? "bg-green-100 text-green-700"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {d.status === "posted" ? "comptabilisée" : "à comptabiliser"}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">
                    {d.journal_entry_id ? `écriture #${d.journal_entry_id}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
