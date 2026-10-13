/**
 * Grille produits tactile (maquette caisse A) — tuiles cliquables.
 *
 * Chaque tuile ajoute le produit au panier d'un seul geste : nom,
 * référence, prix de vente (ou prix au mètre pour les produits vendus
 * à la longueur).
 */
"use client";

import { formatCurrency } from "@/lib/utils";
import type { Product } from "@/lib/types";

interface Props {
  products: Product[];
  onPick: (product: Product) => void;
}

export function PosProductGrid({ products, onPick }: Props) {
  if (products.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-500">
        Aucun produit pour cette catégorie — essayez une autre catégorie ou
        utilisez la recherche ci-dessus.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
      {products.map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onPick(p)}
          className="flex h-32 flex-col justify-between rounded-lg border border-gray-200 bg-white p-3 text-left shadow-sm transition hover:border-primary hover:shadow-md active:scale-[0.98]"
        >
          <div className="min-w-0">
            <p className="line-clamp-2 text-sm font-semibold leading-snug text-gray-900">
              {p.name}
            </p>
            <p className="mt-1 truncate text-xs text-gray-400">{p.reference}</p>
          </div>
          <div className="flex items-end justify-between gap-2">
            <span className="text-sm font-bold text-gray-900">
              {p.sell_by_length
                ? `${formatCurrency(p.price_per_meter ?? 0)}/ml`
                : formatCurrency(p.selling_price ?? 0)}
            </span>
            {p.sell_by_length && (
              <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                au mètre
              </span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}