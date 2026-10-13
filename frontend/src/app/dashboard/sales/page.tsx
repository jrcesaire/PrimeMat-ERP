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
  ReceiptText,
  Trash2,
  Eye,
  Undo2,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  Upload,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ImportDialog } from "@/components/shared/import-dialog";
import { ExportButton } from "@/components/shared/export-button";
import {
  useConfirm,
  confirmBackToDraftOptions,
  confirmCloseOptions,
  confirmDeleteOptions,
  confirmPostOptions,
} from "@/components/ui/confirm";
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
import {
  useInvoices,
  useCreateInvoiceFromOrder,
  useCreateInvoiceFromQuote,
  type Invoice,
} from "@/hooks/useOperations";
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
  const [importOpen, setImportOpen] = useState(false);
  const { data: quotes = [], isLoading: loadingQuotes } = useQuotes();
  const { data: orders = [], isLoading: loadingOrders } = useOrders();
  const { data: invoices = [] } = useInvoices();
  const { data: partners = [] } = usePartners();
  const confirmQuote = useConfirmQuote();
  const deleteQuote = useDeleteQuote();
  const quoteBackToDraft = useQuoteBackToDraft();
  const deleteOrder = useDeleteOrder();
  const orderBackToDraft = useOrderBackToDraft();
  const createInvoice = useCreateInvoiceFromOrder();
  const createInvoiceFromQuote = useCreateInvoiceFromQuote();
  const queryClient = useQueryClient();
  const confirm = useConfirm();

  // --- Facturation : reste à facturer par commande ---
  const [invoiceFor, setInvoiceFor] = useState<SalesOrder | null>(null);
  const invoicedByOrder = useMemo(() => {
    const m = new Map<number, number>();
    invoices.forEach((i) => {
      if (i.order_id && !["cancelled", "credit"].includes(i.status)) {
        m.set(i.order_id, (m.get(i.order_id) ?? 0) + i.amount_total);
      }
    });
    return m;
  }, [invoices]);
  const remainingFor = (orderId: number, total: number) =>
    Math.max(total - (invoicedByOrder.get(orderId) ?? 0), 0);

  const handleCreateInvoice = async (p: {
    mode: "full" | "down_payment_percent" | "down_payment_fixed";
    value: number | null;
    dueDays: number;
  }) => {
    if (!invoiceFor) return;
    const inv = await createInvoice.mutateAsync({
      orderId: invoiceFor.id,
      dueDays: p.dueDays,
      mode: p.mode,
      value: p.value,
      post: false,
    });
    setInvoiceFor(null);
    router.push(`/dashboard/invoicing/${inv.id}`);
  };

  /** Parcours de vente : « Créer facture » directement depuis un devis. */
  const handleQuoteInvoice = async (quoteId: number) => {
    try {
      const res = await createInvoiceFromQuote.mutateAsync({ quoteId });
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
      router.push(`/dashboard/invoicing/${res.invoice_id}`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      alert(detail || "Erreur lors de la création de la facture");
    }
  };

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
    const { confirmed } = await confirm(
      confirmDeleteOptions(`le devis ${reference}`),
    );
    if (!confirmed) return;
    try {
      await deleteQuote.mutateAsync(quoteId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la suppression du devis");
    }
  };

  const handleDeleteOrder = async (orderId: number, reference: string) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(`la commande ${reference}`),
    );
    if (!confirmed) return;
    try {
      await deleteOrder.mutateAsync(orderId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la suppression de la commande");
    }
  };

  const handleBackToDraft = async (orderId: number, reference: string) => {
    const { confirmed } = await confirm({
      ...confirmBackToDraftOptions(`la commande ${reference}`),
      description:
        "Les réservations de stock seront libérées. Vous pourrez modifier la commande puis la confirmer à nouveau.",
    });
    if (!confirmed) return;
    try {
      await orderBackToDraft.mutateAsync(orderId);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      alert(detail || "Erreur lors de la remise au brouillon");
    }
  };

  const handleQuoteBackToDraft = async (quoteId: number, reference: string) => {
    const { confirmed } = await confirm(
      confirmBackToDraftOptions(`le devis ${reference}`),
    );
    if (!confirmed) return;
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
    const { confirmed } = await confirm({
      ...confirmPostOptions(`${targets.length} devis`),
      description:
        "Une commande client sera créée pour chaque devis. Vous pourrez la modifier puis la facturer.",
    });
    if (!confirmed) return;
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
    const { confirmed: confirmedQuotes } = await confirm(
      confirmDeleteOptions(`${targets.length} devis brouillons`),
    );
    if (!confirmedQuotes) return;
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
    const { confirmed: confirmedOrders } = await confirm(
      confirmDeleteOptions(`${targets.length} commandes brouillons`),
    );
    if (!confirmedOrders) return;
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
        <div className="flex items-center gap-2">
          <ExportButton
            key={tab}
            endpoint={
              tab === "quotes" ? "/sales/quotes/export" : "/sales/orders/export"
            }
            fallbackName={tab === "quotes" ? "devis" : "commandes"}
          />
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={() => setImportOpen(true)}
          >
            <Upload className="h-4 w-4" />
            Importer commandes
          </Button>
          <Link href="/dashboard/sales/quotes/new">
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nouveau devis
            </Button>
          </Link>
        </div>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        endpoint="/sales/orders/import"
        title="Importer des commandes"
        columnsHint="client, produit, quantite, prix_unitaire, remise (%), date (JJ/MM/AAAA), reference_commande (facultative : regroupe les lignes d'une même commande), description, devise"
        invalidateKeys={[SALES_KEYS.orders]}
      />

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
                                  q.status === "confirmed"
                                    ? `Créer / voir la facture du devis ${q.reference}`
                                    : "La facturation nécessite un devis confirmé"
                                }
                                disabled={
                                  q.status !== "confirmed" ||
                                  createInvoiceFromQuote.isPending
                                }
                                className={
                                  q.status === "confirmed"
                                    ? "text-emerald-600 hover:bg-emerald-50"
                                    : "text-gray-300"
                                }
                                onClick={() => handleQuoteInvoice(q.id)}
                              >
                                <ReceiptText className="h-4 w-4" />
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
                                  isConfirmed
                                    ? remainingFor(o.id, o.amount_total) > 0
                                      ? `Créer une facture pour ${o.reference}`
                                      : `${o.reference} déjà entièrement facturée`
                                    : "La facturation nécessite une commande confirmée"
                                }
                                disabled={
                                  !isConfirmed || remainingFor(o.id, o.amount_total) <= 0
                                }
                                className={
                                  isConfirmed && remainingFor(o.id, o.amount_total) > 0
                                    ? "text-emerald-600 hover:bg-emerald-50"
                                    : "text-gray-300"
                                }
                                onClick={() => setInvoiceFor(o)}
                              >
                                <ReceiptText className="h-4 w-4" />
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

      {/* Dialogue « Créer une facture » (façon Odoo) */}
      {invoiceFor && (
        <CreateInvoiceDialog
          order={invoiceFor}
          remaining={remainingFor(invoiceFor.id, invoiceFor.amount_total)}
          existing={invoices.filter((i) => i.order_id === invoiceFor.id)}
          onClose={() => setInvoiceFor(null)}
          onCreate={handleCreateInvoice}
          pending={createInvoice.isPending}
        />
      )}
    </div>
  );
}

/** Dialogue « Créer une facture » façon Odoo : totale, acompte % ou acompte fixe. */
function CreateInvoiceDialog({
  order,
  remaining,
  existing,
  onClose,
  onCreate,
  pending,
}: {
  order: SalesOrder;
  remaining: number;
  existing: Invoice[];
  onClose: () => void;
  onCreate: (p: {
    mode: "full" | "down_payment_percent" | "down_payment_fixed";
    value: number | null;
    dueDays: number;
  }) => Promise<unknown>;
  pending: boolean;
}) {
  const [mode, setMode] = useState<
    "full" | "down_payment_percent" | "down_payment_fixed"
  >("full");
  const [value, setValue] = useState("30");
  const [dueDays, setDueDays] = useState("0");
  const [error, setError] = useState<string | null>(null);

  const valueNum = parseFloat(value.replace(",", ".")) || 0;
  const preview =
    mode === "full"
      ? remaining
      : mode === "down_payment_percent"
        ? Math.min(remaining, (order.amount_total * valueNum) / 100)
        : Math.min(remaining, valueNum);

  const submit = async () => {
    setError(null);
    const v = mode === "full" ? null : valueNum;
    if (mode !== "full" && (!v || v <= 0)) {
      return setError("Saisissez une valeur positive.");
    }
    if (mode === "down_payment_percent" && v !== null && v > 100) {
      return setError("Le pourcentage doit être compris entre 0 et 100.");
    }
    try {
      await onCreate({ mode, value: v, dueDays: parseInt(dueDays, 10) || 0 });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail : "Erreur lors de la création de la facture",
      );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900">
          Créer facture — {order.reference}
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Total commande : {formatCurrency(order.amount_total)} · Reste à facturer :{" "}
          <span className="font-semibold text-gray-800">{formatCurrency(remaining)}</span>
        </p>

        <div className="mt-4 space-y-2">
          {(
            [
              ["full", "Facture normale", "Facturation du solde restant"],
              ["down_payment_percent", "Acompte (pourcentage)", "% du total commande"],
              ["down_payment_fixed", "Acompte (montant fixe)", "Montant en devises"],
            ] as const
          ).map(([m, label, hint]) => (
            <label
              key={m}
              className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 ${
                mode === m ? "border-primary bg-primary/5" : "border-gray-200"
              }`}
            >
              <input
                type="radio"
                name="invoice-mode"
                checked={mode === m}
                onChange={() => setMode(m)}
                className="h-4 w-4 accent-primary"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900">{label}</span>
                <span className="block text-xs text-gray-500">{hint}</span>
              </span>
            </label>
          ))}
        </div>

        {mode !== "full" && (
          <div className="mt-3">
            <label className="text-xs font-medium text-gray-600">
              {mode === "down_payment_percent" ? "Pourcentage (%)" : "Montant"}
            </label>
            <input
              type="number"
              min="0"
              step="any"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            {valueNum > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                Montant de la facture : <strong>{formatCurrency(preview)}</strong>
              </p>
            )}
          </div>
        )}

        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600">
            Délai de paiement (jours)
          </label>
          <input
            type="number"
            min="0"
            value={dueDays}
            onChange={(e) => setDueDays(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        {existing.length > 0 && (
          <div className="mt-3 rounded-md bg-gray-50 p-3 text-xs text-gray-600">
            <p className="font-medium text-gray-700">Déjà facturé :</p>
            <ul className="mt-1 space-y-0.5">
              {existing.map((i) => (
                <li key={i.id}>
                  {i.reference} — {formatCurrency(i.amount_total)} ({i.status})
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={submit} disabled={pending}>
            {pending ? "Création…" : "Créer brouillon"}
          </Button>
        </div>
      </div>
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