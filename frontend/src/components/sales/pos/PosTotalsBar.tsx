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
      <div className="rounded-card border border-line bg-surface p-4">
        <dl className="space-y-2 text-[13px]">
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted">Sous-total HT</dt>
            <dd className="tabular-nums text-ink">{formatCurrency(subtotal)}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted">Remise</dt>
            <dd className="tabular-nums text-ink">
              {formatCurrency(discountAmount)}
            </dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted">TVA ({formatNumber(taxPercent, 2)} %)</dt>
            <dd className="tabular-nums text-ink">{formatCurrency(taxAmount)}</dd>
          </div>
        </dl>
        <div className="mt-3 flex items-baseline justify-between gap-3 border-t border-line pt-3">
          <span className="text-[15px] font-semibold text-ink">Total TTC</span>
          <span className="text-[22px] font-semibold tabular-nums text-ink">
            {formatCurrency(total)}
          </span>
        </div>
        <p className="mt-1 text-right text-[11px] text-faint">
          {formatNumber(itemsCount, 2)} article(s)
        </p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 rounded-card border border-line bg-surface p-3 text-[13px] sm:grid-cols-5">
      <div>
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">Sous-total</p>
        <p className="font-semibold text-ink">{formatCurrency(subtotal)}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">Remise</p>
        <p className="font-semibold text-ink">{formatCurrency(discountAmount)}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">
          TVA ({formatNumber(taxPercent, 2)} %)
        </p>
        <p className="font-semibold text-ink">{formatCurrency(taxAmount)}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">Articles</p>
        <p className="font-semibold text-ink">{formatNumber(itemsCount, 2)}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">Total</p>
        <p className="text-[17px] font-semibold text-ink">{formatCurrency(total)}</p>
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
