/**
 * Page Facturation — factures, facturation depuis commande, impression.
 */
"use client";
import { RowsSkeleton } from "@/components/ui/skeleton";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExportButton } from "@/components/shared/export-button";
import { ViewSwitcher } from "@/components/shared/view-switcher";
import {
  useInvoices,
  useBillableOrders,
  useCreateInvoiceFromOrder,
  usePostInvoice,
  useDeleteInvoice,
} from "@/hooks/useOperations";
import { usePermission } from "@/hooks/useAuth";
import { useConfirm } from "@/components/ui/confirm";
import {
  confirmDeleteOptions,
  confirmPostOptions,
} from "@/components/ui/confirm";
import { printInvoice } from "@/lib/api/pdf";
import { cn, formatCurrency, formatDate, lastRouteSegment, STATUS_LABELS, StatusBadge } from "@/lib/utils";

/** Vue du module Facturation (sous-routes « Créer » / « Liste »). */
export type InvoicingView = "new" | "list";

/** Sous-route → vue : /dashboard/invoicing/new ouvre la création. */
function viewFromPath(pathname: string | null): InvoicingView {
  return lastRouteSegment(pathname) === "new" ? "new" : "list";
}

export default function InvoicingPage() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: invoices = [], isLoading } = useInvoices();
  const {
    data: billable = [],
    isLoading: loadingBillable,
    isError: billableError,
  } = useBillableOrders();
  const createInvoice = useCreateInvoiceFromOrder();
  const postInvoice = usePostInvoice();
  const deleteInvoice = useDeleteInvoice();
  const can = usePermission();
  const canPostInvoice = can("invoice:edit");
  const canDeleteInvoice = can("invoice:delete");
  const confirm = useConfirm();

  const [orderId, setOrderId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<InvoicingView>(viewFromPath(pathname));

  const handleDeleteInvoice = async (
    e: React.MouseEvent,
    reference: string,
    invoiceId: number
  ) => {
    e.stopPropagation();
    const { confirmed } = await confirm(
      confirmDeleteOptions(
        `la facture ${reference} — Seules les factures en brouillon et sans paiement peuvent être supprimées.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await deleteInvoice.mutateAsync(invoiceId);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la suppression");
    }
  };

  const handlePostInvoice = async (
    e: React.MouseEvent,
    reference: string,
    invoiceId: number
  ) => {
    e.stopPropagation();
    const { confirmed } = await confirm(
      confirmPostOptions(
        `la facture ${reference} — Elle sera comptabilisée et ne pourra plus être modifiée.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await postInvoice.mutateAsync(invoiceId);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la confirmation");
    }
  };

  const handleCreate = async () => {
    setError(null);
    if (!orderId) return setError("Choisissez une commande.");
    try {
      const invoice = await createInvoice.mutateAsync({ orderId });
      setOrderId(null);
      router.push(`/dashboard/invoicing/${invoice.id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la facturation");
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Facturation</h1>
          <p className="text-sm text-muted">Factures clients</p>
        </div>
        <ExportButton
          endpoint="/invoicing/invoices/export"
          fallbackName="factures"
        />
      </div>

      <ViewSwitcher
        value={view}
        onChange={setView}
        options={[
          { key: "new", label: "Créer une facture" },
          { key: "list", label: "Liste des factures" },
        ]}
      />

      {/* Facturer une commande */}
      <Card className={cn("space-y-3 p-4", view !== "new" && "hidden")}>
        <div>
          <h2 className="font-semibold text-ink">Facturer une commande</h2>
          <p className="text-xs text-muted">
            Commandes restant à facturer — le statut est rappelé quand la commande
            n&apos;est pas encore confirmée.
          </p>
        </div>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="min-w-64 rounded-md border border-line px-3 py-2 text-sm"
            value={orderId ?? ""}
            disabled={loadingBillable}
            onChange={(e) => setOrderId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">
              {loadingBillable ? "Chargement des commandes…" : "— Commande —"}
            </option>
            {billable.map((o) => (
              <option key={o.id} value={o.id}>
                {o.reference} — {formatCurrency(o.remaining_amount)} à facturer
                {o.status === "confirmed"
                  ? ""
                  : ` (${(STATUS_LABELS[o.status]?.label ?? o.status).toLowerCase()})`}
              </option>
            ))}
          </select>
          <Button
            onClick={handleCreate}
            disabled={!orderId || createInvoice.isPending || loadingBillable}
          >
            {createInvoice.isPending ? "Création…" : "Créer la facture"}
          </Button>
          {billableError && (
            <p className="text-xs text-red-600">
              Impossible de charger les commandes facturables.
            </p>
          )}
          {!loadingBillable && !billableError && billable.length === 0 && (
            <p className="text-xs text-faint">
              Aucune commande en attente de facturation : elles sont déjà
              facturées, annulées, ou issues d&apos;une vente comptoir.
            </p>
          )}
        </div>
      </Card>

      {/* Liste des factures */}
      <Card className={cn("overflow-hidden p-0", view !== "list" && "hidden")}>
        {isLoading ? (
          <RowsSkeleton />
        ) : invoices.length === 0 ? (
          <p className="p-10 text-center text-sm text-muted">Aucune facture.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase text-muted">
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
                  className="cursor-pointer border-b border-line hover:bg-subtle"
                >
                  <td className="px-4 py-3 font-medium text-ink hover:text-primary hover:underline">
                    {inv.reference}
                  </td>
                  <td className="px-4 py-3 text-muted">{formatDate(inv.invoice_date)}</td>
                  <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(inv.amount_total)}</td>
                  <td className="px-4 py-3 text-right text-muted">{formatCurrency(inv.paid_amount)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">
                    {formatCurrency(Math.max(inv.amount_total - inv.paid_amount, 0))}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {inv.status === "draft" && canPostInvoice && (
                        <button
                          title={`Confirmer la facture ${inv.reference}`}
                          aria-label={`Confirmer la facture ${inv.reference}`}
                          disabled={postInvoice.isPending}
                          onClick={(e) =>
                            handlePostInvoice(e, inv.reference, inv.id)
                          }
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-green-600 hover:bg-green-50 disabled:opacity-50"
                        >
                          ✓
                        </button>
                      )}
                      {inv.status === "draft" && canDeleteInvoice && (
                        <button
                          title={`Supprimer la facture ${inv.reference}`}
                          aria-label={`Supprimer la facture ${inv.reference}`}
                          disabled={deleteInvoice.isPending}
                          onClick={(e) =>
                            handleDeleteInvoice(e, inv.reference, inv.id)
                          }
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          🗑
                        </button>
                      )}
                      <button
                        title={`Imprimer la facture ${inv.reference}`}
                        aria-label={`Imprimer la facture ${inv.reference}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          printInvoice(inv.id).catch(() => alert("Impossible de générer le PDF."));
                        }}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-subtle"
                      >
                        <Printer className="h-4 w-4" />
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
