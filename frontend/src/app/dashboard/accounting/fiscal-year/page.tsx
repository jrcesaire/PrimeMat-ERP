/**
 * Page Clôture d'exercice — verrouillage et report à nouveau automatique.
 *
 * Pour l'exercice sélectionné, l'écran montre l'**aperçu** fourni par le
 * backend (comptes de charges/produits à solder, résultat de l'exercice,
 * exercice qui recevra le report à nouveau) puis déclenche la clôture :
 *
 * 1. soldage des classes 6-7-8 → résultat au compte **121** (bénéfice) ou
 *    **129** (perte) ;
 * 2. affectation du résultat au **report à nouveau** (**111** / **119**) sur
 *    l'exercice suivant, créé automatiquement s'il n'existe pas ;
 * 3. verrouillage : plus aucune écriture ne peut être saisie dans l'exercice.
 *
 * La réouverture retire les écritures de clôture générées pour permettre une
 * correction, puis une nouvelle clôture les régénère sans doublon.
 */
"use client";

import { useEffect, useState } from "react";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConfirm } from "@/components/ui/confirm";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  useCloseFiscalYear,
  useCreateFiscalYear,
  useFiscalYearClosingPreview,
  useFiscalYears,
  useReopenFiscalYear,
} from "@/hooks/useOHADA";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

/** Formulaire « nouvel exercice » — année civile en cours. */
const newYearForm = () => {
  const year = new Date().getFullYear();
  return {
    name: `Exercice ${year}`,
    start_date: `${year}-01-01`,
    end_date: `${year}-12-31`,
  };
};

export default function FiscalYearClosingPage() {
  const { data: years = [], isLoading } = useFiscalYears();
  const [selectedYearId, setSelectedYearId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState(newYearForm());

  const previewQuery = useFiscalYearClosingPreview(selectedYearId);
  const preview = previewQuery.data ?? null;
  const closeYear = useCloseFiscalYear();
  const reopenYear = useReopenFiscalYear();
  const createYear = useCreateFiscalYear();
  const confirm = useConfirm();

  // Du plus récent au plus ancien : l'exercice ouvert prime à la sélection.
  const sortedYears = [...years].sort((a, b) =>
    b.start_date.localeCompare(a.start_date),
  );
  const selectedYear =
    sortedYears.find((y) => y.id === selectedYearId) ?? null;

  useEffect(() => {
    if (selectedYearId !== null || sortedYears.length === 0) return;
    const open = sortedYears.find((y) => y.status === "open");
    setSelectedYearId((open ?? sortedYears[0]).id);
  }, [sortedYears, selectedYearId]);

  const handleCreateYear = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    try {
      const created = await createYear.mutateAsync({
        name: form.name.trim(),
        start_date: form.start_date,
        end_date: form.end_date,
      });
      setForm(newYearForm());
      setOpenCreate(false);
      setSelectedYearId(created.id);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer l'exercice."));
    }
  };

  const handleClose = async () => {
    if (!selectedYear) return;
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm({
      title: `Clôturer « ${selectedYear.name} » ?`,
      description:
        "Les comptes de charges et de produits seront soldés, le résultat porté au compte 121 (bénéfice) ou 129 (perte), puis affecté au report à nouveau (111/119) sur l'exercice suivant. L'exercice sera ensuite verrouillé : plus aucune écriture ne pourra y être saisie.",
      confirmLabel: "Clôturer l'exercice",
      tone: "warning",
      acknowledgement:
        "Je comprends que l'exercice sera verrouillé après la clôture.",
    });
    if (!confirmed) return;
    try {
      await closeYear.mutateAsync(selectedYear.id);
      setNotice(
        `Exercice « ${selectedYear.name} » clôturé — résultat reporté et écritures verrouillées.`,
      );
    } catch (err: unknown) {
      setError(errMsg(err, "Clôture impossible."));
    }
  };

  const handleReopen = async () => {
    if (!selectedYear) return;
    setError(null);
    setNotice(null);
    const { confirmed } = await confirm({
      title: `Réouvrir « ${selectedYear.name} » ?`,
      description:
        "Les écritures générées par la clôture (soldage des charges/produits et affectation du résultat) seront supprimées afin qu'une nouvelle clôture les régénère à partir des soldes à jour.",
      confirmLabel: "Réouvrir",
      tone: "danger",
    });
    if (!confirmed) return;
    try {
      await reopenYear.mutateAsync(selectedYear.id);
      setNotice(
        `Exercice « ${selectedYear.name} » réouvert — vous pouvez corriger puis clôturer à nouveau.`,
      );
    } catch (err: unknown) {
      setError(errMsg(err, "Réouverture impossible."));
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">
            Clôture d&apos;exercice
          </h1>
          <p className="text-sm text-muted">
            Soldage des charges et produits, report à nouveau automatique et
            verrouillage de l&apos;exercice
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setOpenCreate((v) => !v);
            setError(null);
          }}
        >
          {openCreate ? "Fermer" : "Nouvel exercice"}
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
      {notice && (
        <div
          role="status"
          className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
        >
          {notice}
        </div>
      )}

      {openCreate && (
        <Card className="border border-line">
          <div className="mb-4 border-b border-line pb-3">
            <h2 className="font-semibold text-ink">Nouvel exercice</h2>
          </div>
          <form
            onSubmit={handleCreateYear}
            className="grid grid-cols-1 gap-4 md:grid-cols-4"
          >
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs text-muted">
                Libellé *
              </label>
              <Input
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="ex. Exercice 2027"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Début *</label>
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) =>
                  setForm((p) => ({ ...p, start_date: e.target.value }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Fin *</label>
              <Input
                type="date"
                value={form.end_date}
                onChange={(e) =>
                  setForm((p) => ({ ...p, end_date: e.target.value }))
                }
                required
              />
            </div>
            <div className="flex items-end gap-2 md:col-span-4">
              <Button type="submit" disabled={createYear.isPending}>
                {createYear.isPending ? "Création…" : "Créer l'exercice"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setOpenCreate(false);
                  setForm(newYearForm());
                }}
              >
                Annuler
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="p-0">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-semibold text-ink">Exercices comptables</h2>
          <p className="text-xs text-muted">
            Sélectionnez l&apos;exercice à clôturer. Un exercice clôturé est
            verrouillé : ses écritures ne peuvent plus être saisies ni publiées.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 px-4 py-3">
          {isLoading && (
            <span className="text-sm text-faint">Chargement…</span>
          )}
          {!isLoading && sortedYears.length === 0 && (
            <span className="text-sm text-faint">
              Aucun exercice comptable — créez-en un pour commencer.
            </span>
          )}
          {sortedYears.map((y) => {
            const active = y.id === selectedYearId;
            return (
              <button
                key={y.id}
                type="button"
                onClick={() => {
                  setSelectedYearId(y.id);
                  setNotice(null);
                  setError(null);
                }}
                className={`flex flex-col items-start rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  active
                    ? "border-primary bg-primary/5"
                    : "border-line hover:bg-subtle"
                }`}
              >
                <span className="font-medium text-ink">{y.name}</span>
                <span className="text-xs text-muted">
                  {formatDate(y.start_date)} → {formatDate(y.end_date)}
                </span>
                <span
                  className={`mt-1 rounded px-2 py-0.5 text-xs font-medium ${
                    y.status === "closed"
                      ? "bg-neutral-soft text-muted"
                      : "bg-success-soft text-success"
                  }`}
                >
                  {y.status === "closed" ? "clôturé" : "ouvert"}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      {selectedYear && (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardDescription>Résultat de l&apos;exercice</CardDescription>
              <p
                className={`mt-1 text-[28px] font-semibold leading-tight tabular-nums ${
                  preview?.result_type === "profit"
                    ? "text-green-600"
                    : preview?.result_type === "loss"
                    ? "text-red-600"
                    : "text-ink"
                }`}
              >
                {preview ? formatCurrency(preview.result) : "—"}
              </p>
              <p className="mt-1 text-xs text-muted">
                {preview?.result_type === "profit"
                  ? `Bénéfice — comptabilisé au compte ${preview.result_account}`
                  : preview?.result_type === "loss"
                  ? `Perte — comptabilisée au compte ${preview.result_account}`
                  : "Aucun mouvement de charge ou de produit"}
              </p>
            </Card>
            <Card>
              <CardDescription>Comptes à solder</CardDescription>
              <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
                {preview ? preview.lines.length : "—"}
              </p>
              <p className="mt-1 text-xs text-muted">
                Charges (classe 6) et produits (classes 7 et 8)
              </p>
            </Card>
            <Card>
              <CardDescription>Total du soldage</CardDescription>
              <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
                {preview ? formatCurrency(preview.total_debit) : "—"}
              </p>
              <p className="mt-1 text-xs text-muted">
                Débit = crédit ={" "}
                {preview ? formatCurrency(preview.total_credit) : "—"}
              </p>
            </Card>
            <Card>
              <CardDescription>Report à nouveau</CardDescription>
              <p className="mt-1 text-lg font-bold text-ink">
                {preview?.next_year
                  ? preview.next_year.name
                  : preview?.next_year_will_be_created
                  ? "Exercice suivant (créé par la clôture)"
                  : "—"}
              </p>
              <p className="mt-1 text-xs text-muted">
                {preview?.result_type === "profit"
                  ? "Bénéfice viré au compte 111 (report à nouveau créditeur)"
                  : preview?.result_type === "loss"
                  ? "Perte virée au compte 119 (report à nouveau débiteur)"
                  : "Rien à reporter (résultat nul)"}
              </p>
            </Card>
          </div>

          <Card className="overflow-x-auto p-0">
            <div className="border-b border-line px-4 py-3">
              <h2 className="font-semibold text-ink">
                Comptes de charges et de produits de {selectedYear.name}
              </h2>
              <p className="text-xs text-muted">
                Chaque solde est annulé par une ligne de sens inverse ; la
                contrepartie nette est le résultat de l&apos;exercice.
              </p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-2">Compte</th>
                  <th className="px-3 py-2">Libellé</th>
                  <th className="px-3 py-2">Classe</th>
                  <th className="px-3 py-2 text-right">Solde</th>
                  <th className="px-3 py-2 text-right">Ligne débit</th>
                  <th className="px-4 py-2 text-right">Ligne crédit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {previewQuery.isLoading && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-10 text-center text-faint"
                    >
                      Chargement…
                    </td>
                  </tr>
                )}
                {!previewQuery.isLoading &&
                  (preview?.lines.length ?? 0) === 0 && (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-4 py-10 text-center text-faint"
                      >
                        Aucun compte de charge ou de produit mouvementé sur cet
                        exercice — la clôture n&apos;aura pas d&apos;écriture à
                        générer.
                      </td>
                    </tr>
                  )}
                {preview?.lines.map((l) => (
                  <tr key={l.account_code} className="hover:bg-subtle">
                    <td className="px-4 py-2 font-mono text-xs font-semibold text-muted">
                      {l.account_code}
                    </td>
                    <td className="px-3 py-2 text-ink">
                      {l.account_name}
                    </td>
                    <td className="px-3 py-2 text-muted">{l.class_no}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-ink">
                      {formatCurrency(l.balance)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">
                      {l.debit ? formatCurrency(l.debit) : "—"}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-muted">
                      {l.credit ? formatCurrency(l.credit) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {selectedYear && (
        <Card className="border border-line">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-ink">
                {preview?.already_closed
                  ? "Exercice clôturé — écritures verrouillées"
                  : "Clôturer l'exercice"}
              </h2>
              <p className="text-xs text-muted">
                {preview?.already_closed
                  ? `Les écritures de ${selectedYear.name} ne peuvent plus être saisies ni publiées. Réouvrez l'exercice pour corriger.`
                  : `La clôture solde les charges et les produits de ${selectedYear.name}, reporte le résultat au report à nouveau, puis verrouille l'exercice.`}
              </p>
              {(preview?.closing_entry_reference ||
                preview?.opening_entry_reference) && (
                <p className="mt-2 font-mono text-xs text-muted">
                  {preview?.closing_entry_reference
                    ? `Clôture : ${preview.closing_entry_reference}`
                    : ""}
                  {preview?.closing_entry_reference &&
                  preview?.opening_entry_reference
                    ? " · "
                    : ""}
                  {preview?.opening_entry_reference
                    ? `Affectation : ${preview.opening_entry_reference}`
                    : ""}
                </p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {preview?.already_closed ? (
                <Button onClick={handleReopen} disabled={reopenYear.isPending}>
                  {reopenYear.isPending
                    ? "Réouverture…"
                    : "Réouvrir l'exercice"}
                </Button>
              ) : (
                <Button
                  onClick={handleClose}
                  disabled={closeYear.isPending || previewQuery.isLoading}
                  className="bg-gray-900 text-white hover:bg-gray-700"
                >
                  {closeYear.isPending ? "Clôture…" : "Clôturer l'exercice"}
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
