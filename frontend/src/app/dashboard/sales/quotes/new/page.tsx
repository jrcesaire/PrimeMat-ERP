/**
 * Devis / Commande — formulaire plein écran façon Odoo.
 *
 * - Barre d'actions contextuelle + barre de statut en chevrons
 * - Champs en 2 colonnes (client/adresses | dates/conditions)
 * - Onglets : Lignes · Autres informations · Notes
 * - Tableau de lignes dense avec coupes BAC en sous-lignes dépliables
 * - Remise par ligne, remise globale et TVA — totaux HT / TVA / Total
 */
"use client";

import { Suspense, Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Plus,
  Trash2,
  Scissors,
  ArrowLeft,
  Printer,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useProducts } from "@/hooks/useCatalogue";
import {
  usePartners,
  useSites,
} from "@/hooks/useCRM";
import {
  useCreateQuote,
  useConfirmQuote,
  useOrder,
  useQuote,
  useUpdateOrder,
  useUpdateQuote,
} from "@/hooks/useSales";
import { ClientAutocomplete } from "@/components/crm/client-autocomplete";
import { printOrder, printQuote } from "@/lib/api/pdf";
import { formatCurrency, formatNumber } from "@/lib/utils";
import type { Partner, Product } from "@/lib/types";
import {
  CutsEditor,
  type LineState,
} from "./line-editors";

let lineKey = 1;

function emptyLine(): LineState {
  return {
    key: lineKey++,
    product_id: null,
    description: "",
    sell_by_length: false,
    standard_piece: false,
    quantity: 1,
    unit_price: 0,
    discount_percent: 0,
    cuts: [{ key: Date.now(), quantity: 1, length: 0 }],
  };
}

/** Totaux d'une ligne selon son mode de vente. */
function lineTotals(line: LineState, product: Product | null) {
  const price = Number(line.unit_price) || 0;
  const disc = (Number(line.discount_percent) || 0) / 100;
  if (line.sell_by_length) {
    const totalLength = line.cuts.reduce(
      (s, c) => s + (Number(c.quantity) || 0) * (Number(c.length) || 0),
      0
    );
    const raw = line.cuts.reduce(
      (s, c) => s + (Number(c.quantity) || 0) * (Number(c.length) || 0) * price,
      0
    );
    return { totalLength, subtotal: raw * (1 - disc) };
  }
  if (line.standard_piece) {
    const ul = Number(product?.unit_length) || 0;
    const totalLength = (Number(line.quantity) || 0) * ul;
    return { totalLength, subtotal: totalLength * price * (1 - disc) };
  }
  const totalLength = Number(line.quantity) || 0;
  return { totalLength, subtotal: totalLength * price * (1 - disc) };
}

const PAYMENT_TERMS = [
  "Immédiat",
  "À la commande",
  "7 jours",
  "15 jours",
  "30 jours",
  "45 jours",
  "60 jours",
];

export default function NewQuotePage() {
  return (
    <Suspense fallback={null}>
      <NewQuotePageInner />
    </Suspense>
  );
}

function NewQuotePageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = Number(searchParams.get("id")) || null; // devis
  const editOrderId = Number(searchParams.get("orderId")) || null; // commande
  const editingOrder = !!editOrderId;

  const { data: partners = [] } = usePartners();
  const { data: sites = [] } = useSites();
  const { data: products = [] } = useProducts();
  const createQuote = useCreateQuote();
  const updateQuote = useUpdateQuote();
  const updateOrder = useUpdateOrder();
  const confirmQuote = useConfirmQuote();
  const { data: existingQuote } = useQuote(editId ?? 0);
  const { data: existingOrder } = useOrder(editOrderId ?? 0);

  const entity = existingQuote ?? existingOrder;
  const locked = entity?.status === "confirmed";

  // --- État du formulaire ---
  const [partnerId, setPartnerId] = useState<number | null>(null);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [quoteDate, setQuoteDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [validUntil, setValidUntil] = useState("");
  const [paymentTerm, setPaymentTerm] = useState("Immédiat");
  const [customerReference, setCustomerReference] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("");
  const [taxPercent, setTaxPercent] = useState(0);
  const [globalDiscount, setGlobalDiscount] = useState(0);
  const [lines, setLines] = useState<LineState[]>([emptyLine()]);
  const [activeTab, setActiveTab] = useState<"lines" | "info" | "notes">("lines");
  const [expandedKey, setExpandedKey] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState<string | null>(null);
  const loadedForRef = useRef<string | null>(null);

  const partner: Partner | null =
    partners.find((p) => p.id === partnerId) ?? null;
  const productOf = (line: LineState): Product | null =>
    products.find((p) => p.id === line.product_id) ?? null;
  const partnerSites = sites.filter((s) => s.partner_id === partnerId);

  // --- Pré-remplissage en mode édition (une seule fois par entité) ---
  useEffect(() => {
    if (
      !entity ||
      loadedForRef.current === `${entity.id}-${editingOrder ? "o" : "q"}`
    )
      return;
    loadedForRef.current = `${entity.id}-${editingOrder ? "o" : "q"}`;
    setPartnerId(entity.partner_id);
    setSiteId(entity.site_id ?? null);
    setNotes(entity.notes ?? "");
    setLines(
      entity.lines.map((l) => {
        const product = products.find((p) => p.id === l.product_id) ?? null;
        const cuts = (l.cuts ?? []).map((c, i) => ({
          key: Date.now() + i,
          quantity: Number(c.quantity),
          length: Number(c.length),
        }));
        const isStandardPiece =
          product?.sale_mode === "dual" &&
          cuts.length === 1 &&
          product.unit_length != null &&
          Math.abs(cuts[0].length - Number(product.unit_length)) < 0.001;
        return {
          key: lineKey++,
          product_id: l.product_id,
          description: l.description ?? "",
          sell_by_length: l.sell_by_length && !isStandardPiece,
          standard_piece: isStandardPiece,
          quantity: isStandardPiece
            ? Number(cuts[0].quantity)
            : Number(
                (l as { quantity?: number }).quantity ??
                  (l as { quantity_ordered?: number }).quantity_ordered ??
                  1
              ),
          unit_price: Number(l.unit_price),
          discount_percent: Number(
            (l as { discount_percent?: number }).discount_percent ?? 0
          ),
          cuts:
            cuts.length > 0
              ? cuts
              : [{ key: Date.now(), quantity: 1, length: 0 }],
        };
      })
    );
    if (!editingOrder && "quote_date" in entity) {
      const q = entity as typeof existingQuote & { quote_date: string };
      setQuoteDate(q.quote_date?.slice(0, 10) ?? "");
      setValidUntil(q.valid_until?.slice(0, 10) ?? "");
      setTerms(q.terms ?? "");
      setTaxPercent(Number(q.metadata_json?.tax_percent ?? 0));
      setGlobalDiscount(Number(q.discount_amount ?? 0));
      setPaymentTerm(q.metadata_json?.payment_term ?? "Immédiat");
      setCustomerReference(q.metadata_json?.customer_reference ?? "");
    }
  }, [entity, editingOrder, products]);

  // --- Mutations des lignes ---
  const updateLine = (key: number, patch: Partial<LineState>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const addLine = () => setLines((ls) => [...ls, emptyLine()]);

  const removeLine = (key: number) =>
    setLines((ls) => (ls.length > 1 ? ls.filter((l) => l.key !== key) : ls));

  const handleProductChange = (key: number, productId: number | null) => {
    const product = products.find((p) => p.id === productId) ?? null;
    const patch: Partial<LineState> = {
      product_id: productId,
      standard_piece: false,
      sell_by_length: false,
    };
    if (product) {
      if (product.sale_mode === "length") {
        patch.sell_by_length = true;
        patch.unit_price = Number(product.price_per_meter) || 0;
      } else if (product.sale_mode === "dual") {
        patch.unit_price = Number(product.price_per_meter) || 0;
      } else {
        patch.unit_price = Number(product.selling_price) || 0;
      }
    }
    updateLine(key, patch);
  };

  // --- Totaux globaux ---
  const subTotal = useMemo(
    () => lines.reduce((s, l) => s + lineTotals(l, productOf(l)).subtotal, 0),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lines, products]
  );
  const base = Math.max(subTotal - (Number(globalDiscount) || 0), 0);
  const taxAmount = base * ((Number(taxPercent) || 0) / 100);
  const grandTotal = base + taxAmount;

  // --- Enregistrement ---
  const buildPayloadLines = () =>
    lines
      .filter(
        (l): l is LineState & { product_id: number } => l.product_id != null
      )
      .map((l) => {
        const product = productOf(l);
        const isBac =
          !!product &&
          (product.sale_mode === "length" ||
            (l.sell_by_length && !l.standard_piece));
        if (isBac) {
          return {
            product_id: l.product_id,
            quantity: 1,
            unit: "ml",
            sell_by_length: true,
            unit_price: l.unit_price,
            discount_percent: l.discount_percent,
            cuts: l.cuts
              .filter((c) => Number(c.length) > 0 && Number(c.quantity) > 0)
              .map((c) => ({ quantity: c.quantity, length: c.length })),
          };
        }
        const totalLen = lineTotals(l, product).totalLength;
        return {
          product_id: l.product_id,
          ...(editingOrder
            ? { quantity_ordered: totalLen }
            : { quantity: l.quantity }),
          unit: l.standard_piece ? "pièce" : (product as unknown as { unit?: string } | null)?.unit ?? "u",
          sell_by_length: false,
          unit_price: l.unit_price,
          discount_percent: l.discount_percent,
        };
      });

  const handleSave = async () => {
    setError(null);
    setJustSaved(null);
    if (!partnerId) {
      setError("Veuillez sélectionner ou créer un client.");
      return;
    }
    if (!lines.some((l) => l.product_id != null)) {
      setError("Ajoutez au moins une ligne avec un produit.");
      return;
    }
    const payloadLines = buildPayloadLines();
    try {
      if (editId) {
        await updateQuote.mutateAsync({
          id: editId,
          data: {
            partner_id: partnerId,
            site_id: siteId,
            quote_date: quoteDate || undefined,
            valid_until: validUntil || null,
            notes: notes || null,
            terms: terms || null,
            discount_amount: Number(globalDiscount) || 0,
            tax_percent: Number(taxPercent) || 0,
            payment_term: paymentTerm,
            customer_reference: customerReference || null,
            lines: payloadLines,
          },
        });
        setJustSaved("Devis enregistré");
      } else if (editOrderId) {
        await updateOrder.mutateAsync({
          id: editOrderId,
          data: {
            partner_id: partnerId,
            site_id: siteId,
            delivery_date_planned: deliveryDate || null,
            notes: notes || null,
            lines: payloadLines,
          },
        });
        setJustSaved("Commande enregistrée");
      } else {
        const created = await createQuote.mutateAsync({
          partner_id: partnerId,
          site_id: siteId,
          quote_date: quoteDate || undefined,
          valid_until: validUntil || null,
          notes: notes || null,
          terms: terms || null,
          discount_amount: Number(globalDiscount) || 0,
          tax_percent: Number(taxPercent) || 0,
          payment_term: paymentTerm,
          customer_reference: customerReference || null,
          lines: payloadLines,
        });
        // Reste sur le document (façon Odoo) — l'URL porte désormais l'id
        router.replace(`/dashboard/sales/quotes/new?id=${created.id}`);
        setJustSaved(`Devis ${created.reference} créé`);
        printQuote(created.id).catch(() => undefined);
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? (err as Error)?.message;
      setError(detail || "Erreur lors de l'enregistrement.");
    }
  };

  const handleConfirm = async () => {
    if (!editId) return;
    setError(null);
    try {
      const order = await confirmQuote.mutateAsync(editId);
      setJustSaved(`Devis confirmé — commande ${order.reference} créée`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || "Erreur lors de la confirmation du devis.");
    }
  };

  const handlePrint = () => {
    if (editId)
      printQuote(editId).catch(() =>
        alert("Impossible de générer le PDF du devis.")
      );
    else if (editOrderId)
      printOrder(editOrderId).catch(() => alert("Impossible de générer le PDF."));
  };

  const busy =
    createQuote.isPending || updateQuote.isPending || updateOrder.isPending;

  // Titre + étape du workflow
  const title = editingOrder
    ? entity?.reference ?? "Nouvelle commande"
    : entity?.reference ?? "Nouveau devis";
  const timelineSteps = editingOrder
    ? ["Brouillon", "Confirmée"]
    : ["Brouillon", "Envoyé", "Confirmé"];
  const currentStep = locked ? timelineSteps.length : 1;

  return (
    <div className="mx-auto max-w-6xl space-y-5 pb-24">
      {/* Barre d'actions (façon Odoo) */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="flex items-center gap-1"
          onClick={() => router.push("/dashboard/sales")}
        >
          <ArrowLeft className="h-4 w-4" />
          Retour
        </Button>
        <div className="mx-1 h-6 w-px bg-gray-200" />
        {!locked && (
          <Button onClick={handleSave} disabled={busy}>
            {busy ? "Enregistrement…" : "Enregistrer"}
          </Button>
        )}
        {!editingOrder && editId && !locked && (
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={handleConfirm}
            disabled={confirmQuote.isPending}
          >
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            Confirmer
          </Button>
        )}
        {entity && (
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={handlePrint}
          >
            <Printer className="h-4 w-4" />
            Imprimer
          </Button>
        )}

        {/* Barre de statut — chevrons du workflow */}
        <div className="ml-auto flex items-center overflow-hidden rounded-md border border-gray-200">
          {timelineSteps.map((step, i) => {
            const stepNo = i + 1;
            const isCurrent = stepNo === currentStep;
            const isDone = stepNo < currentStep;
            return (
              <div
                key={step}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium ${
                  isCurrent
                    ? "bg-green-50 text-green-700"
                    : isDone
                      ? "text-green-600"
                      : "text-gray-400"
                }`}
              >
                {step}
                {i < timelineSteps.length - 1 && (
                  <ChevronRight className="h-3.5 w-3.5 text-gray-300" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Titre du document */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        {entity && (
          <p className="mt-0.5 text-sm text-gray-500">
            {editingOrder ? "Commande client" : "Devis client"} · créé le{" "}
            {new Date(entity.created_at).toLocaleString("fr-FR")}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {justSaved && (
        <div className="rounded-md border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {justSaved}
        </div>
      )}

      {/* Formulaire verrouillé si confirmé */}
      <fieldset disabled={locked} className="space-y-5">
        {/* Champs en 2 colonnes */}
        <Card className="grid grid-cols-1 gap-6 p-5 md:grid-cols-2">
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Client *
              </label>
              <ClientAutocomplete
                value={partnerId}
                onChange={(v) => {
                  setPartnerId(v);
                  setSiteId(null);
                }}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Adresse de facturation
              </label>
              <p className="min-h-9 rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-600">
                {partner
                  ? (() => {
                      const addr = partner.addresses?.[0];
                      const txt = [addr?.line_1, addr?.city]
                        .filter(Boolean)
                        .join(", ");
                      return txt || partner.phone || "—";
                    })()
                  : "Sélectionnez un client"}
              </p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">
                  {editingOrder ? "Date de commande" : "Date du devis"}
                </label>
                {editingOrder ? (
                  <p className="min-h-9 rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-600">
                    {entity && "order_date" in entity
                      ? String(entity.order_date)
                      : quoteDate}
                  </p>
                ) : (
                  <Input
                    type="date"
                    value={quoteDate}
                    onChange={(e) => setQuoteDate(e.target.value)}
                  />
                )}
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">
                  {editingOrder ? "Livraison prévue" : "Validité (expiration)"}
                </label>
                <Input
                  type="date"
                  value={editingOrder ? deliveryDate : validUntil}
                  onChange={(e) =>
                    editingOrder
                      ? setDeliveryDate(e.target.value)
                      : setValidUntil(e.target.value)
                  }
                />
              </div>
            </div>
            {!editingOrder && (
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">
                  Conditions de paiement
                </label>
                <select
                  value={paymentTerm}
                  onChange={(e) => setPaymentTerm(e.target.value)}
                  className="h-9 w-full rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-primary focus:outline-none"
                >
                  {PAYMENT_TERMS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </Card>

        {/* Onglets */}
        <div className="flex gap-1 border-b border-gray-200">
          {(
            [
              ["lines", "Lignes de commande"],
              ["info", "Autres informations"],
              ["notes", "Notes"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === key
                  ? "border-primary text-primary"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {activeTab === "lines" && (
          <Card className="overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs uppercase text-gray-500">
                  <th className="px-3 py-2.5">Produit</th>
                  <th className="px-3 py-2.5 w-28">Quantité</th>
                  <th className="px-3 py-2.5 w-24">Unité</th>
                  <th className="px-3 py-2.5 w-28 text-right">P.U.</th>
                  <th className="px-3 py-2.5 w-20 text-right">Rem.%</th>
                  <th className="px-3 py-2.5 w-32 text-right">Montant</th>
                  <th className="px-2 py-2.5 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => {
                  const product = productOf(line);
                  const totals = lineTotals(line, product);
                  const isBac =
                    product?.sale_mode === "length" ||
                    (product?.sale_mode === "dual" &&
                      !line.standard_piece &&
                      line.sell_by_length);
                  const isDual = product?.sale_mode === "dual";
                  const expanded = expandedKey === line.key;
                  return (
                    <Fragment key={line.key}>
                      {/* Ligne principale */}
                      <tr className="border-b border-gray-100">
                        <td className="px-3 py-2">
                          <select
                            value={line.product_id ?? ""}
                            onChange={(e) =>
                              handleProductChange(
                                line.key,
                                e.target.value ? Number(e.target.value) : null
                              )
                            }
                            className="h-8 w-full max-w-xs rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-primary focus:outline-none"
                          >
                            <option value="">— Choisir un produit —</option>
                            {products.map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.name}
                                {p.sale_mode === "length"
                                  ? " (au m)"
                                  : p.sale_mode === "dual"
                                    ? " (ml / pièce)"
                                    : ""}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          {isBac ? (
                            <span
                              className="block text-right font-medium text-gray-700"
                              title="Longueur totale (somme des coupes)"
                            >
                              {formatNumber(totals.totalLength, 2)}
                            </span>
                          ) : (
                            <Input
                              type="number"
                              min={0}
                              className="h-8 text-right"
                              value={line.quantity}
                              onChange={(e) =>
                                updateLine(line.key, {
                                  quantity: Number(e.target.value),
                                })
                              }
                            />
                          )}
                        </td>
                        <td className="px-3 py-2 text-xs text-gray-500">
                          {isBac
                            ? "ml"
                            : line.standard_piece
                              ? `pièce${product?.unit_length ? ` de ${formatNumber(product.unit_length, 2)} m` : ""}`
                              : (product as unknown as { unit?: string } | null)?.unit ?? "u"}
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            className="h-8 text-right"
                            value={line.unit_price}
                            onChange={(e) =>
                              updateLine(line.key, {
                                unit_price: Number(e.target.value),
                              })
                            }
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="number"
                            min={0}
                            max={100}
                            className="h-8 text-right"
                            value={line.discount_percent}
                            onChange={(e) =>
                              updateLine(line.key, {
                                discount_percent: Number(e.target.value),
                              })
                            }
                          />
                        </td>
                        <td className="px-3 py-2 text-right font-semibold text-gray-900">
                          {formatCurrency(totals.subtotal)}
                        </td>
                        <td className="px-2 py-2 text-center">
                          <button
                            onClick={() => removeLine(line.key)}
                            title="Supprimer la ligne"
                            className="text-gray-400 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                      {/* Sous-ligne : détail des coupes BAC */}
                      {isBac && (
                        <tr
                          key={`${line.key}-sub`}
                          className="border-b border-gray-100 bg-gray-50/60"
                        >
                          <td colSpan={7} className="px-3 py-1.5">
                            <div className="flex items-center gap-3">
                              <Scissors className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                              <span className="flex-1 text-xs italic text-gray-600">
                                {line.cuts.filter((c) => Number(c.length) > 0)
                                  .length > 0
                                  ? line.cuts
                                      .filter((c) => Number(c.length) > 0)
                                      .map(
                                        (c) =>
                                          `${formatNumber(c.quantity, 0)} feuille(s) de ${formatNumber(c.length, 2)} m`
                                      )
                                      .join(", ")
                                  : "Aucune coupe définie"}
                              </span>
                              <button
                                onClick={() =>
                                  setExpandedKey(expanded ? null : line.key)
                                }
                                className="text-xs font-medium text-primary hover:underline"
                              >
                                {expanded ? "Masquer" : "✂ Modifier les coupes"}
                              </button>
                            </div>
                            {expanded && (
                              <div className="mt-2 rounded-md border border-gray-200 bg-white p-3">
                                <CutsEditor
                                  line={line}
                                  onLineChange={(patch) =>
                                    updateLine(line.key, patch)
                                  }
                                />
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                      {/* Sous-ligne : choix de mode pour les produits dual */}
                      {isDual && !line.standard_piece && !isBac && (
                        <tr
                          key={`${line.key}-dual`}
                          className="border-b border-gray-100 bg-gray-50/60"
                        >
                          <td colSpan={7} className="px-3 py-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500">
                                Mode de vente :
                              </span>
                              <button
                                onClick={() =>
                                  updateLine(line.key, {
                                    standard_piece: true,
                                    sell_by_length: false,
                                  })
                                }
                                className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                              >
                                À la pièce standard
                              </button>
                              <button
                                onClick={() =>
                                  updateLine(line.key, {
                                    sell_by_length: true,
                                    standard_piece: false,
                                  })
                                }
                                className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                              >
                                Au mètre (coupes)
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                      {/* Sous-ligne : rappel prorata pièce standard */}
                      {isDual && line.standard_piece && (
                        <tr
                          key={`${line.key}-std`}
                          className="border-b border-gray-100 bg-gray-50/60"
                        >
                          <td
                            colSpan={7}
                            className="px-3 py-1.5 text-xs italic text-gray-600"
                          >
                            Pièce standard de{" "}
                            {formatNumber(product?.unit_length ?? 0, 2)} m —
                            facturée au prorata du mètre linéaire (
                            {formatNumber(line.quantity, 0)} ×{" "}
                            {formatNumber(product?.unit_length ?? 0, 2)} m ×{" "}
                            {formatCurrency(line.unit_price)}/ml).
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
            <div className="border-t border-gray-100 px-3 py-2">
              <button
                onClick={addLine}
                className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                <Plus className="h-4 w-4" />
                Ajouter un produit
              </button>
            </div>
          </Card>
        )}

        {activeTab === "info" && (
          <Card className="grid grid-cols-1 gap-6 p-5 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Référence client (bon de commande)
              </label>
              <Input
                value={customerReference}
                onChange={(e) => setCustomerReference(e.target.value)}
                placeholder="Ex. BC-2026-88"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Chantier / lieu de livraison
              </label>
              {partnerSites.length > 0 ? (
                <select
                  value={siteId ?? ""}
                  onChange={(e) =>
                    setSiteId(e.target.value ? Number(e.target.value) : null)
                  }
                  className="h-9 w-full rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="">— Aucun —</option>
                  {partnerSites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="min-h-9 rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-sm text-gray-500">
                  Aucun chantier enregistré pour ce client
                </p>
              )}
            </div>
          </Card>
        )}

        {activeTab === "notes" && (
          <Card className="space-y-4 p-5">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Notes internes (non imprimées)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none"
                placeholder="Notes visibles uniquement en interne…"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">
                Conditions particulières (imprimées sur le devis)
              </label>
              <textarea
                value={terms}
                onChange={(e) => setTerms(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none"
                placeholder="Ex. Matériaux vendus aux risques du client. Les articles découpés ne sont ni repris ni échangés…"
              />
            </div>
          </Card>
        )}
      </fieldset>

      {/* Barre des totaux — ancrée en bas */}
      <Card className="fixed inset-x-0 bottom-0 z-30 border-t shadow-lg md:left-64">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-end gap-x-8 gap-y-2 px-6 py-3">
          <div className="text-sm">
            <span className="text-gray-500">Sous-total HT : </span>
            <span className="font-medium text-gray-900">
              {formatCurrency(subTotal)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Remise globale :</span>
            <Input
              type="number"
              min={0}
              className="h-8 w-28 text-right"
              value={globalDiscount}
              onChange={(e) => setGlobalDiscount(Number(e.target.value) || 0)}
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">TVA % :</span>
            <Input
              type="number"
              min={0}
              max={100}
              className="h-8 w-16 text-right"
              value={taxPercent}
              onChange={(e) => setTaxPercent(Number(e.target.value) || 0)}
            />
            <span className="font-medium text-gray-900">
              {formatCurrency(taxAmount)}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div>
              <p className="text-xs text-gray-500">Total</p>
              <p className="text-xl font-bold text-gray-900">
                {formatCurrency(grandTotal)}
              </p>
            </div>
            {!locked && (
              <Button onClick={handleSave} disabled={busy} size="lg">
                {busy ? "Enregistrement…" : "Enregistrer"}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}