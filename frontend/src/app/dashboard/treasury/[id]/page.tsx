/**
 * Page détail d'un compte de trésorerie — relevés bancaires et rapprochement.
 *
 * Trois blocs :
 * 1. **État de rapprochement** : solde comptable (écritures publiées sur le
 *    compte rattaché) vs solde du dernier relevé, et montant déjà rapproché ;
 * 2. **Relevés** : saisie d'un relevé (soldes d'ouverture / clôture), lignes
 *    au montant signé, clôture qui verrouille le relevé ;
 * 3. **Rapprochement** : appariement automatique (montant identique à ±5 jours)
 *    ou manuel, ligne de relevé ↔ ligne d'écriture de trésorerie.
 *
 * Le backend refuse d'apparier des montants différents : la liste déroulante
 * présente donc d'abord les écritures de même montant, et affiche le montant
 * des autres pour éviter les allers-retours.
 */
"use client";
import { NumberInput } from "@/components/ui/number-input";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmCloseOptions, useConfirm } from "@/components/ui/confirm";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  useAddStatementLine,
  useAutoReconcile,
  useCloseStatement,
  useCreateStatement,
  useDeleteStatementLine,
  useReconcileLine,
  useReconciliationReport,
  useStatements,
  useTreasuryAccounts,
  useUnreconcileLine,
} from "@/hooks/useTreasury";
import type { UnreconciledEntryLine } from "@/lib/types";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

/** Date du jour au format `YYYY-MM-DD` (valeur par défaut des formulaires). */
function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Écritures candidates pour une ligne de relevé, triées par proximité de
 * montant (montant signé identique en tête) puis par date.
 */
function sortCandidates(
  candidates: UnreconciledEntryLine[],
  amount: number,
): UnreconciledEntryLine[] {
  return [...candidates].sort((a, b) => {
    const gapA = Math.abs(a.amount - amount);
    const gapB = Math.abs(b.amount - amount);
    if (gapA !== gapB) return gapA - gapB;
    return a.entry_date.localeCompare(b.entry_date);
  });
}

/** Formulaire « nouveau relevé » — daté du jour par défaut. */
const newStatementForm = () => ({
  label: "",
  statement_date: todayISO(),
  opening_balance: "",
  closing_balance: "",
});

/** Formulaire « nouvelle ligne de relevé » — daté du jour par défaut. */
const newLineForm = () => ({
  line_date: todayISO(),
  label: "",
  amount: "",
});

export default function TreasuryAccountPage() {
  const params = useParams<{ id: string }>();
  const accountId = Number(params?.id) || null;

  const { data: accounts = [] } = useTreasuryAccounts(false);
  const { data: statements = [], isLoading: loadingStatements } =
    useStatements(accountId);
  const reportQuery = useReconciliationReport(accountId);
  const report = reportQuery.data ?? null;

  const createStatement = useCreateStatement();
  const addLine = useAddStatementLine();
  const removeLine = useDeleteStatementLine();
  const closeStatement = useCloseStatement();
  const autoReconcile = useAutoReconcile();
  const reconcileLine = useReconcileLine();
  const unreconcileLine = useUnreconcileLine();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedStatementId, setSelectedStatementId] = useState<number | null>(
    null,
  );
  const [openNewStatement, setOpenNewStatement] = useState(false);
  const [openAddLine, setOpenAddLine] = useState(false);
  const [stForm, setStForm] = useState(newStatementForm());
  const [lnForm, setLnForm] = useState(newLineForm());
  // Ligne de relevé → écriture choisie dans la liste déroulante.
  const [chosenEntry, setChosenEntry] = useState<Record<number, string>>({});

  // Sélectionne le relevé le plus récent dès qu'ils sont chargés.
  useEffect(() => {
    if (selectedStatementId === null && statements.length > 0) {
      setSelectedStatementId(statements[0].id);
    }
  }, [statements, selectedStatementId]);

  const account = accounts.find((a) => a.id === accountId) ?? null;
  const statement =
    statements.find((s) => s.id === selectedStatementId) ?? null;
  const isClosed = statement?.status === "closed";
  const candidates = report?.unreconciled_entry_lines ?? [];
  /** Écart entre le solde comptable et le solde du dernier relevé saisi. */
  const variance = report
    ? report.accounting_balance - report.statement_balance
    : 0;
  const reconciledCount = statement
    ? statement.lines.filter((l) => l.entry_line_id !== null).length
    : 0;

  const handleCreateStatement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountId) return;
    setError(null);
    setNotice(null);
    try {
      const created = await createStatement.mutateAsync({
        accountId,
        data: {
          label: stForm.label.trim(),
          statement_date: stForm.statement_date,
          opening_balance: Number(stForm.opening_balance || 0),
          closing_balance: Number(stForm.closing_balance || 0),
        },
      });
      setStForm(newStatementForm());
      setOpenNewStatement(false);
      setSelectedStatementId(created.id);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer le relevé."));
    }
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!statement) return;
    setError(null);
    setNotice(null);
    try {
      await addLine.mutateAsync({
        statementId: statement.id,
        data: {
          line_date: lnForm.line_date,
          label: lnForm.label.trim(),
          amount: Number(lnForm.amount),
        },
      });
      setLnForm(newLineForm());
      setOpenAddLine(false);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible d'ajouter la ligne au relevé."));
    }
  };

  const handleAutoReconcile = async () => {
    if (!statement) return;
    setError(null);
    setNotice(null);
    try {
      const result = await autoReconcile.mutateAsync(statement.id);
      setNotice(result.message);
    } catch (err: unknown) {
      setError(errMsg(err, "Rapprochement automatique impossible."));
    }
  };

  const handleReconcile = async (lineId: number) => {
    const entryLineId = Number(chosenEntry[lineId] ?? 0);
    if (!entryLineId) {
      setError("Sélectionnez d'abord une écriture à rapprocher.");
      return;
    }
    setError(null);
    setNotice(null);
    try {
      await reconcileLine.mutateAsync({ lineId, entryLineId });
      setChosenEntry((prev) => {
        const next = { ...prev };
        delete next[lineId];
        return next;
      });
    } catch (err: unknown) {
      setError(errMsg(err, "Rapprochement impossible."));
    }
  };

  const handleUnreconcile = async (lineId: number) => {
    setError(null);
    setNotice(null);
    try {
      await unreconcileLine.mutateAsync(lineId);
    } catch (err: unknown) {
      setError(errMsg(err, "Retrait du rapprochement impossible."));
    }
  };

  const handleDeleteLine = async (lineId: number) => {
    setError(null);
    setNotice(null);
    try {
      await removeLine.mutateAsync(lineId);
    } catch (err: unknown) {
      setError(errMsg(err, "Suppression de la ligne impossible."));
    }
  };

  const handleCloseStatement = async () => {
    if (!statement) return;
    const { confirmed } = await confirm(confirmCloseOptions(statement.label));
    if (!confirmed) return;
    setError(null);
    setNotice(null);
    try {
      await closeStatement.mutateAsync(statement.id);
      setNotice(
        `Relevé « ${statement.label} » clôturé — lignes verrouillées.`,
      );
    } catch (err: unknown) {
      setError(errMsg(err, "Clôture du relevé impossible."));
    }
  };


  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/dashboard/treasury"
          className="text-sm text-muted hover:text-ink"
        >
          ← Trésorerie
        </Link>
        <h1 className="mt-2 text-[28px] font-semibold leading-tight text-ink">
          {account ? account.name : `Compte #${accountId ?? "?"}`}
        </h1>
        <p className="text-sm text-muted">
          {account
            ? `Compte comptable ${account.account_code} · ${account.code}${
                account.bank_name ? ` · ${account.bank_name}` : ""
              } · ${account.currency}`
            : "Chargement du compte…"}
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

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardDescription>Solde comptable</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {report
              ? formatCurrency(report.accounting_balance)
              : "—"}
          </p>
          <p className="mt-1 text-xs text-muted">
            Écritures publiées sur le compte {report?.account_code ?? "—"}
          </p>
        </Card>
        <Card>
          <CardDescription>Solde du dernier relevé</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {report ? formatCurrency(report.statement_balance) : "—"}
          </p>
          <p className="mt-1 text-xs text-muted">
            Solde de clôture du relevé le plus récent
          </p>
        </Card>
        <Card>
          <CardDescription>Déjà rapproché</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {report ? formatCurrency(report.reconciled_amount) : "—"}
          </p>
          <p className="mt-1 text-xs text-muted">
            Cumul des lignes de relevé appariées
          </p>
        </Card>
        <Card>
          <CardDescription>Écart comptable / relevé</CardDescription>
          <p
            className={`mt-1 text-[28px] font-semibold leading-tight tabular-nums ${
              Math.abs(variance) < 0.01 ? "text-green-600" : "text-amber-600"
            }`}
          >
            {report ? formatCurrency(variance) : "—"}
          </p>
          <p className="mt-1 text-xs text-muted">
            {report && Math.abs(variance) < 0.01
              ? "Soldes concordants"
              : `${report?.unreconciled_lines.length ?? 0} ligne(s) de relevé et ${
                  report?.unreconciled_entry_lines.length ?? 0
                } écriture(s) en attente`}
          </p>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
          <div>
            <h2 className="font-semibold text-ink">Relevés bancaires</h2>
            <p className="text-xs text-muted">
              Saisissez les lignes du relevé, puis rapprochez-les des écritures
              du compte {account?.account_code ?? ""}.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setOpenNewStatement((v) => !v);
              setError(null);
            }}
          >
            {openNewStatement ? "Fermer" : "Nouveau relevé"}
          </Button>
        </div>

        {openNewStatement && (
          <form
            onSubmit={handleCreateStatement}
            className="grid grid-cols-1 gap-4 border-b border-line bg-subtle px-4 py-4 md:grid-cols-4"
          >
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs text-muted">
                Libellé *
              </label>
              <Input
                value={stForm.label}
                onChange={(e) =>
                  setStForm((p) => ({ ...p, label: e.target.value }))
                }
                placeholder="ex. Relevé bancaire octobre 2026"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Date du relevé *
              </label>
              <Input
                type="date"
                value={stForm.statement_date}
                onChange={(e) =>
                  setStForm((p) => ({ ...p, statement_date: e.target.value }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Solde d&apos;ouverture
              </label>
              <NumberInput
                min={0}
                step="0.01"
                value={stForm.opening_balance}
                onChange={(v, raw) => setStForm((p) => ({ ...p, opening_balance: (raw === "" ? "" : String(v)) }))}
                placeholder="0"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Solde de clôture
              </label>
              <NumberInput
                min={0}
                step="0.01"
                value={stForm.closing_balance}
                onChange={(v, raw) => setStForm((p) => ({ ...p, closing_balance: (raw === "" ? "" : String(v)) }))}
                placeholder="0"
              />
            </div>
            <div className="flex items-end gap-2 md:col-span-4">
              <Button type="submit" disabled={createStatement.isPending}>
                {createStatement.isPending ? "Création…" : "Créer le relevé"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setOpenNewStatement(false);
                  setStForm(newStatementForm());
                }}
              >
                Annuler
              </Button>
            </div>
          </form>
        )}

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Date</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2 text-right">Ouverture</th>
              <th className="px-3 py-2 text-right">Clôture</th>
              <th className="px-3 py-2 text-right">Lignes</th>
              <th className="px-3 py-2 text-right">Rapprochées</th>
              <th className="px-3 py-2">Statut</th>
              <th className="px-4 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loadingStatements && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-faint">
                  Chargement…
                </td>
              </tr>
            )}
            {!loadingStatements && statements.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-faint">
                  Aucun relevé — créez un relevé pour saisir ses lignes et
                  commencer le rapprochement.
                </td>
              </tr>
            )}
            {statements.map((s) => {
              const done = s.lines.filter(
                (l) => l.entry_line_id !== null,
              ).length;
              const isSelected = s.id === selectedStatementId;
              return (
                <tr
                  key={s.id}
                  className={isSelected ? "bg-primary/5" : "hover:bg-subtle"}
                >
                  <td className="px-4 py-2 tabular-nums text-muted">
                    {formatDate(s.statement_date)}
                  </td>
                  <td className="px-3 py-2 font-medium text-ink">
                    {s.label}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-muted">
                    {formatCurrency(s.opening_balance)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-muted">
                    {formatCurrency(s.closing_balance)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-muted">
                    {s.lines.length}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    <span
                      className={
                        s.lines.length > 0 && done === s.lines.length
                          ? "font-semibold text-green-700"
                          : "text-muted"
                      }
                    >
                      {done}/{s.lines.length}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        s.status === "closed"
                          ? "bg-gray-200 text-muted"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {s.status === "closed" ? "clôturé" : "ouvert"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedStatementId(s.id)}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      {isSelected ? "Sélectionné" : "Rapprocher"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card className="overflow-x-auto p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h2 className="font-semibold text-ink">
              Rapprochement{statement ? ` — ${statement.label}` : ""}
            </h2>
            <p className="text-xs text-muted">
              {statement
                ? `${reconciledCount}/${statement.lines.length} ligne(s) rapprochée(s). L'appariement automatique exige un montant identique à ±5 jours.`
                : "Sélectionnez un relevé ci-dessus pour rapprocher ses lignes."}
            </p>
          </div>
          {statement && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                onClick={handleAutoReconcile}
                disabled={isClosed || autoReconcile.isPending}
                title={
                  isClosed
                    ? "Relevé clôturé : rapprochement impossible"
                    : "Apparie automatiquement les montants identiques"
                }
              >
                {autoReconcile.isPending
                  ? "Rapprochement…"
                  : "Rapprochement automatique"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setOpenAddLine((v) => !v);
                  setError(null);
                }}
                disabled={isClosed}
              >
                {openAddLine ? "Fermer" : "Ajouter une ligne"}
              </Button>
              <Button
                onClick={handleCloseStatement}
                disabled={isClosed || closeStatement.isPending}
              >
                {isClosed ? "Relevé clôturé" : "Clôturer le relevé"}
              </Button>
            </div>
          )}
        </div>

        {statement && openAddLine && (
          <form
            onSubmit={handleAddLine}
            className="grid grid-cols-1 gap-4 border-b border-line bg-subtle px-4 py-4 md:grid-cols-4"
          >
            <div>
              <label className="mb-1 block text-xs text-muted">
                Date de l&apos;opération *
              </label>
              <Input
                type="date"
                value={lnForm.line_date}
                onChange={(e) =>
                  setLnForm((p) => ({ ...p, line_date: e.target.value }))
                }
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs text-muted">
                Libellé *
              </label>
              <Input
                value={lnForm.label}
                onChange={(e) =>
                  setLnForm((p) => ({ ...p, label: e.target.value }))
                }
                placeholder="ex. Virement client, frais bancaires…"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Montant signé *
              </label>
              <NumberInput
                step="0.01"
                value={lnForm.amount}
                onChange={(v, raw) => setLnForm((p) => ({ ...p, amount: (raw === "" ? "" : String(v)) }))}
                placeholder="ex. 250000 ou -15000"
                required
              />
            </div>
            <div className="flex items-end gap-2 md:col-span-4">
              <Button type="submit" disabled={addLine.isPending}>
                {addLine.isPending ? "Ajout…" : "Ajouter la ligne"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setOpenAddLine(false);
                  setLnForm(newLineForm());
                }}
              >
                Annuler
              </Button>
              <span className="text-xs text-muted">
                Positif = encaissement, négatif = décaissement (même convention
                que le relevé bancaire).
              </span>
            </div>
          </form>
        )}

        {statement && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-2">Date</th>
                <th className="px-3 py-2">Libellé du relevé</th>
                <th className="px-3 py-2 text-right">Montant</th>
                <th className="px-3 py-2">Écriture rapprochée</th>
                <th className="px-3 py-2">État</th>
                <th className="px-4 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {statement.lines.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-faint"
                  >
                    Aucune ligne dans ce relevé — ajoutez les opérations du
                    relevé bancaire.
                  </td>
                </tr>
              )}
              {statement.lines.map((l) => {
                const reconciled = l.entry_line_id !== null;
                const options = sortCandidates(candidates, l.amount);
                return (
                  <tr key={l.id} className="hover:bg-subtle">
                    <td className="px-4 py-2 tabular-nums text-muted">
                      {formatDate(l.line_date)}
                    </td>
                    <td className="px-3 py-2 text-ink">{l.label}</td>
                    <td
                      className={`px-3 py-2 text-right font-semibold tabular-nums ${
                        l.amount < 0 ? "text-red-600" : "text-green-700"
                      }`}
                    >
                      {formatCurrency(l.amount)}
                    </td>
                    <td className="px-3 py-2 text-muted">
                      {reconciled ? (
                        <span className="font-mono text-xs">
                          écriture #{l.entry_line_id}
                          {l.reconciled_at
                            ? ` · ${formatDate(l.reconciled_at)}`
                            : ""}
                        </span>
                      ) : options.length === 0 ? (
                        <span className="text-xs text-faint">
                          Aucune écriture en attente sur ce compte
                        </span>
                      ) : (
                        <select
                          value={chosenEntry[l.id] ?? ""}
                          onChange={(e) =>
                            setChosenEntry((prev) => ({
                              ...prev,
                              [l.id]: e.target.value,
                            }))
                          }
                          disabled={isClosed}
                          className="h-9 w-full rounded-md border border-line bg-surface px-2 text-sm disabled:opacity-50"
                        >
                          <option value="">— choisir une écriture —</option>
                          {options.map((c) => (
                            <option key={c.entry_line_id} value={c.entry_line_id}>
                              {c.reference} · {formatDate(c.entry_date)} ·{" "}
                              {formatCurrency(c.amount)}
                              {c.label ? ` · ${c.label}` : ""}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          reconciled
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {reconciled ? "rapprochée" : "en attente"}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center justify-end gap-3">
                        {reconciled ? (
                          <button
                            type="button"
                            onClick={() => handleUnreconcile(l.id)}
                            disabled={isClosed || unreconcileLine.isPending}
                            className="text-sm text-muted hover:underline disabled:opacity-50"
                          >
                            Retirer
                          </button>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => handleReconcile(l.id)}
                              disabled={isClosed || reconcileLine.isPending}
                              className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
                            >
                              Rapprocher
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteLine(l.id)}
                              disabled={isClosed || removeLine.isPending}
                              className="text-sm text-red-600 hover:underline disabled:opacity-50"
                            >
                              Supprimer
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {!statement && (
          <p className="px-4 py-10 text-center text-sm text-faint">
            Aucun relevé sélectionné.
          </p>
        )}
      </Card>

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-line px-4 py-3">
          <h2 className="font-semibold text-ink">
            Écritures de trésorerie non rapprochées
          </h2>
          <p className="text-xs text-muted">
            Lignes publiées sur le compte {report?.account_code ?? "—"} qui
            n&apos;ont encore été appariées à aucune ligne de relevé.
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Référence</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-4 py-2 text-right">Montant</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {reportQuery.isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-faint">
                  Chargement…
                </td>
              </tr>
            )}
            {!reportQuery.isLoading && candidates.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-faint">
                  Toutes les écritures de ce compte sont rapprochées.
                </td>
              </tr>
            )}
            {candidates.map((c) => (
              <tr key={c.entry_line_id} className="hover:bg-subtle">
                <td className="px-4 py-2 font-mono text-xs font-semibold text-muted">
                  {c.reference}
                </td>
                <td className="px-3 py-2 tabular-nums text-muted">
                  {formatDate(c.entry_date)}
                </td>
                <td className="px-3 py-2 text-muted">{c.label ?? "—"}</td>
                <td
                  className={`px-4 py-2 text-right font-semibold tabular-nums ${
                    c.amount < 0 ? "text-red-600" : "text-green-700"
                  }`}
                >
                  {formatCurrency(c.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
