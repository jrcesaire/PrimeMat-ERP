/**
 * Page Immobilisations — registre des immobilisations amortissables.
 *
 * Chaque immobilisation est rattachée à un compte du plan OHADA (ex. 245
 * matériel de transport) ; le compte d'amortissement cumulé en découle
 * (245 → 284) et le compte de dotation est 681 (exploitation) ou 686
 * (financier). La fiche détaillée (plan d'amortissement et comptabilisation
 * des dotations) est sur `/dashboard/accounting/fixed-assets/[id]`.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmDeleteOptions, useConfirm } from "@/components/ui/confirm";
import { formatCurrency } from "@/lib/utils";
import {
  useCreateFixedAsset,
  useDeleteFixedAsset,
  useFixedAssets,
} from "@/hooks/useFixedAssets";
import type { FixedAssetCreate } from "@/lib/types";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

/** Catégories d'immobilisation et compte OHADA suggéré. */
const CATEGORIES: { value: string; label: string; account: string }[] = [
  { value: "incorporeal", label: "Immobilisation incorporelle", account: "213" },
  { value: "land", label: "Terrain (non amortissable en principe)", account: "223" },
  { value: "building", label: "Bâtiment et installations", account: "231" },
  { value: "equipment", label: "Matériel et mobilier", account: "245" },
  { value: "financial", label: "Immobilisation financière", account: "261" },
  { value: "other", label: "Autre immobilisation", account: "218" },
];

const METHOD_LABELS: Record<string, string> = {
  linear: "Linéaire",
  declining: "Dégressif",
};

const PERIODICITY_LABELS: Record<string, string> = {
  annual: "Annuelle",
  monthly: "Mensuelle",
};

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label]),
);

/** Formulaire « nouvelle immobilisation » — daté du jour. */
const newAssetForm = () => {
  const today = new Date().toISOString().slice(0, 10);
  return {
    code: "",
    name: "",
    category: "equipment",
    asset_account: "245",
    depreciation_account: "",
    expense_account: "681",
    journal_code: "OD",
    acquisition_date: today,
    in_service_date: today,
    acquisition_cost: "",
    residual_value: "",
    useful_life_years: "5",
    method: "linear",
    periodicity: "annual",
    notes: "",
  };
};

/** Cumul des dotations déjà comptabilisées d'une immobilisation. */
function postedAccumulated(asset: {
  depreciations: { status: string; amount: number }[];
}): number {
  return asset.depreciations
    .filter((d) => d.status === "posted")
    .reduce((sum, d) => sum + Number(d.amount), 0);
}

export default function FixedAssetsPage() {
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState(newAssetForm());
  const [error, setError] = useState<string | null>(null);

  const { data: assets = [], isLoading } = useFixedAssets();
  const createAsset = useCreateFixedAsset();
  const deleteAsset = useDeleteFixedAsset();
  const confirm = useConfirm();

  const setField = (key: keyof ReturnType<typeof newAssetForm>, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  /** Change la catégorie et propose le compte d'immobilisation associé. */
  const setCategory = (value: string) => {
    const category = CATEGORIES.find((c) => c.value === value);
    setForm((prev) => ({
      ...prev,
      category: value,
      asset_account: category ? category.account : prev.asset_account,
      depreciation_account: "",
    }));
  };

  const totalCost = assets.reduce((s, a) => s + Number(a.acquisition_cost), 0);
  const totalAccumulated = assets.reduce((s, a) => s + postedAccumulated(a), 0);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const payload: FixedAssetCreate = {
      code: form.code.trim(),
      name: form.name.trim(),
      category: form.category,
      asset_account: form.asset_account.trim(),
      depreciation_account: form.depreciation_account.trim() || undefined,
      expense_account: form.expense_account.trim() || "681",
      journal_code: form.journal_code.trim() || "OD",
      acquisition_date: form.acquisition_date,
      in_service_date: form.in_service_date || form.acquisition_date,
      acquisition_cost: Number(form.acquisition_cost || 0),
      residual_value: Number(form.residual_value || 0),
      useful_life_years: Number(form.useful_life_years || 1),
      method: form.method as "linear" | "declining",
      periodicity: form.periodicity as "annual" | "monthly",
      notes: form.notes.trim() || null,
    };
    try {
      await createAsset.mutateAsync(payload);
      setForm(newAssetForm());
      setOpenCreate(false);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer l'immobilisation."));
    }
  };

  const handleDelete = async (id: number, name: string) => {
    setError(null);
    const { confirmed } = await confirm(confirmDeleteOptions(name));
    if (!confirmed) return;
    try {
      await deleteAsset.mutateAsync(id);
    } catch (err: unknown) {
      setError(errMsg(err, "Suppression impossible."));
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Immobilisations</h1>
          <p className="text-sm text-muted">
            Registre des immobilisations amortissables — plans linéaires et
            dégressifs (SYSCOHADA)
          </p>
        </div>
        <Button
          onClick={() => {
            setOpenCreate((v) => !v);
            setError(null);
          }}
        >
          {openCreate ? "Fermer" : "Nouvelle immobilisation"}
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-3">
        <Card>
          <CardDescription>Valeur d&apos;acquisition</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {formatCurrency(totalCost)}
          </p>
          <p className="mt-1 text-xs text-muted">
            {assets.length} immobilisation(s)
          </p>
        </Card>
        <Card>
          <CardDescription>Amortissements comptabilisés</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {formatCurrency(totalAccumulated)}
          </p>
          <p className="mt-1 text-xs text-muted">
            Cumul des dotations déjà passées en comptabilité
          </p>
        </Card>
        <Card>
          <CardDescription>Valeur nette comptable</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {formatCurrency(totalCost - totalAccumulated)}
          </p>
          <p className="mt-1 text-xs text-muted">
            Valeur d&apos;acquisition − amortissements cumulés
          </p>
        </Card>
      </div>

      {openCreate && (
        <Card className="border border-line">
          <div className="mb-4 border-b border-line pb-3">
            <h2 className="font-semibold text-ink">
              Nouvelle immobilisation
            </h2>
            <p className="text-xs text-muted">
              Le plan d&apos;amortissement est généré automatiquement à la
              création.
            </p>
          </div>
          <form
            onSubmit={handleCreate}
            className="grid grid-cols-1 gap-4 md:grid-cols-4"
          >
            <div>
              <label className="mb-1 block text-xs text-muted">Code *</label>
              <Input
                value={form.code}
                onChange={(e) => setField("code", e.target.value)}
                placeholder="ex. IMM-2026-001"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs text-muted">
                Libellé *
              </label>
              <Input
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="ex. Camion benne 10 t"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Catégorie
              </label>
              <select
                value={form.category}
                onChange={(e) => setCategory(e.target.value)}
                className="h-10 w-full rounded-md border border-line bg-surface px-2 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs text-muted">
                Compte d&apos;immobilisation *
              </label>
              <Input
                value={form.asset_account}
                onChange={(e) => setField("asset_account", e.target.value)}
                placeholder="245"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Compte d&apos;amortissement
              </label>
              <Input
                value={form.depreciation_account}
                onChange={(e) =>
                  setField("depreciation_account", e.target.value)
                }
                placeholder="auto (245 → 284)"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Compte de dotation
              </label>
              <Input
                value={form.expense_account}
                onChange={(e) => setField("expense_account", e.target.value)}
                placeholder="681"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Journal</label>
              <Input
                value={form.journal_code}
                onChange={(e) => setField("journal_code", e.target.value)}
                placeholder="OD"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs text-muted">
                Date d&apos;acquisition *
              </label>
              <Input
                type="date"
                value={form.acquisition_date}
                onChange={(e) => setField("acquisition_date", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Mise en service
              </label>
              <Input
                type="date"
                value={form.in_service_date}
                onChange={(e) => setField("in_service_date", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Valeur d&apos;acquisition *
              </label>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.acquisition_cost}
                onChange={(e) => setField("acquisition_cost", e.target.value)}
                placeholder="0"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Valeur résiduelle
              </label>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.residual_value}
                onChange={(e) => setField("residual_value", e.target.value)}
                placeholder="0"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs text-muted">
                Durée (années) *
              </label>
              <Input
                type="number"
                min={1}
                max={100}
                value={form.useful_life_years}
                onChange={(e) => setField("useful_life_years", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Méthode</label>
              <select
                value={form.method}
                onChange={(e) => {
                  const value = e.target.value;
                  setForm((prev) => ({
                    ...prev,
                    method: value,
                    // Le dégressif n'accepte que la périodicité annuelle.
                    periodicity:
                      value === "declining" ? "annual" : prev.periodicity,
                  }));
                }}
                className="h-10 w-full rounded-md border border-line bg-surface px-2 text-sm"
              >
                <option value="linear">Linéaire</option>
                <option value="declining">Dégressif</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Périodicité
              </label>
              <select
                value={form.periodicity}
                onChange={(e) => setField("periodicity", e.target.value)}
                disabled={form.method === "declining"}
                className="h-10 w-full rounded-md border border-line bg-surface px-2 text-sm disabled:bg-subtle disabled:opacity-60"
              >
                <option value="annual">Annuelle</option>
                <option value="monthly">Mensuelle</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Notes</label>
              <Input
                value={form.notes}
                onChange={(e) => setField("notes", e.target.value)}
                placeholder="Facture, fournisseur…"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 md:col-span-4">
              <Button type="submit" disabled={createAsset.isPending}>
                {createAsset.isPending
                  ? "Création…"
                  : "Créer l'immobilisation"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setOpenCreate(false);
                  setForm(newAssetForm());
                }}
              >
                Annuler
              </Button>
              <span className="text-xs text-muted">
                Les comptes doivent exister dans le plan OHADA (245, 284, 681…).
                Le dégressif applique le coefficient SYSCOHADA puis bascule en
                linéaire sur la durée restante.
              </span>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-semibold text-ink">Registre</h2>
          <p className="text-xs text-muted">
            Ouvrez une immobilisation pour consulter son plan d&apos;amortissement
            et comptabiliser les dotations échues.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Code</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2">Comptes</th>
              <th className="px-3 py-2 text-right">Acquisition</th>
              <th className="px-3 py-2 text-right">Amortissements</th>
              <th className="px-3 py-2 text-right">VNC</th>
              <th className="px-3 py-2 text-right">Plan</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-faint">
                  Chargement…
                </td>
              </tr>
            )}
            {!isLoading && assets.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-faint">
                  Aucune immobilisation — créez-en une pour générer son plan
                  d&apos;amortissement.
                </td>
              </tr>
            )}
            {assets.map((a) => {
              const accumulated = postedAccumulated(a);
              const posted = a.depreciations.filter(
                (d) => d.status === "posted",
              ).length;
              const fullyDepreciated =
                a.depreciations.length > 0 &&
                posted === a.depreciations.length;
              return (
                <tr key={a.id} className="hover:bg-subtle">
                  <td className="px-4 py-2 font-mono text-xs font-semibold text-muted">
                    {a.code}
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-ink">{a.name}</div>
                    <div className="text-xs text-muted">
                      {CATEGORY_LABELS[a.category] ?? a.category} ·{" "}
                      {a.useful_life_years} an(s) ·{" "}
                      {METHOD_LABELS[a.method] ?? a.method}
                      {a.periodicity
                        ? ` · ${PERIODICITY_LABELS[a.periodicity] ?? a.periodicity}`
                        : ""}
                    </div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-muted">
                    {a.asset_account} / {a.depreciation_account}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-muted">
                    {formatCurrency(a.acquisition_cost)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-muted">
                    {formatCurrency(accumulated)}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold tabular-nums text-ink">
                    {formatCurrency(Number(a.acquisition_cost) - accumulated)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    <span
                      className={
                        fullyDepreciated
                          ? "font-semibold text-green-700"
                          : "text-muted"
                      }
                    >
                      {posted}/{a.depreciations.length}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-3">
                      <Link
                        href={`/dashboard/accounting/fixed-assets/${a.id}`}
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        Ouvrir
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDelete(a.id, a.name)}
                        disabled={deleteAsset.isPending}
                        className="text-sm text-red-600 hover:underline disabled:opacity-50"
                      >
                        Supprimer
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
