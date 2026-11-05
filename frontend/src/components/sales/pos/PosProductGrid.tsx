/**
 * Grille produits tactile de la caisse — tuiles cliquables.
 *
 * Design « GEA ERP » : icône encadrée, référence, désignation, prix mis en
 * avant et bouton « + » coloré. Chaque tuile ajoute le produit au panier d'un
 * seul geste.
 */
"use client";

import { Package, Plus } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import type { Product } from "@/lib/types";

interface Props {
  products: Product[];
  onPick: (product: Product) => void;
}

export function PosProductGrid({ products, onPick }: Props) {
  if (products.length === 0) {
    return (
      <div className="rounded-card border border-dashed border-line bg-surface p-10 text-center text-[13px] text-muted">
        Aucun produit pour cette catégorie — essayez une autre catégorie ou
        utilisez la recherche ci-dessus.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
      {products.map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onPick(p)}
          className="flex h-[148px] flex-col justify-between rounded-card border border-line bg-surface p-3 text-left transition-colors hover:border-primary/40 active:scale-[0.98]"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-subtle">
              <Package className="h-4 w-4 text-muted" />
            </div>
            {p.sell_by_length && (
              <span className="shrink-0 rounded-chip bg-warning-soft px-1.5 py-0.5 text-[10px] font-medium text-warning">
                au mètre
              </span>
            )}
          </div>

          <div className="min-w-0">
            <p className="truncate text-[10px] uppercase tracking-wide text-faint">
              {p.reference}
            </p>
            <p className="mt-0.5 line-clamp-2 text-[13px] font-semibold leading-snug text-ink">
              {p.name}
            </p>
          </div>

          <div className="flex items-end justify-between gap-2">
            <span className="text-[15px] font-semibold tabular-nums text-ink">
              {p.sell_by_length
                ? `${formatCurrency(p.price_per_meter ?? 0)}/ml`
                : formatCurrency(p.selling_price ?? 0)}
            </span>
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-chip bg-primary-soft text-primary">
              <Plus className="h-3.5 w-3.5" />
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}