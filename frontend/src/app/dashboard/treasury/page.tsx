/**
 * Page Trésorerie — comptes de trésorerie (banque, caisse, mobile money).
 *
 * Chaque compte est rattaché à un compte du plan comptable OHADA (511 banque,
 * 531 caisse...) : c'est ce rattachement qui permet le rapprochement entre les
 * lignes d'un relevé et les écritures publiées. Le détail d'un compte
 * (relevés + rapprochement) est sur `/dashboard/treasury/[id]`.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmDeleteOptions, useConfirm } from "@/components/ui/confirm";
import {
  useCreateTreasuryAccount,
  useDeleteTreasuryAccount,
  useTreasuryAccounts,
} from "@/hooks/useTreasury";
import type { TreasuryAccountCreate } from "@/lib/types";

/** Message d'erreur renvoyé par l'API (`detail` FastAPI), sinon repli. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

/** Formulaire vierge — 511 (banque) par défaut, devise de la zone XOF. */
const EMPTY_FORM = {
  code: "",
  name: "",
  account_code: "511",
  bank_name: "",
  account_number: "",
  currency: "XOF",
};

export default function TreasuryPage() {
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [error, setError] = useState<string | null>(null);

  // Les comptes désactivés restent listés : ils conservent leurs relevés.
  const { data: accounts = [], isLoading } = useTreasuryAccounts(false);
  const createAccount = useCreateTreasuryAccount();
  const deleteAccount = useDeleteTreasuryAccount();
  const confirm = useConfirm();

  const setField = (key: keyof typeof EMPTY_FORM, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const payload: TreasuryAccountCreate = {
      code: form.code.trim(),
      name: form.name.trim(),
      account_code: form.account_code.trim(),
      bank_name: form.bank_name.trim() || null,
      account_number: form.account_number.trim() || null,
      currency: form.currency.trim().toUpperCase() || "XOF",
    };
    try {
      await createAccount.mutateAsync(payload);
      setForm({ ...EMPTY_FORM });
      setOpenCreate(false);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer le compte de trésorerie."));
    }
  };

  const handleDelete = async (id: number, name: string) => {
    setError(null);
    const { confirmed } = await confirm(confirmDeleteOptions(name));
    if (!confirmed) return;
    try {
      await deleteAccount.mutateAsync(id);
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de supprimer ce compte."));
    }
  };

  const activeCount = accounts.filter((a) => a.is_active).length;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Trésorerie</h1>
          <p className="text-sm text-muted">
            Comptes de banque, de caisse et de mobile money — relevés et
            rapprochement bancaire
          </p>
        </div>
        <Button
          onClick={() => {
            setOpenCreate((v) => !v);
            setError(null);
          }}
        >
          {openCreate ? "Fermer" : "Nouveau compte"}
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
          <CardDescription>Comptes de trésorerie</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {accounts.length}
          </p>
        </Card>
        <Card>
          <CardDescription>Comptes actifs</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-ink">
            {activeCount}
          </p>
        </Card>
        <Card>
          <CardDescription>Comptes désactivés</CardDescription>
          <p className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-muted">
            {accounts.length - activeCount}
          </p>
        </Card>
      </div>

      {openCreate && (
        <Card className="border border-line">
          <div className="mb-4 border-b border-line pb-3">
            <h2 className="font-semibold text-ink">
              Nouveau compte de trésorerie
            </h2>
          </div>
          <form
            onSubmit={handleCreate}
            className="grid grid-cols-1 gap-4 md:grid-cols-3"
          >
            <div>
              <label className="mb-1 block text-xs text-muted">
                Code interne *
              </label>
              <Input
                value={form.code}
                onChange={(e) => setField("code", e.target.value)}
                placeholder="ex. BQ1, CAI1, OM1"
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
                placeholder="ex. Compte bancaire SGCI, Caisse magasin"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Compte comptable *
              </label>
              <Input
                value={form.account_code}
                onChange={(e) => setField("account_code", e.target.value)}
                placeholder="511"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Banque</label>
              <Input
                value={form.bank_name}
                onChange={(e) => setField("bank_name", e.target.value)}
                placeholder="ex. SGCI"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">
                Numéro de compte
              </label>
              <Input
                value={form.account_number}
                onChange={(e) => setField("account_number", e.target.value)}
                placeholder="ex. CI93 0001 2345 6789"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Devise</label>
              <Input
                value={form.currency}
                onChange={(e) => setField("currency", e.target.value)}
                maxLength={3}
                placeholder="XOF"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 md:col-span-3">
              <Button type="submit" disabled={createAccount.isPending}>
                {createAccount.isPending ? "Création…" : "Créer le compte"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setOpenCreate(false);
                  setForm({ ...EMPTY_FORM });
                }}
              >
                Annuler
              </Button>
              <span className="text-xs text-muted">
                Le compte comptable doit exister dans le plan OHADA (511, 512,
                531…), sans quoi les lignes de relevé ne pourront pas être
                rapprochées.
              </span>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
          <div>
            <h2 className="font-semibold text-ink">Comptes</h2>
            <p className="text-xs text-muted">
              Cliquez sur « Relevés » pour saisir un relevé et rapprocher les
              écritures du compte.
            </p>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-4 py-2">Code</th>
              <th className="px-3 py-2">Libellé</th>
              <th className="px-3 py-2">Compte</th>
              <th className="px-3 py-2">Banque</th>
              <th className="px-3 py-2">N° de compte</th>
              <th className="px-3 py-2">Devise</th>
              <th className="px-3 py-2">Statut</th>
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
            {!isLoading && accounts.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-faint">
                  Aucun compte de trésorerie — créez un compte de banque, de
                  caisse ou de mobile money pour commencer.
                </td>
              </tr>
            )}
            {accounts.map((a) => (
              <tr key={a.id} className="hover:bg-subtle">
                <td className="px-4 py-2 font-mono text-xs font-semibold text-muted">
                  {a.code}
                </td>
                <td className="px-3 py-2 font-medium text-ink">{a.name}</td>
                <td className="px-3 py-2 font-mono text-xs text-muted">
                  {a.account_code}
                </td>
                <td className="px-3 py-2 text-muted">{a.bank_name ?? "—"}</td>
                <td className="px-3 py-2 text-muted">
                  {a.account_number ?? "—"}
                </td>
                <td className="px-3 py-2 text-muted">{a.currency}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      a.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-subtle text-muted"
                    }`}
                  >
                    {a.is_active ? "actif" : "désactivé"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center justify-end gap-3">
                    <Link
                      href={`/dashboard/treasury/${a.id}`}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      Relevés
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(a.id, a.name)}
                      disabled={deleteAccount.isPending}
                      className="text-sm text-red-600 hover:underline disabled:opacity-50"
                    >
                      Supprimer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
