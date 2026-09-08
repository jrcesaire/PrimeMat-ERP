/**
 * Page Achats — besoins d'achat dérivés des commandes confirmées.
 */
"use client";

import { useMemo } from "react";
import { Card } from "@/components/ui/card";
import { useOrders } from "@/hooks/useSales";
import { useProducts } from "@/hooks/useCatalogue";
import { formatCurrency } from "@/lib/utils";

export default function PurchasesPage() {
  const { data: orders = [], isLoading } = useOrders();
  const { data: products = [] } = useProducts();

  // Agrège les besoins d'achat de toutes les commandes confirmées
  const needs = useMemo(() => {
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
    return [...byProduct.entries()].map(([productId, info]) => ({
      productId,
      ...info,
    }));
  }, [orders, products]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Achats</h1>
        <p className="text-sm text-gray-600">
          Besoins d'achat issus des commandes confirmées (à acheter auprès des fournisseurs)
        </p>
      </div>

      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : needs.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">
            Aucun besoin d'achat en cours.
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
                <tr key={n.productId} className="border-b border-gray-100 hover:bg-gray-50">
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

      <p className="text-xs text-gray-400">
        Les bons de commande fournisseur et réceptions seront ajoutés dans une
        prochaine itération du module Achats.
      </p>
    </div>
  );
}
