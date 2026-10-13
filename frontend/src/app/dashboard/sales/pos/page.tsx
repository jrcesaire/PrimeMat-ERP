/**
 * Point de vente (vente comptoir).
 *
 * - Vue « nouvelle vente » : layout split type caisse tactile (fusion des
 *   maquettes) — rail caisse à gauche (client facultatif, panier, totaux
 *   géants, tuiles de paiement + pavé numérique + encaissement), grille
 *   produits tactile à droite (recherche, catégories, tuiles produits).
 *   Sidebar + header masqués pendant la vente (mode focus `setPosFocus`).
 * - Encaissement sans client obligatoire : sans sélection, la vente est
 *   rattachée au partenaire walk-in « Client de passage » (backend).
 * - Vue « historique » (défaut) : ventes comptoir paginées (15/page,
 *   récent → ancien), ligne cliquable = réimpression du reçu POS.
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Eye,
  Pause,
  Play,
  Plus,
  Printer,
  ShoppingCart,
  Trash2,
  UserRound,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProductSearchAdd } from "@/components/sales/product-search-add";
import { PosCartTable } from "@/components/sales/pos/PosCartTable";
import { PosCategoryRail } from "@/components/sales/pos/PosCategoryRail";
import { PosTotalsBar, computePosTotals } from "@/components/sales/pos/PosTotalsBar";
import { PosProductGrid } from "@/components/sales/pos/PosProductGrid";
import { PosPaymentPanel } from "@/components/sales/pos/PosPaymentPanel";
import { PosPartnerDialog } from "@/components/sales/pos/PosPartnerDialog";
import { useCategoryTree, useProducts } from "@/hooks/useCatalogue";
import { useClients } from "@/hooks/useCRM";
import {
  SALES_KEYS,
  useArchivePosSale,
  usePosSale,
  usePosSales,
} from "@/hooks/useSales";
import { apiClient } from "@/lib/api/client";
import { printPosTicket } from "@/lib/api/pdf";
import { attachHidScanner } from "@/lib/hid-scanner";
import { setPosFocus } from "@/lib/pos-focus";
import { formatCurrency } from "@/lib/utils";

interface PosLine {
  key: number;
  product_id: number;
  name: string;
  reference?: string | null;
  variant_name?: string | null;
  sell_by_length: boolean;
  quantity: number; // pièces ou mètres selon le produit
  unit_price: number;
  discount_percent: number; // remise par ligne (%)
  category_id?: number | null;
}

const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  mobile_money: "Mobile Money",
  bank: "Virement",
  check: "Chèque",
};

let lineKey = 1;

/** TVA POS : 0 = prix affichés TTC, aucun calcul supplémentaire. */
const POS_TAX_PERCENT = 0;

interface SuspendedSale {
  id: string;
  savedAt: string;
  partnerId: number | null;
  method: string;
  lines: PosLine[];
}

const SUSPENDED_KEY = "erp-pos-suspended";

function loadSuspended(): SuspendedSale[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(SUSPENDED_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function PosPage() {
  const { data: clients = [] } = useClients();
  const queryClient = useQueryClient();
  const [view, setView] = useState<"history" | "new" | "detail">("history");
  const [page, setPage] = useState(1);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [suspended, setSuspended] = useState<SuspendedSale[]>(() => loadSuspended());
  const archiveSale = useArchivePosSale();
  const [archivingId, setArchivingId] = useState<number | null>(null);
  const [partnerId, setPartnerId] = useState<number | null>(null);
  const [lines, setLines] = useState<PosLine[]>([]);
  const [method, setMethod] = useState("cash");
  const [amountStr, setAmountStr] = useState(""); // montant reçu (pavé numérique)
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [reprinting, setReprinting] = useState<number | null>(null);
  const [lastSale, setLastSale] = useState<{ orderId: number; ref: string } | null>(
    null,
  );
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  const [selectedKey, setSelectedKey] = useState<number | null>(null);
  const [partnerDialogOpen, setPartnerDialogOpen] = useState(false);

  const { data: history, isLoading } = usePosSales(page, 15);
  const sales = history?.items ?? [];
  const { data: detail, isLoading: detailLoading } = usePosSale(detailId);
  const { data: categoryTree = [] } = useCategoryTree();
  const { data: products = [], isLoading: productsLoading } = useProducts(
    undefined,
    240,
    categoryFilter,
  );

  // Mode focus caisse : masque sidebar + header pendant la vente.
  useEffect(() => {
    setPosFocus(view === "new");
    return () => setPosFocus(false);
  }, [view]);

  const totals = useMemo(() => {
    const gross = lines.reduce((s, l) => s + l.quantity * l.unit_price, 0);
    const t = computePosTotals(lines, 0, POS_TAX_PERCENT);
    // Les remises ligne sont déjà déduites du sous-total (remise commande à 0) :
    // on affiche ici l'écart brut − net correspondant.
    return { ...t, discountAmount: gross - t.subtotal };
  }, [lines]);

  // Scan AIDC (douchette USB / terminal) : produit ajouté direct au panier.
  const [scanMsg, setScanMsg] = useState<string | null>(null);
  useEffect(() => {
    return attachHidScanner(async (code) => {
      try {
        const res = await apiClient.get(
          `/catalogue/products/lookup?code=${encodeURIComponent(code)}`,
        );
        if (res.data?.found && res.data.product) {
          const p = res.data.product;
          setView("new");
          setScanMsg(null);
          addProduct({
            id: p.id,
            name: p.name,
            reference: p.reference,
            category_id: p.category_id,
            sell_by_length: p.sell_by_length,
            price_per_meter: p.price_per_meter,
            selling_price: p.selling_price,
          });
        } else {
          setScanMsg(`Produit introuvable pour le code « ${code} ».`);
        }
      } catch {
        setScanMsg("Erreur lors de la recherche du code scanné.");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const addProduct = (p: {
    id: number;
    name: string;
    reference?: string | null;
    category_id?: number | null;
    sell_by_length?: boolean;
    price_per_meter?: number | null;
    selling_price?: number | null;
  }) => {
    const existing = lines.find((l) => l.product_id === p.id);
    if (existing && !p.sell_by_length) {
      setLines((ls) =>
        ls.map((l) => (l.product_id === p.id ? { ...l, quantity: l.quantity + 1 } : l)),
      );
      setSelectedKey(existing.key);
      return;
    }
    const key = lineKey++;
    setLines((ls) => [
      ...ls,
      {
        key,
        product_id: p.id,
        name: p.name,
        reference: p.reference ?? null,
        category_id: p.category_id ?? null,
        sell_by_length: !!p.sell_by_length,
        quantity: 1,
        unit_price: p.sell_by_length ? (p.price_per_meter ?? 0) : (p.selling_price ?? 0),
        discount_percent: 0,
      },
    ]);
    setSelectedKey(key);
  };

  const updateLine = (key: number, patch: Partial<PosLine>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const removeLine = (key: number) => {
    setLines((ls) => ls.filter((l) => l.key !== key));
    setSelectedKey((k) => (k === key ? null : k));
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });

  const reprint = async (orderId: number) => {
    setReprinting(orderId);
    try {
      await printPosTicket(orderId);
    } catch {
      alert("Impression bloquée — autorisez les pop-ups pour ce site.");
    } finally {
      setReprinting(null);
    }
  };

  const handleSubmit = async () => {
    setError(null);
    if (lines.length === 0) return setError("Ajoutez au moins un produit.");
    setSubmitting(true);
    try {
      const received = Number(amountStr || 0);
      // Aucun sous-paiement en caisse : le reçu doit couvrir le total.
      if (received > 0 && received + 1e-6 < totals.total) {
        return setError(
          `Montant reçu insuffisant — reste à encaisser ${formatCurrency(totals.total - received)}.`,
        );
      }
      const payload = {
        // Client facultatif : absent → partenaire walk-in côté backend.
        ...(partnerId ? { partner_id: partnerId } : {}),
        method,
        amount: received > 0 ? received : totals.total,
        lines: lines.map((l) => ({
          product_id: l.product_id,
          description: l.name,
          quantity_ordered: l.quantity,
          unit: l.sell_by_length ? "ml" : "p",
          sell_by_length: l.sell_by_length,
          unit_price: l.unit_price,
          discount_percent: l.discount_percent || 0,
          ...(l.sell_by_length ? { cuts: [{ quantity: 1, length: l.quantity }] } : {}),
        })),
      };
      const res = await apiClient.post("/sales/pos/sales", payload);
      const order = res.data as {
        order?: { id?: number; reference?: string };
        id?: number;
        order_id?: number;
        order_reference?: string;
      };
      const orderId = order?.order?.id ?? order?.order_id ?? order?.id;
      if (orderId) {
        try {
          await printPosTicket(orderId);
        } catch {
          /* le reçu pourra être réimprimé depuis l'historique */
        }
        setLastSale({
          orderId,
          ref: order?.order_reference ?? order?.order?.reference ?? "",
        });
      }
      setLines([]);
      setSelectedKey(null);
      setCategoryFilter(null);
      setAmountStr("");
      setPartnerId(null);
      setPage(1);
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.posSales] });
      setView("history");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la vente");
    } finally {
      setSubmitting(false);
    }
  };


  // Vue 1 : historique des ventes (défaut)
  const openDetail = (id: number) => {
    setDetailId(id);
    setView("detail");
  };

  const persistSuspended = (next: SuspendedSale[]) => {
    setSuspended(next);
    try {
      window.localStorage.setItem(SUSPENDED_KEY, JSON.stringify(next));
    } catch {
      /* stockage indisponible : la liste mémoire reste utilisable */
    }
  };

  /** Met la vente en cours en pause : historique accessible, reprise possible. */
  const handleSuspend = () => {
    if (lines.length === 0) return;
    const entry: SuspendedSale = {
      id: `${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
      savedAt: new Date().toISOString(),
      partnerId,
      method,
      lines,
    };
    persistSuspended([entry, ...suspended]);
    setLines([]);
    setPartnerId(null);
    setAmountStr("");
    setSelectedKey(null);
    setError(null);
    setView("history");
  };

  /** Reprend une vente suspendue dans l'écran de caisse. */
  const handleResume = (id: string) => {
    const found = suspended.find((s) => s.id === id);
    if (!found) return;
    setLines(found.lines);
    setPartnerId(found.partnerId);
    setMethod(found.method);
    setAmountStr("");
    setSelectedKey(null);
    setError(null);
    setLastSale(null);
    persistSuspended(suspended.filter((s) => s.id !== id));
    setView("new");
  };

  const handleDeleteSuspended = (id: string) => {
    persistSuspended(suspended.filter((s) => s.id !== id));
  };

  /** Archive une vente clôturée : masquage d'historique, comptabilité conservée. */
  const handleArchive = async (id: number) => {
    if (!window.confirm("Archiver cette vente ? Elle restera consultable via la facturation.")) return;
    setArchivingId(id);
    try {
      await archiveSale.mutateAsync(id);
      if (detailId === id) {
        setDetailId(null);
        setView("history");
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Archivage impossible.");
    } finally {
      setArchivingId(null);
    }
  };

  // Vue détail : lecture seule d'une vente comptoir (lignes, facture, paiement)
  if (view === "detail") {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDetailId(null);
                setView("history");
              }}
            >
              <ArrowLeft className="h-4 w-4" /> Historique
            </Button>
            <h1 className="text-xl font-bold text-gray-900">
              Vente {detail?.reference ?? ""}
            </h1>
            {detail?.archived && (
              <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-600">
                Archivée
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {detailId != null && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  printPosTicket(detailId).catch(() =>
                    alert("Impression bloquée — autorisez les pop-ups."),
                  )
                }
                disabled={detailLoading}
              >
                <Printer className="h-4 w-4" /> Imprimer
              </Button>
            )}
            {detailId != null && !detail?.archived && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleArchive(detailId)}
                disabled={archivingId === detailId}
              >
                <Archive className="h-4 w-4" /> Archiver
              </Button>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <Card className="p-4">
          {detailLoading ? (
            <p className="p-6 text-center text-sm text-gray-500">
              Chargement…
            </p>
          ) : !detail ? (
            <p className="p-6 text-center text-sm text-gray-500">
              Vente introuvable.
            </p>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-xs uppercase text-gray-500">Date</p>
                  <p className="font-medium text-gray-900">
                    {formatDate(detail.created_at)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase text-gray-500">Client</p>
                  <p className="font-medium text-gray-900">
                    {detail.partner?.name ?? "Client de passage"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase text-gray-500">Statut</p>
                  <p className="font-medium text-gray-900">{detail.status}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-gray-500">Facture</p>
                  <p className="font-medium text-gray-900">
                    {detail.invoice
                      ? `${detail.invoice.reference} (${detail.invoice.status})`
                      : "—"}
                  </p>
                </div>
              </div>

              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                    <th className="px-2 py-2">Article</th>
                    <th className="px-2 py-2 text-right">Qté</th>
                    <th className="px-2 py-2 text-right">P.U.</th>
                    <th className="px-2 py-2 text-right">Remise</th>
                    <th className="px-2 py-2 text-right">Sous-total</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.lines.map((l, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="px-2 py-2 text-gray-800">
                        {l.description ?? `Article ${l.product_id ?? "—"}`}
                        {l.variant_name ? ` — ${l.variant_name}` : ""}
                      </td>
                      <td className="px-2 py-2 text-right text-gray-600">
                        {l.quantity} {l.unit ?? ""}
                      </td>
                      <td className="px-2 py-2 text-right text-gray-600">
                        {formatCurrency(l.unit_price)}
                      </td>
                      <td className="px-2 py-2 text-right text-gray-600">
                        {l.discount_percent > 0 ? `${l.discount_percent} %` : "—"}
                      </td>
                      <td className="px-2 py-2 text-right font-medium text-gray-900">
                        {formatCurrency(l.subtotal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="flex items-center justify-between border-t border-gray-200 pt-3">
                <p className="text-sm text-gray-600">
                  Paiement :{" "}
                  {detail.payment
                    ? `${METHOD_LABELS[detail.payment.method] ?? detail.payment.method} — ${formatCurrency(detail.payment.amount)}`
                    : "—"}
                </p>
                <p className="text-lg font-bold text-gray-900">
                  Total : {formatCurrency(detail.amount_total)}
                </p>
              </div>
            </div>
          )}
        </Card>
      </div>
    );
  }

  if (view === "history") {
    const totalSales = history?.total ?? 0;
    const pageCount = Math.max(1, Math.ceil(totalSales / 15));
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Point de vente</h1>
          <p className="text-sm text-gray-600">Historique des ventes comptoir</p>
        </div>

        {scanMsg && (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">{scanMsg}</div>
        )}

        {lastSale && (
          <div className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 px-4 py-3">
            <p className="text-sm font-medium text-green-800">
              Vente {lastSale.ref} enregistrée ✓ — reçu envoyé à l'impression.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  printPosTicket(lastSale.orderId).catch(() =>
                    alert("Impression bloquée — autorisez les pop-ups."),
                  )
                }
              >
                <Printer className="h-4 w-4" /> Réimprimer
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setLastSale(null)}>
                Fermer
              </Button>
            </div>
          </div>
        )}

        <Card className="overflow-hidden p-0">
          {isLoading ? (
            <p className="p-10 text-center text-sm text-gray-500">Chargement…</p>
          ) : sales.length === 0 ? (
            <div className="p-10 text-center">
              <ShoppingCart className="mx-auto mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">
                Aucune vente enregistrée pour le moment.
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                  <th className="px-4 py-3">Référence</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3 text-center">Articles</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-4 py-3">Paiement</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sales.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => openDetail(s.id)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-blue-50"
                    title="Cliquer pour voir le détail de la vente"
                  >
                    <td className="px-4 py-3 font-semibold text-gray-900">
                      {s.reference}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {formatDate(s.created_at)}
                    </td>
                    <td className="px-4 py-3 text-gray-800">
                      {s.partner_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600">
                      {s.items_count}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">
                      {formatCurrency(s.amount_total)}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {s.payment_method
                        ? METHOD_LABELS[s.payment_method] ?? s.payment_method
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openDetail(s.id);
                          }}
                          className="text-gray-400 hover:text-blue-600"
                          title="Voir le détail"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            reprint(s.id);
                          }}
                          className={`text-gray-400 hover:text-blue-600 ${
                            reprinting === s.id ? "opacity-50" : ""
                          }`}
                          title="Réimprimer le reçu"
                        >
                          <Printer className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleArchive(s.id);
                          }}
                          className={`text-gray-400 hover:text-red-600 ${
                            archivingId === s.id ? "opacity-50" : ""
                          }`}
                          title="Archiver (masquer de l'historique)"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* Ventes suspendues (localStorage) — reprendre ou supprimer */}
        {suspended.length > 0 && (
          <Card className="p-4">
            <div className="mb-3 flex items-center gap-2">
              <Pause className="h-4 w-4 text-amber-600" />
              <h2 className="text-sm font-semibold text-gray-900">
                Ventes suspendues ({suspended.length})
              </h2>
            </div>
            <ul className="divide-y divide-gray-100">
              {suspended.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between gap-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-gray-800">
                      {s.lines.length} article{s.lines.length > 1 ? "s" : ""} —{" "}
                      {formatCurrency(
                        s.lines.reduce(
                          (acc, l) =>
                            acc +
                            l.quantity *
                              l.unit_price *
                              (1 - l.discount_percent / 100),
                          0,
                        ),
                      )}
                    </p>
                    <p className="text-xs text-gray-500">
                      Suspendue le {formatDate(s.savedAt)}
                      {s.method ? ` — ${METHOD_LABELS[s.method] ?? s.method}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleResume(s.id)}
                    >
                      <Play className="h-3.5 w-3.5" /> Reprendre
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteSuspended(s.id)}
                      title="Supprimer la vente suspendue"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-red-500" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {sales.length > 0 && (
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              {totalSales} vente{totalSales > 1 ? "s" : ""} — page {page} sur{" "}
              {pageCount}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" /> Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pageCount}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Nouvelle vente — bouton flottant bien visible */}
        <button
          onClick={() => {
            setLastSale(null);
            setView("new");
          }}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-green-600 px-6 py-4 text-base font-semibold text-white shadow-xl transition hover:bg-green-700 hover:shadow-2xl"
          title="Démarrer une nouvelle vente"
        >
          <Plus className="h-7 w-7" />
          Nouvelle vente
        </button>
      </div>
    );
  }

  // Vue 2 : nouvelle vente — split caisse tactile (mode focus plein écran)
  return (
    <div className="flex h-full gap-4">
      {/* Rail caisse (40 %) — client, panier, totaux, encaissement */}
      <div className="flex w-[40%] min-w-[360px] flex-col gap-3 overflow-y-auto pr-1">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Nouvelle vente</h1>
            <p className="text-xs text-gray-600">
              Vente comptoir — encaissement direct
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setView("history")}>
            <ChevronLeft className="h-4 w-4" /> Historique
          </Button>
        </div>

        {scanMsg && (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">
            {scanMsg}
          </div>
        )}

        {/* Client facultatif — défaut : « Client de passage » (walk-in) */}
        <div className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <label className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-gray-500">
              <UserRound className="h-3.5 w-3.5" /> Client (facultatif)
            </label>
            <button
              type="button"
              onClick={() => setPartnerDialogOpen(true)}
              className="flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50"
              title="Créer un nouveau client sans quitter la vente"
            >
              <Plus className="h-3.5 w-3.5" /> Nouveau client
            </button>
          </div>
          <select
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={partnerId ?? ""}
            onChange={(e) =>
              setPartnerId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">Client de passage (sans compte)</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* Suspendre la vente en cours — reprise depuis l'historique */}
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setView("history")}
            title="Retour à l'historique (la vente en cours reste en mémoire)"
          >
            <ArrowLeft className="h-4 w-4" /> Historique
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSuspend}
            disabled={lines.length === 0}
            title="Mettre la vente en pause et la reprendre plus tard"
          >
            <Pause className="h-4 w-4" /> Suspendre
          </Button>
        </div>

        {/* Panier */}
        <PosCartTable
          lines={lines}
          selectedKey={selectedKey}
          onSelect={setSelectedKey}
          onQuantity={(key, qty) => updateLine(key, { quantity: qty })}
          onPrice={(key, price) => updateLine(key, { unit_price: price })}
          onDiscount={(key, pct) => updateLine(key, { discount_percent: pct })}
          onRemove={removeLine}
        />

        {/* Totaux — variante caisse (total géant dominant) */}
        <PosTotalsBar
          variant="giant"
          subtotal={totals.subtotal}
          discountAmount={totals.discountAmount}
          taxPercent={POS_TAX_PERCENT}
          taxAmount={totals.taxAmount}
          total={totals.total}
          itemsCount={totals.itemsCount}
        />

        {/* Encaissement — tuiles de méthode + pavé numérique + bouton géant */}
        <PosPaymentPanel
          method={method}
          onMethod={setMethod}
          amount={amountStr}
          onAmount={setAmountStr}
          total={totals.total}
          disabled={lines.length === 0}
          submitting={submitting}
          error={error}
          onSubmit={handleSubmit}
        />
      </div>

      {/* Colonne produits (60 %) — recherche + catégories + grille tactile */}
      <div className="flex min-w-0 flex-1 flex-col gap-3 overflow-hidden">
        <ProductSearchAdd onAdd={addProduct} categoryId={categoryFilter} />
        <PosCategoryRail
          tree={categoryTree}
          selectedId={categoryFilter}
          onSelect={setCategoryFilter}
        />
        <div className="min-h-0 flex-1 overflow-y-auto pb-1">
          {productsLoading ? (
            <p className="p-6 text-center text-sm text-gray-500">
              Chargement des produits…
            </p>
          ) : (
            <PosProductGrid products={products} onPick={addProduct} />
          )}
        </div>
      </div>

      {/* Popup création de client — la vente en cours est conservée */}
      <PosPartnerDialog
        open={partnerDialogOpen}
        onOpenChange={setPartnerDialogOpen}
        onCreated={(id) => {
          setPartnerId(id);
          setPartnerDialogOpen(false);
        }}
      />
    </div>
  );
}
