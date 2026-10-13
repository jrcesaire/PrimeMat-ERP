"use client";

import { formatCurrency, formatNumber } from "@/lib/utils";

interface Props {
  subtotal: number;
  discountAmount: number;
  taxPercent: number;
  taxAmount: number;
  total: number;
  itemsCount: number;
  /**
   * `grid`   : barre horizontale 5 colonnes (vue dense / historique).
   * `giant`  : mise en page caisse — total géant dominant + détails compacts
   *            (variante des maquettes POS, colonne gauche).
   */
  variant?: "grid" | "giant";
}

export function PosTotalsBar({
  subtotal,
  discountAmount,
  taxPercent,
  taxAmount,
  total,
  itemsCount,
  variant = "grid",
}: Props) {
  if (variant === "giant") {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-4 gap-2 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">
              Sous-total
            </p>
            <p className="font-semibold text-gray-900">
              {formatCurrency(subtotal)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">
              Remise
            </p>
            <p className="font-semibold text-gray-900">
              {formatCurrency(discountAmount)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">
              TVA ({formatNumber(taxPercent, 2)} %)
            </p>
            <p className="font-semibold text-gray-900">
              {formatCurrency(taxAmount)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">
              Articles
            </p>
            <p className="font-semibold text-gray-900">
              {formatNumber(itemsCount, 2)}
            </p>
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between border-t border-gray-100 pt-3">
          <span className="text-sm font-medium uppercase tracking-wide text-gray-500">
            Total
          </span>
          <span className="text-4xl font-extrabold tracking-tight text-gray-900">
            {formatCurrency(total)}
          </span>
        </div>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 rounded-lg border border-gray-200 bg-white p-3 text-sm sm:grid-cols-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400">Sous-total</p>
        <p className="font-semibold text-gray-900">{formatCurrency(subtotal)}</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400">Remise</p>
        <p className="font-semibold text-gray-900">{formatCurrency(discountAmount)}</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400">
          TVA ({formatNumber(taxPercent, 2)} %)
        </p>
        <p className="font-semibold text-gray-900">{formatCurrency(taxAmount)}</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400">Articles</p>
        <p className="font-semibold text-gray-900">{formatNumber(itemsCount, 2)}</p>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400">Total</p>
        <p className="text-lg font-bold text-gray-900">{formatCurrency(total)}</p>
      </div>
    </div>
  );
}

export interface PosTotals {
  subtotal: number;
  discountAmount: number;
  taxable: number;
  taxAmount: number;
  total: number;
  itemsCount: number;
}

export function computePosTotals(
  lines: { quantity: number; unit_price: number; discount_percent: number }[],
  discountAmount: number,
  taxPercent: number,
): PosTotals {
  const subtotal = lines.reduce((s, l) => {
    const gross = l.quantity * l.unit_price;
    return s + gross * (1 - (l.discount_percent || 0) / 100);
  }, 0);
  const taxable = Math.max(0, subtotal - (discountAmount || 0));
  const taxAmount = taxable * ((taxPercent || 0) / 100);
  const itemsCount = lines.reduce((s, l) => s + (l.quantity || 0), 0);
  return {
    subtotal,
    discountAmount: discountAmount || 0,
    taxable,
    taxAmount,
    total: taxable + taxAmount,
    itemsCount,
  };
}
