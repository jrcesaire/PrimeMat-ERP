/**
 * Point de vente (vente comptoir) — panier → encaissement → ticket.
 */
"use client";

import { useMemo, useState } from "react";
import { Trash2, ShoppingCart } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useProducts } from "@/hooks/useCatalogue";
import { useClients } from "@/hooks/useCRM";
import { apiClient } from "@/lib/api/client";
import { printPosTicket } from "@/lib/api/pdf";
import { formatCurrency } from "@/lib/utils";

interface PosLine {
  key: number;
  product_id: number;
  name: string;
  sell_by_length: boolean;
  quantity: number; // pièces ou mètres selon le produit
  unit_price: number;
}

let lineKey = 1;

export default function PosPage() {
  const { data: clients = [] } = useClients();
  const { data: products = [] } = useProducts();

  const [partnerId, setPartnerId] = useState<number | null>(null);
  const [lines, setLines] = useState<PosLine[]>([]);
  const [method, setMethod] = useState("cash");
  const [amountReceived, setAmountReceived] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const total = useMemo(
    () => lines.reduce((s, l) => s + l.quantity * l.unit_price, 0),
    [lines],
  );

  const addProduct = (productId: number) => {
    const p = products.find((x) => x.id === productId);
    if (!p) return;
    const existing = lines.find((l) => l.product_id === productId);
    if (existing && !p.sell_by_length) {
      setLines((ls) =>
        ls.map((l) => (l.product_id === productId ? { ...l, quantity: l.quantity + 1 } : l)),
      );
      return;
    }
    setLines((ls) => [
      ...ls,
      {
        key: lineKey++,
        product_id: p.id,
        name: p.name,
        sell_by_length: !!p.sell_by_length,
        quantity: 1,
        unit_price: p.sell_by_length ? (p.price_per_meter ?? 0) : (p.selling_price ?? 0),
      },
    ]);
  };

  const removeLine = (key: number) => setLines((ls) => ls.filter((l) => l.key !== key));

  const handleSubmit = async () => {
    setError(null);
    if (!partnerId) return setError("Sélectionnez un client (ou créez-le dans Contacts).");
    if (lines.length === 0) return setError("Ajoutez au moins un produit.");
    setSubmitting(true);
    try {
      const payload = {
        partner_id: partnerId,
        method,
        amount: amountReceived > 0 ? amountReceived : total,
        lines: lines.map((l) => ({
          product_id: l.product_id,
          description: l.name,
          quantity_ordered: l.quantity,
          unit: l.sell_by_length ? "ml" : "p",
          sell_by_length: l.sell_by_length,
          unit_price: l.unit_price,
          ...(l.sell_by_length ? { cuts: [{ quantity: 1, length: l.quantity }] } : {}),
        })),
      };
      const res = await apiClient.post("/sales/pos/sales", payload);
      const order = res.data as { order?: { id?: number }; id?: number; order_id?: number };
      const orderId = order?.order?.id ?? order?.order_id ?? order?.id;
      if (orderId) {
        try {
          await printPosTicket(orderId);
        } catch {
          /* ticket accessible via la commande */
        }
      }
      setLines([]);
      setAmountReceived(0);
      alert("Vente comptoir enregistrée ✓");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la vente");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Point de vente</h1>
        <p className="text-sm text-gray-600">Vente comptoir — encaissement direct</p>
      </div>

      <Card className="p-4">
        <label className="mb-1 block text-sm font-medium text-gray-700">Client *</label>
        <select
          className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm"
          value={partnerId ?? ""}
          onChange={(e) => setPartnerId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— Choisir un client —</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </Card>

      {/* Sélection produits */}
      <Card className="p-4">
        <h2 className="mb-3 font-semibold text-gray-800">Produits</h2>
        <div className="flex flex-wrap gap-2">
          {products.map((p) => (
            <button
              key={p.id}
              onClick={() => addProduct(p.id)}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-left text-sm hover:border-blue-400 hover:bg-blue-50"
            >
              <span className="block font-medium text-gray-800">{p.name}</span>
              <span className="text-xs text-gray-500">
                {p.sell_by_length
                  ? `${formatCurrency(p.price_per_meter ?? 0)}/ml`
                  : formatCurrency(p.selling_price ?? 0)}
              </span>
            </button>
          ))}
        </div>
      </Card>

      {/* Panier */}
      <Card className="overflow-hidden p-0">
        <h2 className="px-4 pt-4 font-semibold text-gray-800">Panier</h2>
        {lines.length === 0 ? (
          <div className="p-10 text-center">
            <ShoppingCart className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="text-sm text-gray-500">Cliquez sur un produit pour l'ajouter.</p>
          </div>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Produit</th>
                <th className="w-32 px-4 py-3">Qté (pièce/m)</th>
                <th className="w-36 px-4 py-3">Prix unit.</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.key} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {l.name}
                    {l.sell_by_length && (
                      <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">au m</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Input
                      type="number"
                      min={0}
                      value={l.quantity}
                      onChange={(e) =>
                        setLines((ls) =>
                          ls.map((x) =>
                            x.key === l.key ? { ...x, quantity: Number(e.target.value) } : x,
                          ),
                        )
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Input
                      type="number"
                      min={0}
                      value={l.unit_price}
                      onChange={(e) =>
                        setLines((ls) =>
                          ls.map((x) =>
                            x.key === l.key ? { ...x, unit_price: Number(e.target.value) } : x,
                          ),
                        )
                      }
                    />
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {formatCurrency(l.quantity * l.unit_price)}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => removeLine(l.key)} className="text-gray-400 hover:text-red-600" title="Retirer">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Encaissement */}
      <Card className="sticky bottom-4 space-y-3 p-4 shadow-lg">
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-gray-500">Total à encaisser</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(total)}</p>
          </div>
          <div className="flex items-end gap-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Mode</label>
              <select
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                <option value="cash">Espèces</option>
                <option value="mobile_money">Mobile Money</option>
                <option value="bank">Virement</option>
                <option value="check">Chèque</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Montant reçu</label>
              <Input
                type="number"
                min={0}
                value={amountReceived || ""}
                onChange={(e) => setAmountReceived(Number(e.target.value))}
                className="w-32"
              />
            </div>
            <Button size="lg" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Encaissement…" : "Encaisser"}
            </Button>
          </div>
        </div>
        {amountReceived > total && (
          <p className="text-sm font-medium text-green-700">
            Monnaie à rendre : {formatCurrency(amountReceived - total)}
          </p>
        )}
      </Card>
    </div>
  );
}
