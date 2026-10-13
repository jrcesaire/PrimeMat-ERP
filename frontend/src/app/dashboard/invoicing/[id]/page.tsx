"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Banknote, CheckCircle2, Printer, Truck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PaymentDialog } from "@/components/sales/PaymentDialog";
import {
  useCloseOrder,
  useDeliveryNotes,
  useCreateDeliveryFromOrder,
  useInvoice,
  usePayments,
  usePostInvoice,
  useResetInvoiceToDraft,
  useCancelInvoice,
  useDeleteInvoice,
} from "@/hooks/useOperations";
import { useClients } from "@/hooks/useCRM";
import { usePermission } from "@/hooks/useAuth";
import {
  useConfirm,
  confirmBackToDraftOptions,
  confirmCloseOptions,
  confirmDeleteOptions,
} from "@/components/ui/confirm";
import { printDelivery, printInvoice, printReceipt } from "@/lib/api/pdf";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";
import type { InvoiceLine } from "@/hooks/useOperations";

function LineDetail({ line, currency }: { line: InvoiceLine; currency: string }) {
  const fmt = (n: number) => formatCurrency(n, currency);
  if (line.sell_by_length && line.cuts && line.cuts.length > 0) {
    return (
      <div className="border-b border-gray-100 py-3">
        <div className="font-medium text-gray-900">
          {line.description ?? `Ligne #${line.id}`}
          {line.variant_name && (
            <span className="ml-2 inline-block rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-blue-700">
              {line.variant_name}
            </span>
          )}
        </div>
        <div className="mt-1 space-y-0.5 text-xs text-gray-500">
          {line.cuts.map((c, i) => (
            <div key={i} className="flex justify-between">
              <span>{c.quantity} pièces × {c.length.toFixed(2)} m</span>
              <span>= {(c.quantity * c.length).toFixed(2)} m</span>
            </div>
          ))}
          <div className="flex justify-between border-t border-gray-200 pt-1 font-medium text-gray-700">
            <span>Total: {line.cuts.reduce((s, c) => s + c.quantity * c.length, 0).toFixed(2)} m × {fmt(line.unit_price)}</span>
            <span>{fmt(line.subtotal)}</span>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-between border-b border-gray-100 py-3">
      <div>
        <div className="font-medium text-gray-900">
          {line.description ?? `Ligne #${line.id}`}
          {line.variant_name && (
            <span className="ml-2 inline-block rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-blue-700">
              {line.variant_name}
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">Quantité: {line.quantity}</div>
      </div>
      <div className="text-right">
        <div className="font-medium">{fmt(line.unit_price)}</div>
        <div className="text-sm font-semibold text-gray-900">{fmt(line.subtotal)}</div>
      </div>
    </div>
  );
}

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const invoiceId = Number(params.id);
  const { data: invoice, isLoading, error } = useInvoice(invoiceId);
  const { data: clients = [] } = useClients();
  const postInvoice = usePostInvoice();
  const closeOrder = useCloseOrder();
  const createDelivery = useCreateDeliveryFromOrder();
  const resetToDraft = useResetInvoiceToDraft();
  const cancelInvoice = useCancelInvoice();
  const deleteInvoice = useDeleteInvoice();
  const can = usePermission();
  const canDeleteInvoice = can("invoice:delete");
  const { data: orderDeliveries = [] } = useDeliveryNotes(
    invoice?.order_id ?? undefined
  );
  const { data: invoicePayments = [] } = usePayments(invoiceId);
  const confirm = useConfirm();
  const [payOpen, setPayOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // --- Enregistrement d'un paiement ---

  if (isLoading) return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (error || !invoice) return <p className="p-6 text-sm text-red-500">Facture introuvable.</p>;

  const client = clients.find((c) => c.id === invoice.partner_id);
  const remaining = Math.max(invoice.amount_total - invoice.paid_amount, 0);
  const currency = invoice.currency_code || "XOF";
  const isConfirmed = invoice.status !== "draft";
  const isPaid = invoice.status === "paid" || remaining <= 0.005;
  const activeDeliveries = (orderDeliveries ?? []).filter(
    (d) => d.status !== "cancelled"
  );
  const canPay =
    ["posted", "partially_paid", "paid"].includes(invoice.status) &&
    remaining > 0.005;
  const delivery = activeDeliveries[0];
  const pendingDelivery =
    delivery != null &&
    delivery.status !== "delivered" &&
    delivery.status !== "completed";

  const handlePost = async () => {
    try {
      await postInvoice.mutateAsync(invoice.id);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la confirmation");
    }
  };

  const handleResetToDraft = async () => {
    const { confirmed } = await confirm({
      ...confirmBackToDraftOptions(invoice.reference),
      description:
        "Son écriture comptable sera supprimée. Vous pourrez modifier la facture puis la confirmer à nouveau.",
    });
    if (!confirmed) {
      return;
    }
    try {
      await resetToDraft.mutateAsync(invoice.id);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(
        typeof detail === "string" ? detail : "Erreur lors de la remise en brouillon"
      );
    }
  };

  const handleCancelInvoice = async () => {
    const { confirmed } = await confirm({
      title: `Annuler définitivement la facture ${invoice.reference} ?`,
      description:
        "La commande liée redeviendra facturable. Vous pourrez créer une nouvelle facture depuis la commande.",
      confirmLabel: "Annuler la facture",
      cancelLabel: "Revenir",
      tone: "danger",
    });
    if (!confirmed) {
      return;
    }
    try {
      await cancelInvoice.mutateAsync(invoice.id);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de l'annulation");
    }
  };

  const handleDeleteInvoice = async () => {
    const { confirmed } = await confirm({
      ...confirmDeleteOptions(invoice.reference),
      description:
        "Seules les factures en brouillon et sans paiement peuvent être supprimées. Cette action est irréversible.",
    });
    if (!confirmed) {
      return;
    }
    try {
      await deleteInvoice.mutateAsync(invoice.id);
      router.push("/dashboard/invoicing");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la suppression");
    }
  };

  const handlePay = () => {
    setActionError(null);
    setPayOpen(true);
  };

  const handleCreateDelivery = async () => {
    if (invoice.order_id == null) return;
    setActionError(null);
    try {
      const created = await createDelivery.mutateAsync({
        order_id: invoice.order_id,
      });
      router.push(`/dashboard/delivery/${created.id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setActionError(
        typeof detail === "string"
          ? detail
          : "Erreur lors de la création du bon de livraison"
      );
    }
  };

  const handleCloseSale = async () => {
    if (invoice.order_id == null) return;
    const { confirmed } = await confirm({
      ...confirmCloseOptions(`la vente ${invoice.reference}`),
      description:
        "La commande sera marquée comme livrée et la vente sera close définitivement.",
    });
    if (!confirmed) {
      return;
    }
    setActionError(null);
    try {
      await closeOrder.mutateAsync(invoice.order_id);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setActionError(
        typeof detail === "string" ? detail : "Erreur lors de la clôture"
      );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="rounded-md p-2 hover:bg-gray-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{invoice.reference}</h1>
            <p className="text-sm text-gray-600">
              Facture — {client?.name ?? `Client #${invoice.partner_id}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={invoice.status} />
          {invoice.status === "draft" && (
            <Button
              size="sm"
              onClick={handlePost}
              disabled={postInvoice.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              {postInvoice.isPending ? "Confirmation…" : "Confirmer"}
            </Button>
          )}
          {invoice.status === "posted" && invoice.paid_amount === 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetToDraft}
              disabled={resetToDraft.isPending}
            >
              {resetToDraft.isPending ? "Reprise…" : "Remettre en brouillon"}
            </Button>
          )}
          {["draft", "posted"].includes(invoice.status) &&
            invoice.paid_amount === 0 && (
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 hover:bg-red-50"
                onClick={handleCancelInvoice}
                disabled={cancelInvoice.isPending}
              >
                {cancelInvoice.isPending ? "Annulation…" : "Annuler la facture"}
              </Button>
            )}
          {invoice.status === "draft" && canDeleteInvoice && (
            <Button
              variant="outline"
              size="sm"
              className="text-red-600 hover:bg-red-50"
              onClick={handleDeleteInvoice}
              disabled={deleteInvoice.isPending}
            >
              {deleteInvoice.isPending ? "Suppression…" : "Supprimer"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => printInvoice(invoice.id)}>
            <Printer className="mr-2 h-4 w-4" /> Imprimer
          </Button>
          {canPay && (
            <Button variant="outline" size="sm" onClick={handlePay}>
              <Banknote className="mr-2 h-4 w-4 text-green-600" /> Paiement
            </Button>
          )}
          {invoice.order_id != null && (
            delivery == null ? (
              <Button
                variant="outline"
                size="icon"
                title={
                  isPaid
                    ? `Créer le bon de livraison de la commande #${invoice.order_id}`
                    : "Le bon de livraison sera disponible une fois la facture confirmée"
                }
                onClick={handleCreateDelivery}
                disabled={createDelivery.isPending || !isConfirmed}
              >
                <Truck className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                variant="outline"
                size="icon"
                title={`Voir le bon ${delivery.reference}`}
                onClick={() => router.push(`/dashboard/delivery/${delivery.id}`)}
              >
                <Truck className="h-4 w-4" />
              </Button>
            )
          )}
          {invoice.order_id != null && isPaid && !pendingDelivery && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCloseSale}
              disabled={closeOrder.isPending}
            >
              {closeOrder.isPending ? "Clôture…" : "Clôturer la vente"}
            </Button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">
          {actionError}
        </div>
      )}

      <Card className="grid grid-cols-2 gap-4 p-4 text-sm md:grid-cols-3">
        <div>
          <p className="text-xs text-gray-500">Client</p>
          <p className="font-medium text-gray-900">{client?.name ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Statut</p>
          <StatusBadge status={invoice.status} />
        </div>
        <div>
          <p className="text-xs text-gray-500">Date</p>
          <p className="font-medium text-gray-900">{formatDate(invoice.invoice_date)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Échéance</p>
          <p className="font-medium text-gray-900">{invoice.due_date ? formatDate(invoice.due_date) : "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Total</p>
          <p className="font-medium text-gray-900">{formatCurrency(invoice.amount_total, currency)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Payé</p>
          <p className="font-medium text-green-600">{formatCurrency(invoice.paid_amount, currency)}</p>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <th className="px-4 py-3">Produit</th>
              <th className="px-4 py-3 text-right">Qté</th>
              <th className="px-4 py-3 text-right">P.U.</th>
              <th className="px-4 py-3 text-right">Montant</th>
            </tr>
          </thead>
          <tbody>
            {invoice.lines?.map((l) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {l.description ?? `Produit #${l.product_id}`}
                  {l.variant_name && (
                    <span className="ml-2 inline-block rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-blue-700">
                      {l.variant_name}
                    </span>
                  )}
                  {l.cuts && l.cuts.length > 0 && (
                    <p className="mt-0.5 text-xs italic text-gray-500">
                      {l.cuts.map((c) => `${c.quantity} × ${c.length} m`).join(", ")}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-right">{l.quantity}</td>
                <td className="px-4 py-3 text-right">{formatCurrency(l.unit_price, currency)}</td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(l.subtotal, currency)}</td>
              </tr>
            ))}
            {(!invoice.lines || invoice.lines.length === 0) && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                  Aucune ligne.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card className="space-y-2 p-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Montant hors taxes</span>
          <span className="font-medium text-gray-900">{formatCurrency(invoice.amount_untaxed, currency)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">TVA</span>
          <span className="font-medium text-gray-900">{formatCurrency(invoice.tax_amount, currency)}</span>
        </div>
        <div className="flex justify-between text-base font-bold">
          <span className="text-gray-700">Total</span>
          <span>{formatCurrency(invoice.amount_total, currency)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Payé</span>
          <span className="font-medium text-green-600">{formatCurrency(invoice.paid_amount, currency)}</span>
        </div>
        <div className="flex justify-between text-sm font-semibold">
          <span className="text-gray-500">Reste dû</span>
          <span className={remaining > 0 ? "text-red-600" : "text-gray-600"}>
            {formatCurrency(remaining, currency)}
          </span>
        </div>
        {invoice.order_id && (
          <div className="mt-2 border-t border-gray-100 pt-2 text-xs">
            <Link
              href="/dashboard/sales"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Créée à partir de la commande #{invoice.order_id} →
            </Link>
          </div>
        )}
      </Card>

      {/* Fenêtre d'encaissement (étape 4 : intégral / partiel + journal) */}
      <PaymentDialog
        open={payOpen && canPay}
        onClose={() => setPayOpen(false)}
        invoiceId={invoice.id}
        partnerId={invoice.partner_id}
        remaining={remaining}
        currency={currency}
      />

      {/* Historique des paiements + reçus (étape 5) */}
      {invoicePayments.length > 0 && (
        <Card className="space-y-2 p-4">
          <h2 className="flex items-center gap-2 font-semibold text-gray-800">
            <Banknote className="h-4 w-4 text-green-600" />
            Paiements ({invoicePayments.length})
          </h2>
          {invoicePayments.map((p) => (
            <div
              key={p.id}
              onClick={() => router.push(`/dashboard/payments/${p.id}`)}
              className="-mx-2 flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-md border-b border-gray-100 px-2 py-2 text-sm transition-colors last:border-0 hover:bg-gray-50"
            >
              <div>
                <span className="font-medium text-gray-900 hover:text-primary hover:underline">
                  {p.reference}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {formatDate(p.payment_date)} — {formatCurrency(p.amount, currency)}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  printReceipt(p.id);
                }}
              >
                <Printer className="mr-2 h-4 w-4" /> Reçu
              </Button>
            </div>
          ))}
        </Card>
      )}

      {/* Bon de livraison lié (validation / impression) */}
      {delivery != null && (
        <Card
          onClick={() => router.push(`/dashboard/delivery/${delivery.id}`)}
          className="flex cursor-pointer flex-wrap items-center justify-between gap-2 p-4 text-sm transition-colors hover:bg-gray-50"
        >
          <div>
            <span className="text-gray-500">Bon de livraison : </span>
            <span className="font-medium text-gray-900 hover:text-primary hover:underline">
              {delivery.reference}
            </span>
            <span className="ml-2">
              <StatusBadge status={delivery.status} />
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                router.push(`/dashboard/delivery/${delivery.id}`);
              }}
            >
              <Truck className="mr-2 h-4 w-4" /> Valider
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                printDelivery(delivery.id);
              }}
            >
              <Printer className="mr-2 h-4 w-4" /> Imprimer
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
