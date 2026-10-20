/**
 * Page Livraison — bons de livraison, planning, impression.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExportButton } from "@/components/shared/export-button";
import {
  useDeliveryNotes,
  useCreateDeliveryFromOrder,
  useUpdateDeliveryStatus,
  useBackToDraftDelivery,
  useDeleteDelivery,
} from "@/hooks/useOperations";
import { useOrders } from "@/hooks/useSales";
import { useClients } from "@/hooks/useCRM";
import { usePermission } from "@/hooks/useAuth";
import { useConfirm } from "@/components/ui/confirm";
import {
  confirmBackToDraftOptions,
  confirmDeleteOptions,
} from "@/components/ui/confirm";
import { printDelivery } from "@/lib/api/pdf";
import { formatDate, StatusBadge } from "@/lib/utils";

const NEXT_STATUS: Record<string, { label: string; value: string }> = {
  draft: { label: "Confirmer", value: "pending" },
  planned: { label: "Expédier", value: "shipped" },
  shipped: { label: "Livrer", value: "delivered" },
  pending: { label: "Livrer", value: "delivered" },
  in_progress: { label: "Livrer", value: "delivered" },
  delivered: { label: "Terminer", value: "completed" },
};

export default function DeliveryPage() {
  const router = useRouter();
  const { data: deliveries = [], isLoading } = useDeliveryNotes();
  const { data: orders = [] } = useOrders();
  const { data: clients = [] } = useClients();
  const createDelivery = useCreateDeliveryFromOrder();
  const updateStatus = useUpdateDeliveryStatus();
  const backToDraft = useBackToDraftDelivery();
  const deleteDelivery = useDeleteDelivery();
  const can = usePermission();
  const canEditDelivery = can("delivery:edit");
  const canDeleteDelivery = can("delivery:delete");
  const confirm = useConfirm();

  const [orderId, setOrderId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBackToDraft = async (reference: string, deliveryId: number) => {
    const { confirmed } = await confirm(
      confirmBackToDraftOptions(
        `${reference} — Seul un BL au brouillon peut être supprimé.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await backToDraft.mutateAsync(deliveryId);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la remise au brouillon");
    }
  };

  const handleDeleteDelivery = async (reference: string, deliveryId: number) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(
        `${reference} — Seuls les BL en brouillon et sans paiement restant peuvent être supprimés.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await deleteDelivery.mutateAsync(deliveryId);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la suppression");
    }
  };

  const clientName = (id: number) =>
    clients.find((c) => c.id === id)?.name ?? `#${id}`;

  // Commandes confirmées sans bon de livraison
  const deliverable = orders.filter(
    (o) =>
      o.status === "confirmed" &&
      o.fulfillment_mode !== "pos" &&
      !deliveries.some((d) => d.order_id === o.id),
  );

  const handleCreate = async () => {
    setError(null);
    if (!orderId) return setError("Choisissez une commande.");
    try {
      await createDelivery.mutateAsync({ order_id: orderId });
      setOrderId(null);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la création");
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Livraison</h1>
          <p className="text-sm text-gray-600">Bons de livraison</p>
        </div>
        <ExportButton
          endpoint="/delivery/notes/export"
          fallbackName="livraisons"
        />
      </div>

      {/* Créer depuis commande */}
      <Card className="space-y-3 p-4">
        <h2 className="font-semibold text-gray-800">Préparer une livraison</h2>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="min-w-64 rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={orderId ?? ""}
            onChange={(e) => setOrderId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Commande confirmée —</option>
            {deliverable.map((o) => (
              <option key={o.id} value={o.id}>
                {o.reference} — {clientName(o.partner_id)}
              </option>
            ))}
          </select>
          <Button onClick={handleCreate} disabled={createDelivery.isPending}>
            {createDelivery.isPending ? "Création…" : "Créer le bon de livraison"}
          </Button>
          {deliverable.length === 0 && (
            <p className="text-xs text-gray-400">Aucune commande en attente de livraison.</p>
          )}
        </div>
      </Card>

      {/* Liste */}
      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : deliveries.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucun bon de livraison.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Référence</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">Date prévue</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((d) => {
                const next = NEXT_STATUS[d.status];
                return (
                  <tr
                    key={d.id}
                    onClick={() => router.push(`/dashboard/delivery/${d.id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">
                      {d.reference}
                    </td>
                    <td className="px-4 py-3">{clientName(d.partner_id)}</td>
                    <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                    <td className="px-4 py-3 text-gray-600">
                      {d.expected_date ? formatDate(d.expected_date) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {next && canEditDelivery && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={updateStatus.isPending}
                            onClick={(e) => {
                              e.stopPropagation();
                              updateStatus
                                .mutateAsync({ deliveryId: d.id, status: next.value })
                                .catch(() => alert("Erreur changement de statut"));
                            }}
                          >
                            {next.label}
                          </Button>
                        )}
                        {d.status !== "draft" && canEditDelivery && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-amber-700 hover:bg-amber-50"
                            disabled={backToDraft.isPending}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleBackToDraft(d.reference, d.id);
                            }}
                          >
                            Brouillon
                          </Button>
                        )}
                        {d.status === "draft" && canDeleteDelivery && (
                          <button
                            title={`Supprimer ${d.reference}`}
                            aria-label={`Supprimer ${d.reference}`}
                            disabled={deleteDelivery.isPending}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteDelivery(d.reference, d.id);
                            }}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            🗑
                          </button>
                        )}
                        <button
                          title={`Imprimer le bon ${d.reference}`}
                          aria-label={`Imprimer le bon ${d.reference}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            printDelivery(d.id).catch(() =>
                              alert("Impossible de générer le PDF.")
                            );
                          }}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-gray-600 hover:bg-gray-100"
                        >
                          🖨
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
