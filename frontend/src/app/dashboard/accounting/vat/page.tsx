/**
 * Page TVA déclarative — déclaration de la TVA d'une période.
 *
 * L'écran calcule la **TVA collectée** (comptes ``tax_collected`` : 443x) et
 * la **TVA déductible** (comptes ``tax_deductible`` : 442x/445x) de la période
 * choisie, puis permet de créer la déclaration. Le cycle est :
 *
 * 1. ``draft`` — brouillon recalculable tant qu'aucune écriture n'est passée ;
 * 2. ``submitted`` — **liquidation** : les comptes de TVA sont soldés et la
 *    position nette constatée sur le compte de l'État (crédit = TVA à payer,
 *    débit = crédit de TVA reportable) ;
 * 3. ``paid`` — **règlement** de la TVA due (``D 441 / C 521``).
 *
 * Les écritures générées par les déclarations sont exclues du calcul : un
 * nouvel aperçu d'une période déjà liquidée donne toujours les mêmes montants.
 */
"use client";

import { Fragment, useState } from "react";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmDeleteOptions, useConfirm } from "@/components/ui/confirm";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  useCreateVATReturn,
  useDeleteVATReturn,
  usePayVATReturn,
  useRecomputeVATReturn,
  useSubmitVATReturn,
  useVATPreview,
  useVATReturns,
} from "@/hooks/useVAT";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  draft: { label: "Brouillon", className: "bg-gray-100 text-gray-700" },
  submitted: { label: "Soumise", className: "bg-blue-100 text-blue-800" },
  paid: { label: "Réglée", className: "bg-green-100 text-green-800" },
};

const KIND_LABELS: Record<string, string> = {
  collected: "TVA collectée",
  deductible: "TVA déductible",
};

/** Date locale au format `YYYY-MM-DD` (sans décalage UTC). */
function isoLocal(value: Date): string {
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, "0"),
    String(value.getDate()).padStart(2, "0"),
  ].join("-");
}

/** Période par défaut : le mois civil écoulé. */
function defaultPeriod(): { start: string; end: string } {
  const now = new Date();
  return {
    start: isoLocal(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
    end: isoLocal(new Date(now.getFullYear(), now.getMonth(), 0)),
  };
}

export default function VATPage() {
  const initial = defaultPeriod();
  const [periodStart, setPeriodStart] = useState(initial.start);
  const [periodEnd, setPeriodEnd] = useState(initial.end);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const previewQuery = useVATPreview(periodStart, periodEnd);
  const preview = previewQuery.data ?? null;
  const { data: returns = [], isLoading } = useVATReturns();

  const createReturn = useCreateVATReturn();
  const recomputeReturn = useRecomputeVATReturn();
  const submitReturn = useSubmitVATReturn();
  const payReturn = usePayVATReturn();
  const deleteReturn = useDeleteVATReturn();
  const confirm = useConfirm();

  const handleCreate = async () => {
    setError(null);
    setNotice(null);
    try {
      const created = await createReturn.mutateAsync({
        period_start: periodStart,
        period_end: periodEnd,
      });
      setNotice(
        `Déclaration ${created.reference} créée (brouillon) — ${
          created.net_due > 0
            ? `TVA à payer : ${formatCurrency(created.net_due)}`
            : `crédit reportable : ${formatCurrency(created.credit_carry)}`
        }.`,
      );
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer la déclaration."));
    }
  };

  const handleSubmit = async (id: number, reference: string) => {
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm({
      title: `Soumettre la déclaration ${reference} ?`,
      description:
        "Les comptes de TVA de la période seront soldés et la position nette constatée sur le compte de l'État (TVA à payer ou crédit reportable). L'écriture générée est définitive.",
      confirmLabel: "Soumettre",
      tone: "warning",
    });
    if (!confirmed) return;
    try {
      await submitReturn.mutateAsync(id);
      setNotice(
        `Déclaration ${reference} soumise — écriture de liquidation générée.`,
      );
    } catch (err: unknown) {
      setError(errMsg(err, "Soumission impossible."));
    }
  };

  const handlePay = async (id: number, reference: string) => {
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm({
      title: `Régler la TVA de ${reference} ?`,
      description:
        "Le compte de l'État sera soldé et le compte de trésorerie débité du montant de la TVA due.",
      confirmLabel: "Régler",
      tone: "info",
    });
    if (!confirmed) return;
    try {
      await payReturn.mutateAsync({ returnId: id, data: {} });
      setNotice(`Déclaration ${reference} réglée — décaissement enregistré.`);
    } catch (err: unknown) {
      setError(errMsg(err, "Règlement impossible."));
    }
  };

  const handleRecompute = async (id: number) => {
    setError(null);
    setNotice(null);
    try {
      await recomputeReturn.mutateAsync(id);
      setNotice("Déclaration recalculée sur les écritures à jour.");
    } catch (err: unknown) {
      setError(errMsg(err, "Recalcul impossible."));
    }
  };

  const handleDelete = async (id: number, label: string) => {
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm(confirmDeleteOptions(label));
    if (!confirmed) return;
    try {
      await deleteReturn.mutateAsync(id);
    } catch (err: unknown) {
      setError(errMsg(err, "Suppression impossible."));
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Déclaration de TVA</h1>
        <p className="text-sm text-gray-600">
          TVA collectée / déductible d&apos;une période, liquidation et
          règlement (SYSCOHADA)
        </p>
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

      <Card className="border border-gray-200">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-gray-100 pb-3">
          <div>
            <h2 className="font-semibold text-gray-900">
              Période à déclarer
            </h2>
            <p className="text-xs text-gray-500">
              Les montants sont calculés sur les écritures publiées de la
              période (bornes incluses).
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="mb-1 block text-xs text-gray-500">Du</label>
              <Input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="w-40"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Au</label>
              <Input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="w-40"
              />
            </div>
            <Button
              onClick={handleCreate}
              disabled={
                createReturn.isPending ||
                previewQuery.isLoading ||
                !preview ||
                preview.lines.length === 0
              }
              className="bg-gray-900 text-white hover:bg-gray-700"
            >
              {createReturn.isPending
                ? "Création…"
                : "Créer la déclaration"}
            </Button>
          </div>
        </div>

        <div className="grid gap-6 pt-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <CardDescription>TVA collectée</CardDescription>
            <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
              {preview ? formatCurrency(preview.collected_amount) : "—"}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Comptes 443x (TVA facturée)
            </p>
          </div>
          <div>
            <CardDescription>TVA déductible</CardDescription>
            <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">
              {preview ? formatCurrency(preview.deductible_amount) : "—"}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Comptes 442x / 445x (TVA récupérable)
            </p>
          </div>
          <div>
            <CardDescription>TVA à payer</CardDescription>
            <p className="mt-1 text-2xl font-bold tabular-nums text-amber-600">
              {preview ? formatCurrency(preview.net_due) : "—"}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {preview?.label ?? "Période sélectionnée"}
            </p>
          </div>
          <div>
            <CardDescription>Crédit reportable</CardDescription>
            <p className="mt-1 text-2xl font-bold tabular-nums text-blue-600">
              {preview ? formatCurrency(preview.credit_carry) : "—"}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Reporté sur la période suivante
            </p>
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-2 py-2">Compte</th>
                <th className="px-3 py-2">Libellé</th>
                <th className="px-3 py-2">Nature</th>
                <th className="px-3 py-2 text-right">Écritures</th>
                <th className="px-3 py-2 text-right">Montant</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {previewQuery.isLoading && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-gray-400">
                    Calcul en cours…
                  </td>
                </tr>
              )}
              {!previewQuery.isLoading && (preview?.lines.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-gray-400">
                    Aucun mouvement de TVA sur cette période — vérifiez les
                    dates ou la comptabilisation des factures.
                  </td>
                </tr>
              )}
              {preview?.lines.map((l) => (
                <tr key={l.account_code} className="hover:bg-gray-50">
                  <td className="px-2 py-2 font-mono text-xs font-semibold text-gray-700">
                    {l.account_code}
                  </td>
                  <td className="px-3 py-2 text-gray-900">{l.account_name}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        l.kind === "collected"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {KIND_LABELS[l.kind] ?? l.kind}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-500">
                    {l.entry_count}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold tabular-nums text-gray-900">
                    {formatCurrency(l.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="font-semibold text-gray-900">
            Historique des déclarations
          </h2>
          <p className="text-xs text-gray-500">
            Brouillon (recalculable) → Soumise (liquidation comptabilisée) →
            Réglée (décaissement enregistré).
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-2">Référence</th>
              <th className="px-3 py-2">Période</th>
              <th className="px-3 py-2 text-right">Collectée</th>
              <th className="px-3 py-2 text-right">Déductible</th>
              <th className="px-3 py-2 text-right">À payer</th>
              <th className="px-3 py-2 text-right">Crédit</th>
              <th className="px-3 py-2">Statut</th>
              <th className="px-4 py-2 text-right">Actions</th>
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
            {!isLoading && returns.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                  Aucune déclaration — choisissez une période ci-dessus puis
                  créez la déclaration.
                </td>
              </tr>
            )}
            {returns.map((v) => {
              const status = STATUS_LABELS[v.status] ?? {
                label: v.status,
                className: "bg-gray-100 text-gray-700",
              };
              return (
                <Fragment key={v.id}>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs font-semibold text-gray-700">
                      {v.reference}
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">{v.label}</div>
                      <div className="text-xs text-gray-500">
                        {formatDate(v.period_start)} → {formatDate(v.period_end)}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {formatCurrency(v.collected_amount)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {formatCurrency(v.deductible_amount)}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-amber-700">
                      {formatCurrency(v.net_due)}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-blue-700">
                      {formatCurrency(v.credit_carry)}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap items-center justify-end gap-3">
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedId(expandedId === v.id ? null : v.id)
                          }
                          className="text-sm text-gray-600 hover:underline"
                        >
                          {expandedId === v.id ? "Masquer" : "Détail"}
                        </button>
                        {v.status === "draft" && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleRecompute(v.id)}
                              disabled={recomputeReturn.isPending}
                              className="text-sm text-gray-600 hover:underline disabled:opacity-50"
                            >
                              Recalculer
                            </button>
                            <button
                              type="button"
                              onClick={() => handleSubmit(v.id, v.reference)}
                              disabled={submitReturn.isPending}
                              className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
                            >
                              Soumettre
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDelete(v.id, v.label)}
                              disabled={deleteReturn.isPending}
                              className="text-sm text-red-600 hover:underline disabled:opacity-50"
                            >
                              Supprimer
                            </button>
                          </>
                        )}
                        {v.status === "submitted" && v.net_due > 0 && (
                          <button
                            type="button"
                            onClick={() => handlePay(v.id, v.reference)}
                            disabled={payReturn.isPending}
                            className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
                          >
                            Régler
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedId === v.id && (
                    <tr>
                      <td colSpan={8} className="bg-gray-50 px-4 py-3">
                        <p className="mb-2 text-xs font-medium text-gray-600">
                          Détail par compte —{" "}
                          {v.journal_entry_id
                            ? `liquidation : écriture #${v.journal_entry_id}`
                            : "non encore liquidée"}
                          {v.payment_entry_id
                            ? ` · règlement : écriture #${v.payment_entry_id}`
                            : ""}
                        </p>
                        <table className="w-full text-sm">
                          <tbody className="divide-y divide-gray-100">
                            {v.lines.length === 0 && (
                              <tr>
                                <td className="py-3 text-center text-gray-400">
                                  Aucun compte de TVA mouvementé.
                                </td>
                              </tr>
                            )}
                            {v.lines.map((l) => (
                              <tr key={l.id}>
                                <td className="w-20 py-1 font-mono text-xs text-gray-700">
                                  {l.account_code}
                                </td>
                                <td className="py-1 text-gray-600">
                                  {l.account_name}
                                </td>
                                <td className="w-32 py-1 text-gray-500">
                                  {KIND_LABELS[l.kind] ?? l.kind}
                                </td>
                                <td className="w-32 py-1 text-right tabular-nums text-gray-900">
                                  {formatCurrency(l.amount)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
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
