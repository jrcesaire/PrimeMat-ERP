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

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArrowLeft,
  Circle,
  ChevronLeft,
  ChevronRight,
  Eye,
  LogOut,
  Pause,
  Play,
  Plus,
  Printer,
  ScanBarcode,
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
import { PosSessionsManager } from "@/components/sales/pos/PosSessionsManager";
import { useCategoryTree, useProducts } from "@/hooks/useCatalogue";
import { useClients } from "@/hooks/useCRM";
import { usePosSessions } from "@/hooks/usePosSessions";
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
import { addProductToCart, type PosCartLine, type PosCartProduct } from "@/lib/pos-cart";
import { cn, formatCurrency, formatNumber } from "@/lib/utils";

/** Ligne du ticket — voir `lib/pos-cart.ts` pour la règle d'ajout. */
type PosLine = PosCartLine;

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
  return (
    <Suspense fallback={null}>
      <PosPageInner />
    </Suspense>
  );
}

function PosPageInner() {
  const { data: clients = [] } = useClients();
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  // La tuile « + Nouvelle Vente » du dashboard PoS arrive avec ?action=new
  // pour ouvrir directement l'écran de scan/saisie (§4.2.2 du PRD).
  const [view, setView] = useState<"history" | "new" | "detail" | "sessions">(
    searchParams.get("action") === "new" ? "new" : "history",
  );
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

  // Statut de la caisse : session ouverte de l'entreprise courante. Sert de
  // repère au caissier (une vente hors session n'est rattachée à aucune caisse).
  const { data: sessionsPage } = usePosSessions(0, 20);
  const openSession =
    (sessionsPage?.items ?? []).find((session) => session.status === "open") ??
    null;
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


  /**
   * Ajoute un produit au ticket.
   *
   * Un clic répété sur la même tuile **incrémente la quantité** de la ligne
   * existante (pièces ou mètres) au lieu d'empiler des lignes identiques.
   * La règle est portée par `lib/pos-cart.ts`, où elle est couverte par des
   * tests unitaires.
   */
  const addProduct = (p: PosCartProduct) => {
    const result = addProductToCart(lines, p, lineKey);
    // La clé n'est consommée que si une nouvelle ligne a réellement été créée.
    if (result.lines.length > lines.length) lineKey += 1;
    setLines(result.lines);
    setSelectedKey(result.selectedKey);
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* Retour à l'accueil du module PoS (mode immersif). */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/dashboard/sales/pos")}
              title="Retour à l'accueil du Point de vente"
            >
              <ArrowLeft className="h-4 w-4" /> Retour
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Point de vente</h1>
              <p className="text-sm text-gray-600">Historique des ventes comptoir</p>
            </div>
          </div>
          <Button
            size="sm"
            onClick={() => setView("sessions")}
            title="Gérer les sessions de caisse (ouverture, clôture, solde)"
          >
            <Circle className="h-4 w-4" /> Sessions
          </Button>
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

  // Vue 3 : gestion des sessions de caisse. L'en-tête (titre + bouton retour)
  // est porté par `PosSessionsManager` afin d'éviter un doublon de titre et de
  // bouton retour sur cet écran.
  if (view === "sessions") {
    return <PosSessionsManager onBack={() => setView("history")} />;
  }

  // Vue 2 : nouvelle vente — disposition de la maquette « GEA ERP » :
  // en-tête de page, puis catalogue à gauche et ticket de caisse à droite.
  return (
    <div className="flex h-full flex-col gap-5 overflow-hidden px-8 py-6">
      {/* En-tête de page */}
      <div className="flex shrink-0 flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-primary">
            Point de vente
          </p>
          <h1 className="mt-1 text-[28px] font-semibold leading-tight text-ink">
            Votre caisse, en toute simplicité.
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Statut de la caisse — le clic ouvre la gestion des sessions. */}
          <button
            type="button"
            onClick={() => setView("sessions")}
            title={
              openSession
                ? `Session ${openSession.reference} ouverte — gérer les sessions de caisse`
                : "Aucune session ouverte — ouvrir une session de caisse"
            }
            className={cn(
              "inline-flex items-center gap-2 rounded-control px-3 py-1.5 transition-colors",
              openSession ? "bg-success-soft" : "bg-warning-soft",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 shrink-0 rounded-full",
                openSession ? "bg-success" : "bg-warning",
              )}
            />
            {openSession ? (
              <>
                <span className="text-[12px] font-semibold text-success">
                  {openSession.reference}
                </span>
                <span className="text-[12px] text-success/80">
                  Session ouverte
                </span>
              </>
            ) : (
              <span className="text-[12px] font-medium text-warning">
                Aucune session ouverte
              </span>
            )}
          </button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/dashboard/sales/pos")}
            title="Retour au menu du point de vente"
          >
            <ArrowLeft className="h-4 w-4" /> Retour
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/dashboard")}
            title="Fermer la caisse et revenir au tableau de bord"
          >
            <LogOut className="h-4 w-4" /> Fermer la caisse
          </Button>
        </div>
      </div>

      {scanMsg && (
        <div className="shrink-0 rounded-control bg-warning-soft px-3 py-2 text-[12px] text-warning">
          {scanMsg}
        </div>
      )}

      {/* Catalogue (gauche) + ticket de caisse (droite) */}
      <div className="flex min-h-0 flex-1 gap-5">
        {/* ---- Colonne catalogue ---- */}
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {/* Recherche + scan */}
          <div className="flex shrink-0 items-center gap-3">
            <div className="min-w-0 flex-1">
              <ProductSearchAdd onAdd={addProduct} categoryId={categoryFilter} />
            </div>
            <Button
              variant="outline"
              className="shrink-0"
              onClick={() => setView("history")}
              title="Historique des ventes et recherche par code-barres"
            >
              <ScanBarcode className="h-4 w-4" /> Scanner
            </Button>
          </div>

          {/* Catégories */}
          <PosCategoryRail
            tree={categoryTree}
            selectedId={categoryFilter}
            onSelect={setCategoryFilter}
          />

          {/* Bandeau de la grille */}
          <div className="flex shrink-0 items-center justify-between text-[13px]">
            <span className="font-semibold text-ink">
              Catalogue{" "}
              <span className="font-normal text-muted">
                · {products.length} produit{products.length > 1 ? "s" : ""}
              </span>
            </span>
            <span className="text-muted">Prix TTC</span>
          </div>

          {/* Grille produits — seule zone défilante de la colonne */}
          <div className="min-h-0 flex-1 overflow-y-auto pb-1">
            {productsLoading ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-[148px] animate-pulse rounded-card bg-subtle"
                  />
                ))}
              </div>
            ) : (
              <PosProductGrid products={products} onPick={addProduct} />
            )}
          </div>

          {/* Rappel des raccourcis — encart de la maquette */}
          <div className="shrink-0 rounded-card bg-primary-soft px-4 py-3">
            <p className="text-[11px] font-semibold text-primary">
              Une caisse pensée pour aller vite.
            </p>
            <p className="mt-1 text-[10px] text-primary/70">
              F2 Rechercher · F4 Client · F8 Encaisser
            </p>
          </div>
        </div>

        {/* ---- Ticket de caisse ---- */}
        <div className="flex w-[380px] shrink-0 flex-col overflow-hidden rounded-card border border-line bg-surface">
          {/* En-tête du ticket */}
          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-line px-5 py-3.5">
            <div className="min-w-0">
              <h2 className="text-[17px] font-semibold text-ink">
                Ticket en cours
              </h2>
              <p className="mt-0.5 text-[11px] text-muted" suppressHydrationWarning>
                {new Date().toLocaleDateString("fr-FR", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                })}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <span className="rounded-chip bg-primary-soft px-2 py-0.5 text-[11px] font-medium text-primary">
                {formatNumber(totals.itemsCount)} article
                {totals.itemsCount > 1 ? "s" : ""}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setLines([])}
                disabled={lines.length === 0}
                title="Vider le ticket"
                aria-label="Vider le ticket"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Client du ticket — facultatif, « client de passage » par défaut */}
          <div className="shrink-0 px-5 pt-3">
            <div className="flex items-center gap-3 rounded-control bg-subtle px-3 py-2">
              <UserRound className="h-4 w-4 shrink-0 text-muted" />
              <div className="min-w-0 flex-1">
                <select
                  className="w-full cursor-pointer bg-transparent text-[12px] font-medium text-ink focus:outline-none"
                  value={partnerId ?? ""}
                  onChange={(e) =>
                    setPartnerId(e.target.value ? Number(e.target.value) : null)
                  }
                  title="Client rattaché au ticket"
                >
                  <option value="">Client de passage</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => setPartnerDialogOpen(true)}
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-chip bg-primary-soft text-primary"
                title="Créer un nouveau client sans quitter la vente"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Lignes du ticket — seule zone défilante du panneau. `min-h-0`
              laisse la liste céder de la place si le pavé numérique est
              déplié, plutôt que de rogner le bouton d'encaissement. */}
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3">
            <PosCartTable
              lines={lines}
              selectedKey={selectedKey}
              onSelect={setSelectedKey}
              onQuantity={(key, qty) => updateLine(key, { quantity: qty })}
              onPrice={(key, price) => updateLine(key, { unit_price: price })}
              onDiscount={(key, pct) => updateLine(key, { discount_percent: pct })}
              onRemove={removeLine}
            />
          </div>

          {/* Pied du ticket : remise, totaux, encaissement */}
          <div className="shrink-0 space-y-3 border-t border-line px-5 py-4">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setSelectedKey(lines[0]?.key ?? null)}
                disabled={lines.length === 0}
                className="text-[12px] font-medium text-primary hover:underline disabled:opacity-50"
                title="Sélectionnez une ligne du ticket pour saisir sa remise"
              >
                Ajouter une remise
              </button>
              <Plus className="h-4 w-4 text-primary" />
            </div>

            <PosTotalsBar
              variant="giant"
              subtotal={totals.subtotal}
              discountAmount={totals.discountAmount}
              taxPercent={POS_TAX_PERCENT}
              taxAmount={totals.taxAmount}
              total={totals.total}
              itemsCount={totals.itemsCount}
            />

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

            <p className="text-center text-[10px] text-faint">
              Paiement sécurisé · Ticket imprimé après encaissement
            </p>
          </div>
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
