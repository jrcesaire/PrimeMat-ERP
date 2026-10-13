"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useDeliveryNote,
  useUpdateDeliveryStatus,
  useBackToDraftDelivery,
  useDeleteDelivery,
} from "@/hooks/useOperations";
import { useClients } from "@/hooks/useCRM";
import { usePermission } from "@/hooks/useAuth";
import {
  useConfirm,
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

export default function DeliveryDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id: idParam } = use(params);
  const id = Number(idParam) || 0;
  const { data: d, isLoading } = useDeliveryNote(id);
  const { data: clients = [] } = useClients();
  const updateStatus = useUpdateDeliveryStatus();
  const backToDraft = useBackToDraftDelivery();
  const deleteDelivery = useDeleteDelivery();
  const can = usePermission();
  const canEditDelivery = can("delivery:edit");
  const canDeleteDelivery = can("delivery:delete");
  const confirm = useConfirm();

  const handleBackToDraft = async (reference: string) => {
    const { confirmed } = await confirm(
      confirmBackToDraftOptions(
        `${reference} — Seul un BL au brouillon peut être supprimé.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await backToDraft.mutateAsync(id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la remise au brouillon");
    }
  };

  const handleDelete = async (reference: string) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(
        `${reference} — Seuls les BL en brouillon et sans paiement restant peuvent être supprimés.`,
      ),
    );
    if (!confirmed) {
      return;
    }
    try {
      await deleteDelivery.mutateAsync(id);
      router.push("/dashboard/delivery");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Erreur lors de la suppression");
    }
  };

  if (isLoading)
    return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (!d)
    return (
      <p className="p-6 text-sm text-gray-500">
        Bon de livraison introuvable (ou accès refusé).
      </p>
    );

  const client = clients.find((c) => c.id === d.partner_id);
  const next = NEXT_STATUS[d.status];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/dashboard/delivery" className="text-sm text-gray-500 hover:text-primary">
            <ArrowLeft className="mr-1 inline h-4 w-4" /> Retour aux livraisons
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{d.reference}</h1>
          <p className="text-sm text-gray-600">
            {client?.name ?? `Client #${d.partner_id}`}
            {d.order_id ? ` · Commande #${d.order_id}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {next && canEditDelivery && (
            <Button
              variant="outline"
              disabled={updateStatus.isPending}
              onClick={() =>
                updateStatus
                  .mutateAsync({ deliveryId: d.id, status: next.value })
                  .catch(() => alert("Erreur lors du changement de statut"))
              }
            >
              {next.label}
            </Button>
          )}
          <Button
            className="flex items-center gap-2"
            onClick={() => printDelivery(d.id)}
          >
            <Printer className="h-4 w-4" /> Imprimer
          </Button>
          {d.status !== "draft" && canEditDelivery && (
            <Button
              variant="outline"
              className="text-amber-700 hover:bg-amber-50"
              disabled={backToDraft.isPending}
              onClick={() => handleBackToDraft(d.reference)}
            >
              {backToDraft.isPending ? "Reprise…" : "Remettre au brouillon"}
            </Button>
          )}
          {d.status === "draft" && canDeleteDelivery && (
            <Button
              variant="outline"
              className="text-red-600 hover:bg-red-50"
              disabled={deleteDelivery.isPending}
              onClick={() => handleDelete(d.reference)}
            >
              {deleteDelivery.isPending ? "Suppression…" : "Supprimer"}
            </Button>
          )}
        </div>
      </div>

      <Card className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-gray-500">Statut</p>
          <StatusBadge status={d.status} />
        </div>
        <div>
          <p className="text-xs text-gray-500">Date prévue</p>
          <p className="text-sm font-medium text-gray-900">
            {d.expected_date ? formatDate(d.expected_date) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Expédié</p>
          <p className="text-sm font-medium text-gray-900">
            {d.shipped_date ? formatDate(d.shipped_date) : "—"}
          </p>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <th className="px-4 py-3">Produit</th>
              <th className="px-4 py-3 text-right">Commandé</th>
              <th className="px-4 py-3 text-right">Livré</th>
              <th className="px-4 py-3">Unité</th>
            </tr>
          </thead>
          <tbody>
            {d.lines?.map((l) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {l.description ?? `Produit #${l.product_id}`}
                  {l.variant_name && (
                    <span className="ml-2 inline-block rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-blue-700">
                      {l.variant_name}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">{l.quantity_ordered}</td>
                <td className="px-4 py-3 text-right font-semibold">
                  {l.quantity_delivered}
                </td>
                <td className="px-4 py-3 text-gray-600">{l.unit ?? "—"}</td>
              </tr>
            ))}
            {(!d.lines || d.lines.length === 0) && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                  Aucune ligne.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}