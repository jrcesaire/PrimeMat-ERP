/**
 * Détail d'un paiement — lecture + reçu imprimable.
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { use } from "react";
import {
  usePayments,
  useBackToDraftPayment,
  useConfirmPayment,
  useDeletePayment,
  type Payment,
} from "@/hooks/useOperations";
import { useInvoices } from "@/hooks/useOperations";
import { useClients } from "@/hooks/useCRM";
import { usePermission } from "@/hooks/useAuth";
import {
  useConfirm,
  confirmBackToDraftOptions,
  confirmDeleteOptions,
} from "@/components/ui/confirm";
import { printReceipt } from "@/lib/api/pdf";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";

const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  mobile_money: "Mobile Money",
  bank: "Virement",
  check: "Chèque",
};

export default function PaymentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id: idParam } = use(params);
  const id = Number(idParam) || 0;
  const { data: payments = [], isLoading } = usePayments();
  const { data: invoices = [] } = useInvoices();
  const { data: clients = [] } = useClients();
  const backToDraft = useBackToDraftPayment();
  const confirmPayment = useConfirmPayment();
  const deletePayment = useDeletePayment();
  const can = usePermission();
  const canEditPayment = can("payment:edit");
  const canDeletePayment = can("payment:delete");
  const confirm = useConfirm();

  const payment: Payment | undefined = payments.find((p) => p.id === id);

  const handleConfirm = async () => {
    if (!payment) return;
    try {
      await confirmPayment.mutateAsync(payment.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la confirmation");
    }
  };

  const handleBackToDraft = async () => {
    if (!payment) return;
    const { confirmed } = await confirm({
      ...confirmBackToDraftOptions(payment.reference),
      description:
        "Le montant sera retiré de la facture liée et son écriture comptable supprimée. Vous pourrez confirmer à nouveau.",
    });
    if (!confirmed) {
      return;
    }
    try {
      await backToDraft.mutateAsync(payment.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(
        typeof detail === "string"
          ? detail
          : "Erreur lors de la remise au brouillon"
      );
    }
  };

  const handleDelete = async () => {
    if (!payment) return;
    const { confirmed } = await confirm(confirmDeleteOptions(payment.reference));
    if (!confirmed) {
      return;
    }
    try {
      await deletePayment.mutateAsync(payment.id);
      router.push("/dashboard/payments");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la suppression");
    }
  };

  if (isLoading)
    return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (!payment)
    return (
      <p className="p-6 text-sm text-gray-500">
        Paiement introuvable (ou accès refusé).
      </p>
    );

  const client = clients.find((c) => c.id === payment.partner_id);
  const invoice = invoices.find((i) => i.id === payment.invoice_id);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/dashboard/payments" className="text-sm text-gray-500 hover:text-primary">
            <ArrowLeft className="mr-1 inline h-4 w-4" /> Retour aux paiements
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{payment.reference}</h1>
          <p className="text-sm text-gray-600">
            {client?.name ?? `Client #${payment.partner_id ?? "?"}`} ·{" "}
            {formatDate(payment.payment_date)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {payment.status === "draft" && canEditPayment && (
            <Button
              size="sm"
              onClick={handleConfirm}
              disabled={confirmPayment.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {confirmPayment.isPending ? "Confirmation…" : "Confirmer"}
            </Button>
          )}
          {payment.status !== "draft" && canEditPayment && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleBackToDraft}
              disabled={backToDraft.isPending}
              className="text-amber-700 hover:bg-amber-50"
            >
              {backToDraft.isPending ? "Reprise…" : "Remettre au brouillon"}
            </Button>
          )}
          {payment.status === "draft" && canDeletePayment && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={deletePayment.isPending}
              className="text-red-600 hover:bg-red-50"
            >
              {deletePayment.isPending ? "Suppression…" : "Supprimer"}
            </Button>
          )}
          {payment.status !== "draft" && (
            <Button
              variant="outline"
              className="flex items-center gap-2"
              onClick={() => printReceipt(payment.id)}
            >
              <Printer className="h-4 w-4" /> Imprimer le reçu
            </Button>
          )}
        </div>
      </div>

      <Card className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-gray-500">Statut</p>
          <StatusBadge status={payment.status} />
        </div>
        <div>
          <p className="text-xs text-gray-500">Mode</p>
          <p className="text-sm font-medium text-gray-900">
            {METHOD_LABELS[payment.method] ?? payment.method}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Direction</p>
          <p className="text-sm font-medium text-gray-900">
            {payment.direction === "in" ? "Entrant" : "Sortant"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Facture liée</p>
          <p className="text-sm font-medium text-gray-900">
            {invoice?.reference ?? (payment.invoice_id ? `#${payment.invoice_id}` : "—")}
          </p>
        </div>
      </Card>

      <Card className="flex justify-between p-5">
        <span className="text-sm text-gray-500">Montant</span>
        <span className="text-2xl font-bold text-green-700">
          {formatCurrency(payment.amount)}
        </span>
      </Card>
    </div>
  );
}