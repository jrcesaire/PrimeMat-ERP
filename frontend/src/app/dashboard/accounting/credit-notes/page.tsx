"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  useCreditNotes,
  useCreateCreditNote,
  useIssueCreditNote,
  useApplyCreditNote,
} from "@/hooks/useAccounting";
import type {
  CreditNote,
  CreditNoteCreate,
  CreditNoteIssue,
  CreditNoteApply,
} from "@/lib/types";

type CnStatus = "draft" | "issued" | "applied";
type CnType = "customer" | "supplier";

const STATUS_LABEL: Record<string, { label: string; className: string }> = {
  draft: { label: "Brouillon", className: "bg-gray-100 text-gray-700" },
  issued: { label: "Émis", className: "bg-blue-100 text-blue-800" },
  applied: { label: "Imputé", className: "bg-green-100 text-green-800" },
};
const TYPE_LABEL: Record<string, string> = { customer: "Client", supplier: "Fournisseur" };

function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return fallback;
}

export default function CreditNotesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [openCreate, setOpenCreate] = useState(false);
  const [openApply, setOpenApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [cnType, setCnType] = useState<CnType>("customer");
  const [partnerId, setPartnerId] = useState("");
  const [amountUntaxed, setAmountUntaxed] = useState("");
  const [taxAmount, setTaxAmount] = useState("");
  const [amountTotal, setAmountTotal] = useState("");
  const [creditDate, setCreditDate] = useState("");
  const [reason, setReason] = useState("");

  const [applyId, setApplyId] = useState("");
  const [applyInvoiceId, setApplyInvoiceId] = useState("");
  const [applyAmount, setApplyAmount] = useState("");

  const { data: notes = [], isLoading } = useCreditNotes({
    status: statusFilter || undefined,
    type: typeFilter || undefined,
  });
  const createCn = useCreateCreditNote();
  const issueCn = useIssueCreditNote();
  const applyCn = useApplyCreditNote();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const payload: CreditNoteCreate = {
      type: cnType,
      partner_id: partnerId ? Number(partnerId) : undefined,
      amount_untaxed: amountUntaxed ? Number(amountUntaxed) : 0,
      tax_amount: taxAmount ? Number(taxAmount) : 0,
      amount_total: amountTotal ? Number(amountTotal) : 0,
      credit_date: creditDate || undefined,
      reason: reason || undefined,
    };
    try {
      await createCn.mutateAsync(payload);
      setOpenCreate(false);
      setCnType("customer");
      setPartnerId("");
      setAmountUntaxed("");
      setTaxAmount("");
      setAmountTotal("");
      setCreditDate("");
      setReason("");
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible de créer l'avoir."));
    }
  };

  const handleIssue = async (id: number, reference: string) => {
    setError(null);
    try {
      await issueCn.mutateAsync({ id, data: {} });
    } catch (err: unknown) {
      setError(errMsg(err, `Impossible d'émettre l'avoir ${reference}.`));
    }
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!applyId || !applyInvoiceId) {
      setError("Choisissez un avoir et une facture.");
      return;
    }
    try {
      await applyCn.mutateAsync({
        id: Number(applyId),
        data: {
          invoice_id: Number(applyInvoiceId),
          amount_to_apply: applyAmount ? Number(applyAmount) : undefined,
        },
      });
      setOpenApply(false);
      setApplyId("");
      setApplyInvoiceId("");
      setApplyAmount("");
    } catch (err: unknown) {
      setError(errMsg(err, "Impossible d'imputer l'avoir."));
    }
  };

  const total = notes.reduce((s, n) => s + (n.amount_total ?? 0), 0);
  const issuedTotal = notes
    .filter((n) => n.status === "issued")
    .reduce((s, n) => s + (n.amount_total ?? 0), 0);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Avoirs / notes de crédit</h1>
          <p className="text-sm text-gray-600">
            Notes de crédit client et fournisseur (SYSCOHADA / OHADA)
          </p>
        </div>
        <Button
          onClick={() => setOpenCreate(true)}
          disabled={createCn.isPending}
        >
          {createCn.isPending ? "Création…" : "Nouvel avoir"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className="font-medium text-gray-700">Filtres :</span>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Statut</span>
            {["", "draft", "issued", "applied"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1 text-xs rounded border ${
                  statusFilter === s
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {s ? STATUS_LABEL[s]?.label ?? s : "Tous"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Type</span>
            {["", "customer", "supplier"].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`px-3 py-1 text-xs rounded border ${
                  typeFilter === t
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {t ? TYPE_LABEL[t] : "Tous"}
              </button>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-xs text-gray-500">Total avoirs</p>
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(total)} ({notes.length})
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500">À imputer (émis)</p>
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(issuedTotal)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-gray-500">Déjà imputés</p>
          <p className="text-lg font-semibold text-gray-900">
            {notes.filter((n) => n.status === "applied").length}
          </p>
        </Card>
      </div>
      <Card className="overflow-hidden">
        <div className="border-b border-gray-100 bg-gray-50 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-900">Liste des avoirs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="px-4 py-3 font-mono">Référence</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Partenaire</th>
                <th className="px-4 py-3 text-right">HT</th>
                <th className="px-4 py-3 text-right">TVA</th>
                <th className="px-4 py-3 text-right">TTC</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-sm text-gray-400">
                    Chargement…
                  </td>
                </tr>
              ) : notes.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-sm text-gray-400">
                    Aucun avoir trouvé.
                  </td>
                </tr>
              ) : (
                notes.map((n) => (
                  <tr key={n.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-medium text-gray-900">
                      {n.reference}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {formatDate(n.credit_date)}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {TYPE_LABEL[n.type]}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {n.partner_id ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-600">
                      {formatCurrency(n.amount_untaxed)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-600">
                      {formatCurrency(n.tax_amount)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">
                      {formatCurrency(n.amount_total)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_LABEL[n.status]?.className ?? "bg-gray-100 text-gray-700"}`}>
                        {STATUS_LABEL[n.status]?.label ?? n.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {n.status === "draft" && (
                          <Button
                            size="sm"
                            onClick={() => handleIssue(n.id, n.reference)}
                            disabled={issueCn.isPending}
                            className="h-7 w-7 text-green-600 hover:bg-green-50 disabled:opacity-50"
                            title={`Émettre ${n.reference}`}
                          >
                            ✓
                          </Button>
                        )}
                        {n.status === "issued" && (
                          <Button
                            size="sm"
                            onClick={() => {
                              setApplyId(String(n.id));
                              setApplyInvoiceId("");
                              setApplyAmount("");
                              setOpenApply(true);
                            }}
                            disabled={applyCn.isPending}
                            className="h-7 w-7 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                            title={`Imputer ${n.reference}`}
                          >
                            ⇨
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
      {openCreate && (
        <Card className="border border-gray-200">
          <div className="border-b border-gray-100 px-4 py-3 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Nouvel avoir (brouillon)</h2>
            <Button
              size="sm"
              onClick={() => setOpenCreate(false)}
              className="text-gray-500 hover:text-gray-900"
            >
              Fermer
            </Button>
          </div>
          <form onSubmit={handleCreate} className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={cnType}
                onChange={(e) => setCnType(e.target.value as CnType)}
                className="w-full h-10 rounded-md border border-gray-300 bg-white px-3 text-sm"
              >
                <option value="customer">Client</option>
                <option value="supplier">Fournisseur</option>
              </select>
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">ID partenaire</label>
              <Input
                value={partnerId}
                onChange={(e) => setPartnerId(e.target.value)}
                placeholder="ex. 42"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Montant HT</label>
              <Input
                type="number"
                value={amountUntaxed}
                onChange={(e) => setAmountUntaxed(e.target.value)}
                placeholder="0,00"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">TVA</label>
              <Input
                type="number"
                value={taxAmount}
                onChange={(e) => setTaxAmount(e.target.value)}
                placeholder="0,00"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Montant TTC</label>
              <Input
                type="number"
                value={amountTotal}
                onChange={(e) => setAmountTotal(e.target.value)}
                placeholder="0,00"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <Input
                type="date"
                value={creditDate}
                onChange={(e) => setCreditDate(e.target.value)}
              />
            </div>
            <div className="col-span-4">
              <label className="block text-xs text-gray-500 mb-1">Motif</label>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Retour marchandise, facture erronée…"
              />
            </div>
            <div className="col-span-4 flex items-end gap-2">
              <Button type="button" onClick={() => setOpenCreate(false)} variant="outline">
                Annuler
              </Button>
              <Button type="submit" disabled={createCn.isPending}>
                {createCn.isPending ? "Création…" : "Créer l'avoir"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {openApply && (
        <Card className="border border-gray-200">
          <div className="border-b border-gray-100 px-4 py-3 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">
              Imputer un avoir sur une facture
            </h2>
            <Button
              size="sm"
              onClick={() => setOpenApply(false)}
              className="text-gray-500 hover:text-gray-900"
            >
              Fermer
            </Button>
          </div>
          <form onSubmit={handleApply} className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Avoir (ID)</label>
              <Input value={applyId} readOnly className="bg-gray-50" />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">Facture (ID)</label>
              <Input
                value={applyInvoiceId}
                onChange={(e) => setApplyInvoiceId(e.target.value)}
                placeholder="ex. 105"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">
                Montant à imputer
              </label>
              <Input
                type="number"
                value={applyAmount}
                onChange={(e) => setApplyAmount(e.target.value)}
                placeholder="vide = total"
              />
            </div>
            <div className="col-span-1 md:col-span-1">
              <label className="block text-xs text-gray-500 mb-1">‎</label>
              <span className="text-xs text-gray-500">
                Par défaut le montant total de l’avoir est imputé (plafonné par le solde de la facture).
              </span>
            </div>
            <div className="col-span-4 flex items-end gap-2">
              <Button type="button" onClick={() => setOpenApply(false)} variant="outline">
                Annuler
              </Button>
              <Button type="submit" disabled={applyCn.isPending}>
                {applyCn.isPending ? "Imputation…" : "Imputer"}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
