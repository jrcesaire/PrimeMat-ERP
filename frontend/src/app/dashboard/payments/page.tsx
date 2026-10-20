/**
 * Page Paiements — encaissements, reçus imprimables.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  usePayments,
  useCreatePayment,
  useBackToDraftPayment,
  useConfirmPayment,
  useDeletePayment,
  useInvoices,
  type Payment,
} from "@/hooks/useOperations";
import { useClients } from "@/hooks/useCRM";
import { usePermission } from "@/hooks/useAuth";
import {
  useConfirm,
  confirmBackToDraftOptions,
  confirmDeleteOptions,
} from "@/components/ui/confirm";
import { printReceipt } from "@/lib/api/pdf";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";

function apiDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  mobile_money: "Mobile Money",
  bank: "Virement",
  check: "Chèque",
};

export default function PaymentsPage() {
  const router = useRouter();
  const { data: payments = [], isLoading } = usePayments();
  const { data: invoices = [] } = useInvoices();
  const { data: clients = [] } = useClients();
  const createPayment = useCreatePayment();
  const backToDraft = useBackToDraftPayment();
  const confirmPayment = useConfirmPayment();
  const deletePayment = useDeletePayment();
  const can = usePermission();
  const canEditPayment = can("payment:edit");
  const canDeletePayment = can("payment:delete");
  const confirm = useConfirm();

  const [invoiceId, setInvoiceId] = useState<number | null>(null);
  const [method, setMethod] = useState("cash");
  const [amount, setAmount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Cascade de suppression : remise au brouillon → suppression
  const handleBackToDraft = async (p: Payment) => {
    const { confirmed } = await confirm({
      ...confirmBackToDraftOptions(p.reference),
      description:
        "Le montant sera retiré de la facture liée et son écriture comptable supprimée. Vous pourrez confirmer à nouveau.",
    });
    if (!confirmed) {
      return;
    }
    try {
      await backToDraft.mutateAsync(p.id);
    } catch (err: unknown) {
      alert(apiDetail(err, "Erreur lors de la remise au brouillon"));
    }
  };

  const handleConfirmPayment = async (p: Payment) => {
    try {
      await confirmPayment.mutateAsync(p.id);
    } catch (err: unknown) {
      alert(apiDetail(err, "Erreur lors de la confirmation"));
    }
  };

  const handleDeletePayment = async (p: Payment) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(p.reference),
    );
    if (!confirmed) {
      return;
    }
    try {
      await deletePayment.mutateAsync(p.id);
    } catch (err: unknown) {
      alert(apiDetail(err, "Erreur lors de la suppression"));
    }
  };

  // Factures non soldées
  const unpaid = invoices.filter((i) => i.amount_total - i.paid_amount > 1);

  const handleCreate = async () => {
    setError(null);
    const inv = invoices.find((i) => i.id === invoiceId);
    if (!inv) return setError("Choisissez une facture.");
    if (amount <= 0) return setError("Montant requis.");
    try {
      await createPayment.mutateAsync({
        partner_id: inv.partner_id,
        invoice_id: inv.id,
        method,
        amount,
      });
      setInvoiceId(null);
      setAmount(0);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de l'encaissement");
    }
  };

  const partnerName = (p: Payment) =>
    clients.find((c) => c.id === p.partner_id)?.name ?? `#${p.partner_id ?? "?"}`;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Paiements</h1>
        <p className="text-sm text-gray-600">Encaissements clients</p>
      </div>

      {/* Nouveau paiement */}
      <Card className="space-y-3 p-4">
        <h2 className="font-semibold text-gray-800">Encaisser un paiement</h2>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={invoiceId ?? ""}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null;
              setInvoiceId(id);
              const inv = invoices.find((i) => i.id === id);
              if (inv) setAmount(Math.max(inv.amount_total - inv.paid_amount, 0));
            }}
          >
            <option value="">— Facture —</option>
            {unpaid.map((i) => (
              <option key={i.id} value={i.id}>
                {i.reference} — reste {formatCurrency(i.amount_total - i.paid_amount)}
              </option>
            ))}
          </select>
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            <option value="cash">Espèces</option>
            <option value="mobile_money">Mobile Money</option>
            <option value="bank">Virement</option>
            <option value="check">Chèque</option>
          </select>
          <Input
            type="number"
            min={0}
            value={amount || ""}
            onChange={(e) => setAmount(Number(e.target.value))}
            placeholder="Montant"
          />
          <Button onClick={handleCreate} disabled={createPayment.isPending}>
            {createPayment.isPending ? "…" : "Encaisser"}
          </Button>
        </div>
        {unpaid.length === 0 && (
          <p className="text-xs text-gray-400">Aucune facture en attente de paiement.</p>
        )}
      </Card>

      {/* Liste */}
      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : payments.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucun paiement.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Référence</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">Mode</th>
                <th className="px-4 py-3 text-right">Montant</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => router.push(`/dashboard/payments/${p.id}`)}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">
                    {p.reference}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(p.payment_date)}</td>
                  <td className="px-4 py-3">{partnerName(p)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3">{METHOD_LABELS[p.method] ?? p.method}</td>
                  <td className="px-4 py-3 text-right font-semibold text-green-700">
                    {formatCurrency(p.amount)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {p.status !== "draft" && canEditPayment && (
                        <button
                          title={`Remettre ${p.reference} au brouillon`}
                          aria-label={`Remettre ${p.reference} au brouillon`}
                          disabled={backToDraft.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleBackToDraft(p);
                          }}
                          className="inline-flex h-8 items-center rounded-md px-2 text-xs text-amber-700 hover:bg-amber-50 disabled:opacity-50"
                        >
                          Brouillon
                        </button>
                      )}
                      {p.status === "draft" && canEditPayment && (
                        <button
                          title={`Confirmer ${p.reference}`}
                          aria-label={`Confirmer ${p.reference}`}
                          disabled={confirmPayment.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleConfirmPayment(p);
                          }}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-green-600 hover:bg-green-50 disabled:opacity-50"
                        >
                          ✓
                        </button>
                      )}
                      {p.status === "draft" && canDeletePayment && (
                        <button
                          title={`Supprimer ${p.reference}`}
                          aria-label={`Supprimer ${p.reference}`}
                          disabled={deletePayment.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeletePayment(p);
                          }}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          🗑
                        </button>
                      )}
                      <button
                        title={`Imprimer le reçu ${p.reference}`}
                        aria-label={`Imprimer le reçu ${p.reference}`}
                        disabled={p.status === "draft"}
                        onClick={(e) => {
                          e.stopPropagation();
                          printReceipt(p.id).catch(() => alert("Impossible de générer le reçu."));
                        }}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-gray-600 hover:bg-gray-100 disabled:opacity-40"
                      >
                        🖨
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
