/**
 * Page Facturation — factures, facturation depuis commande, impression.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useInvoices, useCreateInvoiceFromOrder } from "@/hooks/useOperations";
import { useOrders } from "@/hooks/useSales";
import { printInvoice } from "@/lib/api/pdf";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";

export default function InvoicingPage() {
  const router = useRouter();
  const { data: invoices = [], isLoading } = useInvoices();
  const { data: orders = [] } = useOrders();
  const createInvoice = useCreateInvoiceFromOrder();

  const [orderId, setOrderId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Commandes confirmées pas encore facturées
  const billable = orders.filter(
    (o) => o.status === "confirmed" && !invoices.some((i) => i.order_id === o.id),
  );

  const handleCreate = async () => {
    setError(null);
    if (!orderId) return setError("Choisissez une commande.");
    try {
      await createInvoice.mutateAsync({ orderId });
      setOrderId(null);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la facturation");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Facturation</h1>
        <p className="text-sm text-gray-600">Factures clients</p>
      </div>

      {/* Facturer une commande */}
      <Card className="space-y-3 p-4">
        <h2 className="font-semibold text-gray-800">Facturer une commande confirmée</h2>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="min-w-64 rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={orderId ?? ""}
            onChange={(e) => setOrderId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Commande —</option>
            {billable.map((o) => (
              <option key={o.id} value={o.id}>
                {o.reference} — {formatCurrency(o.amount_total)}
              </option>
            ))}
          </select>
          <Button onClick={handleCreate} disabled={createInvoice.isPending}>
            {createInvoice.isPending ? "Création…" : "Créer la facture"}
          </Button>
          {billable.length === 0 && (
            <p className="text-xs text-gray-400">
              Aucune commande confirmée en attente de facturation.
            </p>
          )}
        </div>
      </Card>

      {/* Liste des factures */}
      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : invoices.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucune facture.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Référence</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-right">Payé</th>
                <th className="px-4 py-3 text-right">Reste</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr
                  key={inv.id}
                  onClick={() => router.push(`/dashboard/invoicing/${inv.id}`)}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">
                    {inv.reference}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(inv.invoice_date)}</td>
                  <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(inv.amount_total)}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{formatCurrency(inv.paid_amount)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">
                    {formatCurrency(Math.max(inv.amount_total - inv.paid_amount, 0))}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      title={`Imprimer la facture ${inv.reference}`}
                      aria-label={`Imprimer la facture ${inv.reference}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        printInvoice(inv.id).catch(() => alert("Impossible de générer le PDF."));
                      }}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-gray-600 hover:bg-gray-100"
                    >
                      <Printer className="h-4 w-4" />
                    </button>
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
