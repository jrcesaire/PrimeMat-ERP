/**
 * Page Ventes — liste des devis et commandes client.
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  FileText,
  ShoppingCart,
  CheckCircle2,
  Printer,
  Pencil,
  Trash2,
  Eye,
  Undo2,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useQuotes,
  useOrders,
  useConfirmQuote,
  useDeleteQuote,
  useDeleteOrder,
  useOrderBackToDraft,
  useQuoteBackToDraft,
  SALES_KEYS,
} from "@/hooks/useSales";
import { usePartners } from "@/hooks/useCRM";
import type { Partner, Quote, SalesOrder } from "@/lib/types";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";
import { printQuote, printOrder } from "@/lib/api/pdf";

/** Nombre de lignes par page (pagination façon Odoo). */
const PAGE_SIZE = 25;

interface ListDoc {
  id: number;
  reference: string;
  partner_id: number;
  status: string;
}

/** Filtre + tri (plus récents d'abord) d'une liste de documents. */
function filterDocs<T extends ListDoc>(
  list: T[],
  search: string,
  statusFilter: "all" | "draft" | "confirmed",
  partnerMap: Map<number, Partner>,
): T[] {
  let out = list;
  if (statusFilter !== "all") out = out.filter((d) => d.status === statusFilter);
  const q = search.trim().toLowerCase();
  if (q) {
    out = out.filter((d) => {
      const p = partnerMap.get(d.partner_id);
      return (
        d.reference.toLowerCase().includes(q) ||
        (p?.name ?? "").toLowerCase().includes(q) ||
        (p?.phone ?? "").includes(q)
      );
    });
  }
  return [...out].sort((a, b) => b.id - a.id);
}

export default function SalesPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"quotes" | "orders">("quotes");
  const { data: quotes = [], isLoading: loadingQuotes } = useQuotes();
  const { data: orders = [], isLoading: loadingOrders } = useOrders();
  const { data: partners = [] } = usePartners();
  const confirmQuote = useConfirmQuote();
  const deleteQuote = useDeleteQuote();
  const quoteBackToDraft = useQuoteBackToDraft();
  const deleteOrder = useDeleteOrder();
  const orderBackToDraft = useOrderBackToDraft();
  const queryClient = useQueryClient();

  // --- Recherche, filtres, sélection et pagination (façon Odoo) ---
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "confirmed">("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const partnerMap = useMemo(
    () => new Map(partners.map((p) => [p.id, p])),
    [partners]
  );
  const partnerName = (id: number) =>
    partnerMap.get(id)?.name ?? `Partenaire #${id}`;
  const partnerPhone = (id: number) => partnerMap.get(id)?.phone ?? null;

  const filteredQuotes = useMemo(
    () => filterDocs(quotes, search, statusFilter, partnerMap),
    [quotes, search, statusFilter, partnerMap]
  );
  const filteredOrders = useMemo(
    () => filterDocs(orders, search, statusFilter, partnerMap),
    [orders, search, statusFilter, partnerMap]
  );

  const docs = tab === "quotes" ? filteredQuotes : filteredOrders;
  const totalPages = Math.max(1, Math.ceil(docs.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageSlice = docs.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const quotesPage = tab === "quotes" ? (pageSlice as Quote[]) : [];
  const ordersPage = tab === "orders" ? (pageSlice as SalesOrder[]) : [];

  const switchTab = (t: "quotes" | "orders") => {
    setTab(t);
    setPage(1);
    setSelected(new Set());
  };

  const toggleAllOnPage = (checked: boolean) => {
    const s = new Set(selected);
    pageSlice.forEach((d) => (checked ? s.add(d.id) : s.delete(d.id)));
    setSelected(s);
  };

  const handleConfirm = async (quoteId: number) => {
    try {
      await confirmQuote.mutateAsync(quoteId);
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
      setTab("orders");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la confirmation du devis");
    }
  };

  const handleDelete = async (quoteId: number, reference: string) => {
    if (!window.confirm(`Supprimer définitivement le devis ${reference} ?`)) return;
    try {
      await deleteQuote.mutateAsync(quoteId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la suppression du devis");
    }
  };

  const handleDeleteOrder = async (orderId: number, reference: string) => {
    if (!window.confirm(`Supprimer définitivement la commande ${reference} ?`)) return;
    try {
      await deleteOrder.mutateAsync(orderId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la suppression de la commande");
    }
  };

  const handleBackToDraft = async (orderId: number, reference: string) => {
    if (
      !window.confirm(
        `Remettre la commande ${reference} au brouillon ? Les réservations de stock seront libérées.`,
      )
    )
      return;
    try {
      await orderBackToDraft.mutateAsync(orderId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la remise au brouillon");
    }
  };

  const handleQuoteBackToDraft = async (quoteId: number, reference: string) => {
    if (!window.confirm(`Remettre le devis ${reference} au brouillon ?`)) return;
    try {
      await quoteBackToDraft.mutateAsync(quoteId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la remise du devis au brouillon");
    }
  };

  // --- Actions groupées ---
  const handleBulkConfirmQuotes = async () => {
    const targets = quotes.filter((q) => selected.has(q.id) && q.status === "draft");
    if (targets.length === 0) return;
    if (
      !window.confirm(
        `Confirmer ${targets.length} devis ? Une commande sera créée pour chacun.`
      )
    )
      return;
    let ok = 0;
    let fail = 0;
    for (const t of targets) {
      try {
        await confirmQuote.mutateAsync(t.id);
        ok++;
      } catch {
        fail++;
      }
    }
    setSelected(new Set());
    if (ok > 0) setTab("orders");
    alert(`${ok} devis confirmé(s).${fail ? ` ${fail} échec(s).` : ""}`);
  };

  const handleBulkDeleteQuotes = async () => {
    const targets = quotes.filter((q) => selected.has(q.id) && q.status === "draft");
    if (targets.length === 0) {
      alert("Seuls les devis brouillons peuvent être supprimés.");
      return;
    }
    if (!window.confirm(`Supprimer définitivement ${targets.length} devis ?`)) return;
    let fail = 0;
    for (const t of targets) {
      try {
        await deleteQuote.mutateAsync(t.id);
      } catch {
        fail++;
      }
    }
    setSelected(new Set());
    if (fail > 0) alert(`${fail} suppression(s) ont échoué.`);
  };

  const handleBulkDeleteOrders = async () => {
    const targets = orders.filter((o) => selected.has(o.id) && o.status === "draft");
    if (targets.length === 0) {
      alert("Seules les commandes brouillons peuvent être supprimées.");
      return;
    }
    if (
      !window.confirm(`Supprimer définitivement ${targets.length} commande(s) brouillon(s) ?`)
    )
      return;
    let fail = 0;
    for (const t of targets) {
      try {
        await deleteOrder.mutateAsync(t.id);
      } catch {
        fail++;
      }
    }
    setSelected(new Set());
    if (fail > 0) alert(`${fail} suppression(s) ont échoué.`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ventes</h1>
          <p className="text-sm text-gray-600">Devis et commandes clients</p>
        </div>
        <Link href="/dashboard/sales/quotes/new">
          <Button className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Nouveau devis
          </Button>
        </Link>
      </div>

      {/* Onglets */}
      <div className="flex gap-4 border-b border-gray-200">
        <button
          onClick={() => switchTab("quotes")}
          className={`flex items-center gap-2 border-b-2 px-4 pb-2 text-sm font-medium ${
            tab === "quotes"
              ? "border-primary text-primary"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <FileText className="h-4 w-4" />
          Devis ({quotes.length})
        </button>
        <button
          onClick={() => switchTab("orders")}
          className={`flex items-center gap-2 border-b-2 px-4 pb-2 text-sm font-medium ${
            tab === "orders"
              ? "border-primary text-primary"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <ShoppingCart className="h-4 w-4" />
          Commandes ({orders.length})
        </button>
      </div>

      {/* Barre d'outils — recherche, filtres, pagination (façon Odoo) */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Rechercher : référence, client, téléphone…"
            className="h-9 w-full rounded-md border border-gray-300 bg-white pl-9 pr-8 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
          {search && (
            <button
              onClick={() => {
                setSearch("");
                setPage(1);
              }}
              aria-label="Effacer la recherche"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {(
            [
              ["all", "Tous"],
              ["draft", "Brouillons"],
              ["confirmed", "Confirmés"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => {
                setStatusFilter(value);
                setPage(1);
              }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                statusFilter === value
                  ? "bg-primary text-white"
                  : "border border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-gray-500">
          {docs.length === 0
            ? "0 résultat"
            : `${(safePage - 1) * PAGE_SIZE + 1}–${Math.min(safePage * PAGE_SIZE, docs.length)} / ${docs.length}`}
        </span>
      </div>

      {/* Barre d'actions groupées */}
      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm">
          <span className="font-medium text-blue-900">
            {selected.size} sélectionné(s)
          </span>
          {tab === "quotes" ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleBulkConfirmQuotes}
                disabled={confirmQuote.isPending}
              >
                Confirmer la sélection
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-red-600 hover:bg-red-50"
                onClick={handleBulkDeleteQuotes}
                disabled={deleteQuote.isPending}
              >
                Supprimer
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="text-red-600 hover:bg-red-50"
              onClick={handleBulkDeleteOrders}
              disabled={deleteOrder.isPending}
            >
              Supprimer
            </Button>
          )}
          <button
            className="ml-auto text-xs text-gray-500 hover:text-gray-700"
            onClick={() => setSelected(new Set())}
          >
            Annuler la sélection
          </button>
        </div>
      )}

      {/* Devis */}
      {tab === "quotes" && (
        <Card className="overflow-hidden p-0">
          {loadingQuotes ? (
            <p className="p-6 text-sm text-gray-500">Chargement…</p>
          ) : quotes.length === 0 ? (
            <div className="p-10 text-center">
              <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">Aucun devis pour le moment.</p>
              <Link href="/dashboard/sales/quotes/new" className="mt-3 inline-block">
                <Button size="sm">Créer le premier devis</Button>
              </Link>
            </div>
          ) : filteredQuotes.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-sm text-gray-500">
                Aucun devis ne correspond à la recherche ou au filtre.
              </p>
            </div>
          ) : (
            <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label="Tout sélectionner sur la page"
                      checked={
                        quotesPage.length > 0 &&
                        quotesPage.every((d) => selected.has(d.id))
                      }
                      onChange={(e) => toggleAllOnPage(e.target.checked)}
                    />
                  </th>
                  <th className="px-4 py-3">Référence</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {quotesPage.map((q) => (
                  <tr
                    key={q.id}
                    onClick={() => router.push(`/dashboard/sales/quotes/new?id=${q.id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        aria-label={`Sélectionner ${q.reference}`}
                        checked={selected.has(q.id)}
                        onChange={(e) => {
                          e.stopPropagation();
                          const s = new Set(selected);
                          if (e.target.checked) s.add(q.id);
                          else s.delete(q.id);
                          setSelected(s);
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="font-medium text-gray-900 hover:text-primary hover:underline"
                        title="Ouvrir le devis"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/dashboard/sales/quotes/new?id=${q.id}`);
                        }}
                      >
                        {q.reference}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {partnerName(q.partner_id)}
                      </p>
                      {partnerPhone(q.partner_id) && (
                        <p className="text-xs text-gray-500">
                          {partnerPhone(q.partner_id)}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatDate(q.quote_date)}</td>
                    <td className="px-4 py-3"><StatusBadge status={q.status} /></td>
                    <td className="px-4 py-3 text-right font-semibold">
                      {formatCurrency(q.amount_total)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {(() => {
                          const isDraft = q.status === "draft";
                          return (
                            <>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Confirmer le devis ${q.reference}`
                                    : `Devis ${q.reference} déjà confirmé`
                                }
                                disabled={!isDraft || confirmQuote.isPending}
                                className={
                                  isDraft
                                    ? "text-green-600 hover:bg-green-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleConfirm(q.id)}
                              >
                                <CheckCircle2 className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Modifier le devis ${q.reference}`
                                    : "Seul un devis brouillon peut être modifié"
                                }
                                disabled={!isDraft}
                                className={
                                  isDraft
                                    ? "text-blue-600 hover:bg-blue-50"
                                    : "text-gray-300"
                                }
                                onClick={() =>
                                  router.push(`/dashboard/sales/quotes/new?id=${q.id}`)
                                }
                              >
                                <Pencil className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Supprimer le devis ${q.reference}`
                                    : "Seul un devis brouillon peut être supprimé"
                                }
                                disabled={!isDraft || deleteQuote.isPending}
                                className={
                                  isDraft
                                    ? "text-red-600 hover:bg-red-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleDelete(q.id, q.reference)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  q.status === "confirmed"
                                    ? `Remettre le devis ${q.reference} au brouillon`
                                    : "Seul un devis confirmé peut être remis au brouillon"
                                }
                                disabled={q.status !== "confirmed" || quoteBackToDraft.isPending}
                                className={
                                  q.status === "confirmed"
                                    ? "text-amber-600 hover:bg-amber-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleQuoteBackToDraft(q.id, q.reference)}
                              >
                                <Undo2 className="h-4 w-4" />
                              </IconAction>
                            </>
                          );
                        })()}
                        <IconAction
                          title={`Imprimer le devis ${q.reference} (PDF)`}
                          className="text-gray-600 hover:bg-gray-100"
                          onClick={() => printQuote(q.id).catch(() =>
                            alert("Impossible de générer le PDF du devis.")
                          )}
                        >
                          <Printer className="h-4 w-4" />
                        </IconAction>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ListPager
              from={(safePage - 1) * PAGE_SIZE + 1}
              to={Math.min(safePage * PAGE_SIZE, docs.length)}
              total={docs.length}
              page={safePage}
              totalPages={totalPages}
              onPage={setPage}
            />
            </>
          )}
        </Card>
      )}

      {/* Commandes */}
      {tab === "orders" && (
        <Card className="overflow-hidden p-0">
          {loadingOrders ? (
            <p className="p-6 text-sm text-gray-500">Chargement…</p>
          ) : orders.length === 0 ? (
            <div className="p-10 text-center">
              <ShoppingCart className="mx-auto mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">
                Aucune commande. Confirmez un devis pour en générer une.
              </p>
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-sm text-gray-500">
                Aucune commande ne correspond à la recherche ou au filtre.
              </p>
            </div>
          ) : (
            <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label="Tout sélectionner sur la page"
                      checked={
                        ordersPage.length > 0 &&
                        ordersPage.every((d) => selected.has(d.id))
                      }
                      onChange={(e) => toggleAllOnPage(e.target.checked)}
                    />
                  </th>
                  <th className="px-4 py-3">Référence</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-4 py-3 text-right">Payé</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {ordersPage.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => router.push(`/dashboard/sales/quotes/new?orderId=${o.id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        aria-label={`Sélectionner ${o.reference}`}
                        checked={selected.has(o.id)}
                        onChange={(e) => {
                          e.stopPropagation();
                          const s = new Set(selected);
                          if (e.target.checked) s.add(o.id);
                          else s.delete(o.id);
                          setSelected(s);
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="font-medium text-gray-900 hover:text-primary hover:underline"
                        title="Ouvrir la commande"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/dashboard/sales/quotes/new?orderId=${o.id}`);
                        }}
                      >
                        {o.reference}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {partnerName(o.partner_id)}
                      </p>
                      {partnerPhone(o.partner_id) && (
                        <p className="text-xs text-gray-500">
                          {partnerPhone(o.partner_id)}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatDate(o.order_date)}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {o.fulfillment_mode === "hybrid"
                        ? "Hybride"
                        : o.fulfillment_mode === "purchase"
                          ? "À acheter"
                          : o.fulfillment_mode === "pos"
                            ? "Comptoir"
                            : "Stock"}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                    <td className="px-4 py-3 text-right font-semibold">
                      {formatCurrency(o.amount_total)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {formatCurrency(o.paid_amount)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {(() => {
                          const isDraft = o.status === "draft";
                          const isConfirmed =
                            o.status === "confirmed" && o.fulfillment_mode !== "pos";
                          return (
                            <>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Confirmer la commande ${o.reference}`
                                    : `Commande ${o.reference} déjà confirmée`
                                }
                                disabled={!isDraft}
                                className={
                                  isDraft
                                    ? "text-green-600 hover:bg-green-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleConfirm(o.id)}
                              >
                                <CheckCircle2 className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Modifier la commande ${o.reference}`
                                    : "Seule une commande brouillon peut être modifiée"
                                }
                                disabled={!isDraft}
                                className={
                                  isDraft
                                    ? "text-blue-600 hover:bg-blue-50"
                                    : "text-gray-300"
                                }
                                onClick={() =>
                                  router.push(`/dashboard/sales/quotes/new?orderId=${o.id}`)
                                }
                              >
                                <Pencil className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isDraft
                                    ? `Supprimer la commande ${o.reference}`
                                    : "Seule une commande brouillon peut être supprimée"
                                }
                                disabled={!isDraft || deleteOrder.isPending}
                                className={
                                  isDraft
                                    ? "text-red-600 hover:bg-red-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleDeleteOrder(o.id, o.reference)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isConfirmed
                                    ? `Voir / imprimer le bon de commande ${o.reference}`
                                    : "Le bon de commande n'est disponible qu'une fois confirmé"
                                }
                                disabled={!isConfirmed}
                                className={
                                  isConfirmed
                                    ? "text-indigo-600 hover:bg-indigo-50"
                                    : "text-gray-300"
                                }
                                onClick={() => printOrder(o.id).catch(() =>
                                  alert("Impossible de générer le bon de commande.")
                                )}
                              >
                                <Eye className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  isConfirmed
                                    ? `Remettre la commande ${o.reference} au brouillon`
                                    : "Seule une commande confirmée peut être remise au brouillon"
                                }
                                disabled={!isConfirmed || orderBackToDraft.isPending}
                                className={
                                  isConfirmed
                                    ? "text-amber-600 hover:bg-amber-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleBackToDraft(o.id, o.reference)}
                              >
                                <Undo2 className="h-4 w-4" />
                              </IconAction>
                              <IconAction
                                title={
                                  o.fulfillment_mode === "pos"
                                    ? `Imprimer le ticket ${o.reference}`
                                    : `Imprimer la facture de ${o.reference}`
                                }
                                className="text-gray-600 hover:bg-gray-100"
                                onClick={() => printOrder(o.id).catch(() =>
                                  alert("Impossible de générer le PDF de la commande.")
                                )}
                              >
                                <Printer className="h-4 w-4" />
                              </IconAction>
                            </>
                          );
                        })()}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ListPager
              from={(safePage - 1) * PAGE_SIZE + 1}
              to={Math.min(safePage * PAGE_SIZE, docs.length)}
              total={docs.length}
              page={safePage}
              totalPages={totalPages}
              onPage={setPage}
            />
            </>
          )}
        </Card>
      )}
    </div>
  );
}

/** Pied de pagination façon Odoo : « X–Y / total » + navigation. */
function ListPager({
  from,
  to,
  total,
  page,
  totalPages,
  onPage,
}: {
  from: number;
  to: number;
  total: number;
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-between border-t border-gray-200 px-4 py-2 text-xs text-gray-500">
      <span>{total === 0 ? "0 résultat" : `${from}–${to} / ${total}`}</span>
      <div className="flex items-center gap-1">
        <IconAction
          title="Page précédente"
          disabled={page <= 1}
          className="text-gray-600 hover:bg-gray-100"
          onClick={() => onPage(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </IconAction>
        <IconAction
          title="Page suivante"
          disabled={page >= totalPages}
          className="text-gray-600 hover:bg-gray-100"
          onClick={() => onPage(page + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </IconAction>
      </div>
    </div>
  );
}

/** Bouton d'action réduit, icône seule, avec infobulle. */
function IconAction({
  title,
  onClick,
  disabled,
  className = "",
  children,
}: {
  title: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {children}
    </button>
  );
}