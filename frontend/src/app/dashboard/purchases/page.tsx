/**
 * Page Achats — demandes d'achat (DA), bons de commande (BC),
 * réceptions (BR), factures fournisseur, fournisseurs et suggestions.
 *
 * Workflow : DA (draft → submitted → approved → converted) → BC
 * (draft → pending → confirmed → received) → BR (draft → validated)
 * → facture (draft → posted → paid, rapprochement 3 voies).
 */
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useConfirm, confirmDeleteOptions } from "@/components/ui/confirm";
import { usePermission } from "@/hooks/useAuth";
import { useOrders } from "@/hooks/useSales";
import { useProducts } from "@/hooks/useCatalogue";
import {
  useSuppliers,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
  useRateSupplier,
  useSupplierSuggestions,
  usePriceSuggestions,
  usePurchaseRequests,
  useCreatePurchaseRequest,
  useSubmitPurchaseRequest,
  useApprovePurchaseRequest,
  useRejectPurchaseRequest,
  useDeletePurchaseRequest,
  useConvertRequestToOrder,
  usePurchaseOrders,
  useCreatePurchaseOrder,
  useSubmitPurchaseOrder,
  useConfirmPurchaseOrder,
  useCancelPurchaseOrder,
  usePurchaseOrderLines,
  usePurchaseReceptions,
  useCreatePurchaseReception,
  useValidatePurchaseReception,
  useSupplierInvoices,
  useCreateSupplierInvoice,
  useMatchSupplierInvoice,
  usePostSupplierInvoice,
  usePaySupplierInvoice,
} from "@/hooks/usePurchases";
import { printPurchaseOrder } from "@/lib/api/pdf";
import { useWarehouses } from "@/hooks/useStock";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";
import type { MatchingResult } from "@/lib/types";

type Tab =
  | "demandes"
  | "commandes"
  | "receptions"
  | "factures"
  | "fournisseurs"
  | "suggestions"
  | "besoins";

const TABS: { key: Tab; label: string }[] = [
  { key: "demandes", label: "Demandes (DA)" },
  { key: "commandes", label: "Bons de commande" },
  { key: "receptions", label: "Réceptions (BR)" },
  { key: "factures", label: "Factures fournisseur" },
  { key: "fournisseurs", label: "Fournisseurs" },
  { key: "suggestions", label: "Suggestions" },
  { key: "besoins", label: "Besoins (ventes)" },
];

const PRIORITY_LABELS: Record<string, { label: string; className: string }> = {
  low: { label: "Basse", className: "bg-gray-100 text-gray-600" },
  normal: { label: "Normale", className: "bg-blue-100 text-blue-700" },
  high: { label: "Haute", className: "bg-amber-100 text-amber-700" },
  urgent: { label: "Urgente", className: "bg-red-100 text-red-700" },
};

type LineDraft = {
  description: string;
  quantity: string;
  unit: string;
  price: string;
};

const EMPTY_LINE: LineDraft = {
  description: "",
  quantity: "1",
  unit: "u",
  price: "",
};

/** Message d'erreur backend (FastAPI detail) ou libellé par défaut. */
function errMsg(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d as { msg?: string })?.msg ?? JSON.stringify(d))
      .join(" — ");
  }
  return fallback;
}

/** Éditeur de lignes partagé (DA, BC, facture). */
function LineEditor({
  lines,
  setLines,
  priceLabel,
}: {
  lines: LineDraft[];
  setLines: (lines: LineDraft[]) => void;
  priceLabel: string;
}) {
  const update = (i: number, patch: Partial<LineDraft>) => {
    setLines(lines.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  };
  return (
    <div className="space-y-2">
      {lines.map((l, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2">
          <input
            className="min-w-52 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder="Désignation"
            value={l.description}
            onChange={(e) => update(i, { description: e.target.value })}
          />
          <input
            className="w-20 rounded-md border border-gray-300 px-2 py-2 text-right text-sm"
            type="number"
            min="0"
            step="any"
            title="Quantité"
            value={l.quantity}
            onChange={(e) => update(i, { quantity: e.target.value })}
          />
          <input
            className="w-20 rounded-md border border-gray-300 px-2 py-2 text-sm"
            placeholder="Unité"
            title="Unité"
            value={l.unit}
            onChange={(e) => update(i, { unit: e.target.value })}
          />
          <input
            className="w-32 rounded-md border border-gray-300 px-2 py-2 text-right text-sm"
            type="number"
            min="0"
            step="any"
            title={priceLabel}
            placeholder={priceLabel}
            value={l.price}
            onChange={(e) => update(i, { price: e.target.value })}
          />
          <Button
            type="button"
            variant="outline"
            className="px-2 py-1 text-xs"
            onClick={() => setLines(lines.filter((_, idx) => idx !== i))}
            disabled={lines.length === 1}
          >
            ✕
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        className="px-3 py-1 text-xs"
        onClick={() => setLines([...lines, { ...EMPTY_LINE }])}
      >
        + Ligne
      </Button>
    </div>
  );
}

export default function PurchasesPage() {
  const [tab, setTab] = useState<Tab>("demandes");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Achats</h1>
        <p className="text-sm text-gray-600">
          Demandes d&apos;achat, bons de commande, réceptions et factures
          fournisseur
        </p>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-b-2 border-gray-900 text-gray-900"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "demandes" && (
        <RequestsTab onConverted={() => setTab("commandes")} />
      )}
      {tab === "commandes" && <OrdersTab />}
      {tab === "receptions" && <ReceptionsTab />}
      {tab === "factures" && <InvoicesTab />}
      {tab === "fournisseurs" && <SuppliersTab />}
      {tab === "suggestions" && <SuggestionsTab />}
      {tab === "besoins" && <NeedsTab />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet : Demandes d'achat (DA)
// ---------------------------------------------------------------------------
async function runAction(
  fn: () => Promise<unknown>,
  fallback: string,
  setError: (msg: string | null) => void,
) {
  setError(null);
  try {
    await fn();
  } catch (err) {
    setError(errMsg(err, fallback));
  }
}

function RequestsTab({ onConverted }: { onConverted: () => void }) {
  const { data: requests = [], isLoading } = usePurchaseRequests();
  const { data: suppliers = [] } = useSuppliers();
  const create = useCreatePurchaseRequest();
  const submit = useSubmitPurchaseRequest();
  const approve = useApprovePurchaseRequest();
  const reject = useRejectPurchaseRequest();
  const remove = useDeletePurchaseRequest();
  const convert = useConvertRequestToOrder();
  const can = usePermission();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [supplierId, setSupplierId] = useState("");
  const [priority, setPriority] = useState("normal");
  const [neededBy, setNeededBy] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([{ ...EMPTY_LINE }]);
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const supplierName = (id: number | null) =>
    id == null ? "—" : (suppliers.find((s) => s.id === id)?.name ?? `#${id}`);

  const resetForm = () => {
    setSupplierId("");
    setPriority("normal");
    setNeededBy("");
    setLines([{ ...EMPTY_LINE }]);
  };

  const handleCreate = () =>
    runAction(
      async () => {
        const payloadLines = lines
          .map((l) => ({
            description: l.description.trim(),
            quantity: Number(l.quantity) || 0,
            unit: l.unit.trim() || "u",
            estimated_unit_price: Number(l.price) || 0,
          }))
          .filter((l) => l.description.length > 0);
        if (payloadLines.length === 0) {
          setError("Ajoutez au moins une ligne avec une désignation.");
          return;
        }
        await create.mutateAsync({
          supplier_id: supplierId ? Number(supplierId) : null,
          priority,
          needed_by: neededBy || null,
          lines: payloadLines,
        });
        resetForm();
        setShowForm(false);
      },
      "Création de la demande impossible",
      setError,
    );

  const handleReject = (requestId: number) =>
    runAction(
      async () => {
        if (!rejectReason.trim()) {
          setError("Indiquez un motif de rejet.");
          return;
        }
        await reject.mutateAsync({ id: requestId, reason: rejectReason.trim() });
        setRejectId(null);
        setRejectReason("");
      },
      "Rejet impossible",
      setError,
    );

  const handleDelete = async (number: string, requestId: number) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(
        `${number} — Seule une demande rejetée peut être supprimée.`,
      ),
    );
    if (!confirmed) return;
    await runAction(
      () => remove.mutateAsync(requestId),
      "Suppression impossible",
      setError,
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {requests.length} demande(s) — workflow soumission / approbation
        </p>
        {can("purchase_request:edit") && (
          <Button onClick={() => setShowForm((v) => !v)} variant="outline">
            {showForm ? "Fermer" : "+ Nouvelle demande"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">Nouvelle demande d&apos;achat</h2>
          <div className="flex flex-wrap gap-2">
            <select
              className="min-w-56 rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
            >
              <option value="">— Fournisseur (recommandé) —</option>
              {suppliers
                .filter((s) => s.is_active)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
            <select
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="low">Priorité basse</option>
              <option value="normal">Priorité normale</option>
              <option value="high">Priorité haute</option>
              <option value="urgent">Urgente</option>
            </select>
            <input
              type="date"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              title="Besoin avant le"
              value={neededBy}
              onChange={(e) => setNeededBy(e.target.value)}
            />
          </div>
          <LineEditor
            lines={lines}
            setLines={setLines}
            priceLabel="Prix estimé"
          />
          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Création…" : "Créer la demande"}
          </Button>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : requests.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucune demande d&apos;achat.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">N°</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Fournisseur</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Priorité</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Lignes</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Estimé</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {requests.map((r) => {
                const prio = PRIORITY_LABELS[r.priority] ?? {
                  label: r.priority,
                  className: "bg-gray-100 text-gray-600",
                };
                return (
                  <tr key={r.id} className="align-top hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">
                      {r.number}
                      {r.status === "rejected" && r.rejection_reason && (
                        <p className="text-xs font-normal text-red-500">
                          {r.rejection_reason}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2.5">{formatDate(r.request_date)}</td>
                    <td className="px-4 py-2.5">{supplierName(r.supplier_id)}</td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${prio.className}`}>
                        {prio.label}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right">{r.lines?.length ?? 0}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {formatCurrency(r.estimated_total)}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex flex-wrap items-center justify-end gap-1">
                        {r.status === "draft" && can("purchase_request:edit") && (
                          <Button
                            size="sm"
                            onClick={() =>
                              runAction(
                                () => submit.mutateAsync(r.id),
                                "Soumission impossible",
                                setError,
                              )
                            }
                          >
                            Soumettre
                          </Button>
                        )}
                        {r.status === "submitted" &&
                          can("purchase_request:approve") && (
                            <>
                              <Button
                                size="sm"
                                onClick={() =>
                                  runAction(
                                    () => approve.mutateAsync(r.id),
                                    "Approbation impossible",
                                    setError,
                                  )
                                }
                              >
                                Approuver
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setRejectId(r.id);
                                  setRejectReason("");
                                }}
                              >
                                Rejeter
                              </Button>
                            </>
                          )}
                        {r.status === "approved" && can("purchase_order:edit") && (
                          <Button
                            size="sm"
                            onClick={() =>
                              runAction(
                                async () => {
                                  await convert.mutateAsync(r.id);
                                  onConverted();
                                },
                                "Conversion impossible",
                                setError,
                              )
                            }
                          >
                            Convertir en BC
                          </Button>
                        )}
                        {r.status === "rejected" &&
                          can("purchase_request:delete") && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDelete(r.number, r.id)}
                            >
                              Supprimer
                            </Button>
                          )}
                      </div>
                      {rejectId === r.id && (
                        <div className="mt-1 flex justify-end gap-1">
                          <input
                            className="w-44 rounded-md border border-gray-300 px-2 py-1 text-xs"
                            placeholder="Motif du rejet"
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                          />
                          <Button
                            size="sm"
                            className="px-2 py-1 text-xs"
                            onClick={() => handleReject(r.id)}
                            disabled={reject.isPending}
                          >
                            OK
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="px-2 py-1 text-xs"
                            onClick={() => setRejectId(null)}
                          >
                            Annuler
                          </Button>
                        </div>
                      )}
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

// ---------------------------------------------------------------------------
// Onglet : Bons de commande (BC)
// ---------------------------------------------------------------------------
function OrdersTab() {
  const { data: orders = [], isLoading } = usePurchaseOrders();
  const { data: suppliers = [] } = useSuppliers();
  const create = useCreatePurchaseOrder();
  const submit = useSubmitPurchaseOrder();
  const confirmOrder = useConfirmPurchaseOrder();
  const cancelOrder = useCancelPurchaseOrder();
  const can = usePermission();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [supplierId, setSupplierId] = useState("");
  const [expectedDate, setExpectedDate] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([{ ...EMPTY_LINE }]);

  const supplierName = (id: number) =>
    suppliers.find((s) => s.id === id)?.name ?? `#${id}`;

  const handleCreate = () =>
    runAction(
      async () => {
        const payloadLines = lines
          .map((l) => ({
            description: l.description.trim(),
            quantity: Number(l.quantity) || 0,
            unit: l.unit.trim() || "u",
            unit_price: Number(l.price) || 0,
          }))
          .filter((l) => l.description.length > 0);
        if (payloadLines.length === 0) {
          setError("Ajoutez au moins une ligne avec une désignation.");
          return;
        }
        if (!supplierId) {
          setError("Choisissez un fournisseur.");
          return;
        }
        await create.mutateAsync({
          supplier_id: Number(supplierId),
          expected_date: expectedDate || null,
          lines: payloadLines,
        });
        setSupplierId("");
        setExpectedDate("");
        setLines([{ ...EMPTY_LINE }]);
        setShowForm(false);
      },
      "Création du bon de commande impossible",
      setError,
    );

  const handleCancel = async (number: string, orderId: number) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(`${number} — Annuler ce bon de commande ?`),
    );
    if (!confirmed) return;
    await runAction(
      () => cancelOrder.mutateAsync(orderId),
      "Annulation impossible",
      setError,
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {orders.length} bon(aux) de commande — les DA approuvées se convertissent
          depuis l&apos;onglet Demandes
        </p>
        {can("purchase_order:edit") && (
          <Button onClick={() => setShowForm((v) => !v)} variant="outline">
            {showForm ? "Fermer" : "+ Nouvelle commande"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">Nouveau bon de commande</h2>
          <div className="flex flex-wrap gap-2">
            <select
              className="min-w-56 rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
            >
              <option value="">— Fournisseur —</option>
              {suppliers
                .filter((s) => s.is_active)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
            <input
              type="date"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              title="Date prévue"
              value={expectedDate}
              onChange={(e) => setExpectedDate(e.target.value)}
            />
          </div>
          <LineEditor lines={lines} setLines={setLines} priceLabel="Prix unitaire" />
          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Création…" : "Créer le bon de commande"}
          </Button>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : orders.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucun bon de commande.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">N°</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Fournisseur</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Prévu le</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Lignes</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Total TTC</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {orders.map((o) => (
                <tr key={o.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-medium text-gray-900">
                    {o.number}
                    {o.origin_request_id && (
                      <span className="ml-1 text-xs text-gray-400">
                        (DA #{o.origin_request_id})
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">{supplierName(o.supplier_id)}</td>
                  <td className="px-4 py-2.5">{formatDate(o.order_date)}</td>
                  <td className="px-4 py-2.5">{formatDate(o.expected_date)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {o.lines?.length ?? 0}
                    {(o.lines ?? []).some((l) => l.quantity_received > 0) && (
                      <span className="ml-1 text-xs text-green-600">reçu</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {formatCurrency(o.amount_total)}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={o.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap justify-end gap-1">
                      {o.status === "draft" && can("purchase_order:edit") && (
                        <Button
                          size="sm"
                          onClick={() =>
                            runAction(
                              () => submit.mutateAsync(o.id),
                              "Soumission impossible",
                              setError,
                            )
                          }
                        >
                          Soumettre
                        </Button>
                      )}
                      {o.status === "pending" && can("purchase_order:confirm") && (
                        <Button
                          size="sm"
                          onClick={() =>
                            runAction(
                              () => confirmOrder.mutateAsync(o.id),
                              "Confirmation impossible",
                              setError,
                            )
                          }
                        >
                          Confirmer
                        </Button>
                      )}
                      {(o.status === "draft" || o.status === "pending") &&
                        can("purchase_order:cancel") && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCancel(o.number, o.id)}
                          >
                            Annuler
                          </Button>
                        )}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      title="Télécharger le PDF"
                      onClick={() => printPurchaseOrder(o.id)}
                    >
                      <svg
                        className="w-3.5 h-3.5"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                      PDF
                    </Button>
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

// ---------------------------------------------------------------------------
// Onglet : Réceptions (BR)
// ---------------------------------------------------------------------------
function ReceptionsTab() {
  const { data: receptions = [], isLoading } = usePurchaseReceptions();
  const { data: orders = [] } = usePurchaseOrders();
  const { data: warehouses = [] } = useWarehouses();
  const create = useCreatePurchaseReception();
  const validate = useValidatePurchaseReception();
  const can = usePermission();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [orderId, setOrderId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  // Quantités saisies par ligne de BC (clé = order_line_id) ; vide = restant.
  const [qtys, setQtys] = useState<Record<number, string>>({});

  // BC ouverts (confirmés, partiellement reçus ou reçus partiellement)
  const openOrders = orders.filter(
    (o) => o.status === "confirmed" || o.status === "partially_received",
  );

  const { data: orderLines = [] } = usePurchaseOrderLines(
    orderId ? Number(orderId) : null,
  );

  const handleCreate = () =>
    runAction(
      async () => {
        if (!orderId) return setError("Choisissez un bon de commande.");
        if (!warehouseId) return setError("Choisissez un entrepôt.");
        const payloadLines = orderLines
          .map((l) => ({
            order_line_id: l.id,
            description: l.description,
            quantity: Number(qtys[l.id] ?? l.quantity_remaining) || 0,
          }))
          .filter((l) => l.quantity > 0);
        if (payloadLines.length === 0) {
          setError("Aucune quantité à recevoir.");
          return;
        }
        await create.mutateAsync({
          order_id: Number(orderId),
          warehouse_id: Number(warehouseId),
          lines: payloadLines,
        });
        setOrderId("");
        setQtys({});
        setShowForm(false);
      },
      "Création de la réception impossible",
      setError,
    );

  const warehouseName = (id: number) =>
    warehouses.find((w) => w.id === id)?.name ?? `#${id}`;

  const orderNumber = (id: number) =>
    orders.find((o) => o.id === id)?.number ?? `#${id}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {receptions.length} réception(s) — validation = mouvement de stock
          entrant
        </p>
        {can("purchase_reception:create") && (
          <Button onClick={() => setShowForm((v) => !v)} variant="outline">
            {showForm ? "Fermer" : "+ Nouvelle réception"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">Nouvelle réception (BR)</h2>
          <div className="flex flex-wrap gap-2">
            <select
              className="min-w-64 rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={orderId}
              onChange={(e) => {
                setOrderId(e.target.value);
                setQtys({});
              }}
            >
              <option value="">— Bon de commande confirmé —</option>
              {openOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.number}
                </option>
              ))}
            </select>
            <select
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
            >
              <option value="">— Entrepôt —</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>

          {orderId && orderLines.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase text-gray-500">
                Quantités reçues (restant par défaut)
              </p>
              {orderLines.map((l) => (
                <div
                  key={l.id}
                  className="flex flex-wrap items-center gap-2 text-sm"
                >
                  <span className="min-w-52 flex-1 text-gray-800">
                    {l.description ?? `Ligne #${l.id}`}
                  </span>
                  <span className="text-xs text-gray-400">
                    restant : {l.quantity_remaining} {l.unit ?? ""}
                  </span>
                  <input
                    className="w-24 rounded-md border border-gray-300 px-2 py-1.5 text-right text-sm"
                    type="number"
                    min="0"
                    step="any"
                    title="Quantité reçue"
                    value={qtys[l.id] ?? String(l.quantity_remaining)}
                    onChange={(e) =>
                      setQtys({ ...qtys, [l.id]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          )}

          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Création…" : "Créer la réception"}
          </Button>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : receptions.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucune réception.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">N°</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Bon de commande</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Entrepôt</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Lignes</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {receptions.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-medium text-gray-900">
                    {r.number}
                  </td>
                  <td className="px-4 py-2.5">{orderNumber(r.order_id)}</td>
                  <td className="px-4 py-2.5">{warehouseName(r.warehouse_id)}</td>
                  <td className="px-4 py-2.5">{formatDate(r.reception_date)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {r.lines?.length ?? 0}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {r.status === "draft" &&
                      can("purchase_reception:validate") && (
                        <Button
                          size="sm"
                          onClick={() =>
                            runAction(
                              () => validate.mutateAsync(r.id),
                              "Validation impossible",
                              setError,
                            )
                          }
                        >
                          Valider
                        </Button>
                      )}
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

// ---------------------------------------------------------------------------
// Onglet : Factures fournisseur
// ---------------------------------------------------------------------------
type InvoiceLinePayload = {
  order_line_id?: number;
  description?: string | null;
  quantity: number;
  unit_price: number;
  tax_rate?: number;
};

function InvoicesTab() {
  const { data: invoices = [], isLoading } = useSupplierInvoices();
  const { data: suppliers = [] } = useSuppliers();
  const { data: orders = [] } = usePurchaseOrders();
  const create = useCreateSupplierInvoice();
  const matchInv = useMatchSupplierInvoice();
  const postInv = usePostSupplierInvoice();
  const payInv = usePaySupplierInvoice();
  const can = usePermission();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [supplierId, setSupplierId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [supplierRef, setSupplierRef] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [freeLines, setFreeLines] = useState<LineDraft[]>([{ ...EMPTY_LINE }]);
  const [qtys, setQtys] = useState<Record<number, string>>({});
  const [prices, setPrices] = useState<Record<number, string>>({});
  const [matchView, setMatchView] = useState<{
    invoiceId: number;
    result: MatchingResult;
  } | null>(null);
  const [payId, setPayId] = useState<number | null>(null);
  const [payAmount, setPayAmount] = useState("");

  const { data: orderLines = [] } = usePurchaseOrderLines(
    orderId ? Number(orderId) : null,
  );

  const supplierName = (id: number) =>
    suppliers.find((s) => s.id === id)?.name ?? `#${id}`;

  // BC du fournisseur sélectionné (hors brouillon / annulés)
  const supplierOrders = orders.filter(
    (o) =>
      Number(supplierId) > 0 &&
      o.supplier_id === Number(supplierId) &&
      !["draft", "pending", "cancelled"].includes(o.status),
  );

  const handleCreate = () =>
    runAction(
      async () => {
        if (!supplierId) {
          setError("Choisissez un fournisseur.");
          return;
        }
        let payloadLines: InvoiceLinePayload[];
        if (orderId) {
          payloadLines = orderLines.map((l) => ({
            order_line_id: l.id,
            description: l.description,
            quantity: Number(qtys[l.id] ?? l.quantity) || 0,
            unit_price: Number(prices[l.id] ?? l.unit_price) || 0,
            tax_rate: l.tax_rate,
          }));
        } else {
          payloadLines = freeLines
            .map((l) => ({
              description: l.description.trim(),
              quantity: Number(l.quantity) || 0,
              unit_price: Number(l.price) || 0,
              tax_rate: 0,
            }))
            .filter((l) => (l.description ?? "").length > 0);
        }
        if (payloadLines.length === 0) {
          setError("Ajoutez au moins une ligne avec une désignation.");
          return;
        }
        await create.mutateAsync({
          supplier_id: Number(supplierId),
          order_id: orderId ? Number(orderId) : null,
          supplier_invoice_number: supplierRef || null,
          invoice_date: invoiceDate || null,
          due_date: dueDate || null,
          lines: payloadLines,
        });
        setSupplierId("");
        setOrderId("");
        setSupplierRef("");
        setInvoiceDate("");
        setDueDate("");
        setQtys({});
        setPrices({});
        setFreeLines([{ ...EMPTY_LINE }]);
        setShowForm(false);
      },
      "Création de la facture impossible",
      setError,
    );

  const handleMatch = (invoiceId: number) =>
    runAction(
      async () => {
        const result = await matchInv.mutateAsync(invoiceId);
        setMatchView({ invoiceId, result });
      },
      "Rapprochement impossible",
      setError,
    );

  const handlePay = (invoiceId: number) =>
    runAction(
      async () => {
        const amount = Number(payAmount);
        if (!amount || amount <= 0) {
          setError("Indiquez le montant réglé.");
          return;
        }
        await payInv.mutateAsync({ id: invoiceId, data: { amount } });
        setPayId(null);
        setPayAmount("");
      },
      "Règlement impossible",
      setError,
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {invoices.length} facture(s) — rapprochement 3 voies, comptabilisation
          et règlements
        </p>
        {can("purchase_invoice:edit") && (
          <Button onClick={() => setShowForm((v) => !v)} variant="outline">
            {showForm ? "Fermer" : "+ Nouvelle facture"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">Nouvelle facture fournisseur</h2>
          <div className="flex flex-wrap gap-2">
            <select
              className="min-w-56 rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={supplierId}
              onChange={(e) => {
                setSupplierId(e.target.value);
                setOrderId("");
                setQtys({});
                setPrices({});
              }}
            >
              <option value="">— Fournisseur —</option>
              {suppliers
                .filter((s) => s.is_active)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
            <select
              className="min-w-64 rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={orderId}
              onChange={(e) => {
                setOrderId(e.target.value);
                setQtys({});
                setPrices({});
              }}
            >
              <option value="">— Facture libre (sans BC) —</option>
              {supplierOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.number}
                </option>
              ))}
            </select>
            <input
              className="w-44 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="N° facture fournisseur"
              value={supplierRef}
              onChange={(e) => setSupplierRef(e.target.value)}
            />
            <input
              type="date"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              title="Date de facture"
              value={invoiceDate}
              onChange={(e) => setInvoiceDate(e.target.value)}
            />
            <input
              type="date"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              title="Échéance"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          {orderId ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase text-gray-500">
                Lignes du bon de commande (quantités et prix modifiables)
              </p>
              {orderLines.map((l) => (
                <div
                  key={l.id}
                  className="flex flex-wrap items-center gap-2 text-sm"
                >
                  <span className="min-w-52 flex-1 text-gray-800">
                    {l.description ?? `Ligne #${l.id}`}
                  </span>
                  <input
                    className="w-24 rounded-md border border-gray-300 px-2 py-1.5 text-right text-sm"
                    type="number"
                    min="0"
                    step="any"
                    title="Quantité facturée"
                    value={qtys[l.id] ?? String(l.quantity)}
                    onChange={(e) => setQtys({ ...qtys, [l.id]: e.target.value })}
                  />
                  <input
                    className="w-32 rounded-md border border-gray-300 px-2 py-1.5 text-right text-sm"
                    type="number"
                    min="0"
                    step="any"
                    title="Prix unitaire facturé"
                    value={prices[l.id] ?? String(l.unit_price)}
                    onChange={(e) =>
                      setPrices({ ...prices, [l.id]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          ) : (
            <LineEditor lines={freeLines} setLines={setFreeLines} priceLabel="Prix HT" />
          )}

          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Création…" : "Créer la facture"}
          </Button>
        </Card>
      )}

      {matchView && (
        <Card className="space-y-2 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">
              Rapprochement —{" "}
              {invoices.find((i) => i.id === matchView.invoiceId)?.reference ??
                `#${matchView.invoiceId}`}
            </h3>
            <Button size="sm" variant="outline" onClick={() => setMatchView(null)}>
              Fermer
            </Button>
          </div>
          <p className="flex items-center gap-2 text-sm text-gray-600">
            Statut : <StatusBadge status={matchView.result.status} />
          </p>
          <p className="text-sm text-gray-600">
            Commandé : {formatCurrency(matchView.result.ordered_total ?? null)} —
            Facturé : {formatCurrency(matchView.result.invoiced_total ?? null)}
          </p>
          {(matchView.result.lines ?? []).some(
            (l) => (l.issues ?? []).length > 0,
          ) && (
            <ul className="list-inside list-disc text-sm">
              {(matchView.result.lines ?? [])
                .filter((l) => (l.issues ?? []).length > 0)
                .map((l, i) => (
                  <li key={i} className="text-amber-700">
                    {l.description ?? `Ligne ${i + 1}`} :{" "}
                    {(l.issues ?? []).join(", ")}
                  </li>
                ))}
            </ul>
          )}
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : invoices.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucune facture fournisseur.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Référence</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Fournisseur</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Total TTC</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Reste dû</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Rapprochement</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {invoices.map((inv) => (
                <tr key={inv.id} className="align-top hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-medium text-gray-900">
                    {inv.reference}
                    {inv.supplier_invoice_number && (
                      <p className="text-xs font-normal text-gray-400">
                        N° fournisseur : {inv.supplier_invoice_number}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-2.5">{supplierName(inv.supplier_id)}</td>
                  <td className="px-4 py-2.5">
                    {formatDate(inv.invoice_date)}
                    {inv.due_date && (
                      <p className="text-xs text-gray-400">
                        échéance {formatDate(inv.due_date)}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {formatCurrency(inv.amount_total)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {formatCurrency(inv.amount_due)}
                  </td>
                  <td className="px-4 py-2.5">
                    {inv.matching_status ? (
                      <StatusBadge status={inv.matching_status} />
                    ) : (
                      <span className="text-xs text-gray-400">
                        non rapprochée
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      {inv.status === "draft" && can("purchase_invoice:edit") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleMatch(inv.id)}
                          disabled={matchInv.isPending}
                        >
                          Rapprocher
                        </Button>
                      )}
                      {inv.status === "draft" && can("purchase_invoice:post") && (
                        <Button
                          size="sm"
                          onClick={() =>
                            runAction(
                              () => postInv.mutateAsync(inv.id),
                              "Comptabilisation impossible",
                              setError,
                            )
                          }
                        >
                          Comptabiliser
                        </Button>
                      )}
                      {(inv.status === "posted" ||
                        inv.status === "partially_paid") &&
                        can("purchase_invoice:pay") && (
                          <Button
                            size="sm"
                            onClick={() => {
                              setPayId(inv.id);
                              setPayAmount(String(inv.amount_due));
                            }}
                          >
                            Régler
                          </Button>
                        )}
                    </div>
                    {payId === inv.id && (
                      <div className="mt-1 flex justify-end gap-1">
                        <input
                          className="w-28 rounded-md border border-gray-300 px-2 py-1 text-right text-xs"
                          type="number"
                          min="0"
                          step="any"
                          title="Montant réglé"
                          value={payAmount}
                          onChange={(e) => setPayAmount(e.target.value)}
                        />
                        <Button
                          size="sm"
                          className="px-2 py-1 text-xs"
                          onClick={() => handlePay(inv.id)}
                          disabled={payInv.isPending}
                        >
                          OK
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          onClick={() => setPayId(null)}
                        >
                          Annuler
                        </Button>
                      </div>
                    )}
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

// ---------------------------------------------------------------------------
// Onglet : Fournisseurs
// ---------------------------------------------------------------------------
function SuppliersTab() {
  const { data: suppliers = [], isLoading } = useSuppliers();
  const create = useCreateSupplier();
  const update = useUpdateSupplier();
  const remove = useDeleteSupplier();
  const rate = useRateSupplier();
  const can = usePermission();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [terms, setTerms] = useState("");
  const [delay, setDelay] = useState("");
  const [rateId, setRateId] = useState<number | null>(null);
  const [rateValue, setRateValue] = useState("3");

  const resetForm = () => {
    setEditId(null);
    setName("");
    setCode("");
    setPhone("");
    setEmail("");
    setTerms("");
    setDelay("");
  };

  const openEdit = (s: (typeof suppliers)[number]) => {
    setEditId(s.id);
    setName(s.name);
    setCode(s.code ?? "");
    setPhone(s.phone ?? "");
    setEmail(s.email ?? "");
    setTerms(s.payment_terms_days != null ? String(s.payment_terms_days) : "");
    setDelay(s.delivery_days != null ? String(s.delivery_days) : "");
    setShowForm(true);
  };

  const handleSave = () =>
    runAction(
      async () => {
        if (!name.trim()) {
          setError("Le nom est obligatoire.");
          return;
        }
        const payload = {
          name: name.trim(),
          code: code.trim() || null,
          phone: phone.trim() || null,
          email: email.trim() || null,
          payment_terms_days: terms ? Number(terms) : null,
          delivery_days: delay ? Number(delay) : null,
        };
        if (editId) {
          await update.mutateAsync({ id: editId, data: payload });
        } else {
          await create.mutateAsync(payload);
        }
        resetForm();
        setShowForm(false);
      },
      editId ? "Mise à jour impossible" : "Création impossible",
      setError,
    );

  const handleRate = (supplierId: number) =>
    runAction(
      async () => {
        const value = Number(rateValue);
        if (!value || value < 1 || value > 5) {
          setError("La note doit être comprise entre 1 et 5.");
          return;
        }
        await rate.mutateAsync({ id: supplierId, rating: value });
        setRateId(null);
      },
      "Notation impossible",
      setError,
    );

  const handleDelete = async (supplierName: string, supplierId: number) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(`${supplierName} — Supprimer ce fournisseur ?`),
    );
    if (!confirmed) return;
    await runAction(
      () => remove.mutateAsync(supplierId),
      "Suppression impossible",
      setError,
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">{suppliers.length} fournisseur(s)</p>
        {can("purchase:create") && (
          <Button
            variant="outline"
            onClick={() => {
              resetForm();
              setShowForm((v) => !v);
            }}
          >
            {showForm ? "Fermer" : "+ Nouveau fournisseur"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">
            {editId ? "Modifier le fournisseur" : "Nouveau fournisseur"}
          </h2>
          <div className="flex flex-wrap gap-2">
            <input
              className="min-w-56 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Nom *"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="w-32 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <input
              className="w-44 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Téléphone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <input
              className="w-56 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              className="w-36 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Délai paiement (j)"
              type="number"
              min="0"
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
            />
            <input
              className="w-36 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Délai livraison (j)"
              type="number"
              min="0"
              value={delay}
              onChange={(e) => setDelay(e.target.value)}
            />
          </div>
          <Button onClick={handleSave} disabled={create.isPending || update.isPending}>
            {editId ? "Mettre à jour" : "Créer le fournisseur"}
          </Button>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : suppliers.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucun fournisseur.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Nom</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Code</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Contact</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Délai livr.</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Note</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Actif</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {suppliers.map((s) => (
                <tr key={s.id} className="align-top hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-medium text-gray-900">{s.name}</td>
                  <td className="px-4 py-2.5">{s.code ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    {s.phone ?? "—"}
                    {s.email && <p className="text-xs text-gray-400">{s.email}</p>}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {s.delivery_days != null ? `${s.delivery_days} j` : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    {s.rating != null ? (
                      <span className="text-amber-500">
                        {"★".repeat(Math.round(s.rating))}
                        {"☆".repeat(5 - Math.round(s.rating))}
                        <span className="ml-1 text-xs text-gray-500">
                          ({Number(s.rating).toFixed(1)})
                        </span>
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">non noté</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {s.is_active ? (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                        Oui
                      </span>
                    ) : (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        Non
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      {can("purchase:edit") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openEdit(s)}
                        >
                          Modifier
                        </Button>
                      )}
                      {can("purchase:edit") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setRateId(s.id);
                            setRateValue(
                              s.rating != null ? String(s.rating) : "3",
                            );
                          }}
                        >
                          Noter
                        </Button>
                      )}
                      {can("purchase:delete") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDelete(s.name, s.id)}
                        >
                          Supprimer
                        </Button>
                      )}
                    </div>
                    {rateId === s.id && (
                      <div className="mt-1 flex justify-end gap-1">
                        <select
                          className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                          value={rateValue}
                          onChange={(e) => setRateValue(e.target.value)}
                        >
                          {[1, 2, 3, 4, 5].map((v) => (
                            <option key={v} value={v}>
                              {v} / 5
                            </option>
                          ))}
                        </select>
                        <Button
                          size="sm"
                          className="px-2 py-1 text-xs"
                          onClick={() => handleRate(s.id)}
                          disabled={rate.isPending}
                        >
                          OK
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          onClick={() => setRateId(null)}
                        >
                          Annuler
                        </Button>
                      </div>
                    )}
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

// ---------------------------------------------------------------------------
// Onglet : Suggestions (note, délai, dernier prix)
// ---------------------------------------------------------------------------
function SuggestTable({
  items,
  loading,
}: {
  items: {
    id: number;
    name: string;
    rating: number | null;
    delivery_days: number | null;
    last_price: number | null;
  }[];
  loading: boolean;
}) {
  if (loading) {
    return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  }
  if (items.length === 0) {
    return (
      <p className="p-8 text-center text-sm text-gray-500">
        Aucune suggestion — l&apos;historique se remplit avec vos achats.
      </p>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-gray-100 bg-gray-50">
        <tr>
          <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Nom</th>
          <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Note</th>
          <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Délai</th>
          <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Dernier prix</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-50">
        {items.map((s) => (
          <tr key={s.id} className="hover:bg-gray-50">
            <td className="px-4 py-2.5 font-medium text-gray-900">{s.name}</td>
            <td className="px-4 py-2.5">
              {s.rating != null ? `${Number(s.rating).toFixed(1)} / 5` : "—"}
            </td>
            <td className="px-4 py-2.5 text-right">
              {s.delivery_days != null ? `${s.delivery_days} j` : "—"}
            </td>
            <td className="px-4 py-2.5 text-right tabular-nums">
              {s.last_price != null ? formatCurrency(s.last_price) : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SuggestionsTab() {
  const { data: supSuggestions = [], isLoading: loadingSup } =
    useSupplierSuggestions();
  const { data: prodSuggestions = [], isLoading: loadingProd } =
    usePriceSuggestions();

  return (
    <div className="space-y-4">
      <Card className="overflow-x-auto p-0">
        <h2 className="px-4 pt-4 font-semibold text-gray-800">
          Fournisseurs suggérés
        </h2>
        <p className="px-4 pb-2 text-sm text-gray-600">
          Classement selon la note, le délai de livraison et le dernier prix
          constaté.
        </p>
        <SuggestTable items={supSuggestions} loading={loadingSup} />
      </Card>
      <Card className="overflow-x-auto p-0">
        <h2 className="px-4 pt-4 font-semibold text-gray-800">
          Historique de prix par produit
        </h2>
        <p className="px-4 pb-2 text-sm text-gray-600">
          Derniers prix d&apos;achat observés pour préparer vos négociations.
        </p>
        <SuggestTable items={prodSuggestions} loading={loadingProd} />
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet : Besoins issus des ventes (commandes confirmées)
// ---------------------------------------------------------------------------
function NeedsTab() {
  const { data: orders = [], isLoading } = useOrders();
  const { data: products = [] } = useProducts();

  // Agrège les besoins d'achat de toutes les commandes confirmées
  const byProduct = new Map<
    number,
    { name: string; quantity: number; sellByLength: boolean }
  >();
  for (const o of orders) {
    if (o.status !== "confirmed") continue;
    for (const l of o.lines ?? []) {
      const toBuy = Number(l.quantity_to_purchase ?? 0);
      if (toBuy <= 0 || !l.product_id) continue;
      const existing = byProduct.get(l.product_id);
      const name =
        l.description ??
        products.find((p) => p.id === l.product_id)?.name ??
        `#${l.product_id}`;
      if (existing) {
        existing.quantity += toBuy;
      } else {
        byProduct.set(l.product_id, {
          name,
          quantity: toBuy,
          sellByLength: l.sell_by_length,
        });
      }
    }
  }
  const needs = [...byProduct.entries()].map(([productId, info]) => ({
    productId,
    ...info,
  }));

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Besoins d&apos;achat issus des commandes confirmées (à acheter auprès
        des fournisseurs).
      </p>
      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : needs.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucun besoin d&apos;achat en cours.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Produit</th>
                <th className="px-4 py-3 text-right">Quantité à acheter</th>
              </tr>
            </thead>
            <tbody>
              {needs.map((n) => (
                <tr
                  key={n.productId}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {n.name}
                    {n.sellByLength && (
                      <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                        au m
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-orange-600">
                    {n.quantity}
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











