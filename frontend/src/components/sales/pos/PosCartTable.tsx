"use client";

import { Minus, Plus, Trash2 } from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";

export interface PosCartLineVM {
  key: number;
  product_id: number;
  name: string;
  reference?: string | null;
  variant_name?: string | null;
  sell_by_length: boolean;
  quantity: number;
  unit_price: number;
  discount_percent: number;
}

interface Props {
  lines: PosCartLineVM[];
  selectedKey: number | null;
  onSelect: (key: number) => void;
  onQuantity: (key: number, qty: number) => void;
  onPrice: (key: number, price: number) => void;
  onDiscount: (key: number, pct: number) => void;
  onRemove: (key: number) => void;
}

export function posLineTotal(l: PosCartLineVM): number {
  const gross = l.quantity * l.unit_price;
  return gross * (1 - (l.discount_percent || 0) / 100);
}

export function PosCartTable({
  lines,
  selectedKey,
  onSelect,
  onQuantity,
  onPrice,
  onDiscount,
  onRemove,
}: Props) {
  if (lines.length === 0) {
    return (
      <div className="rounded-card border border-dashed border-line bg-surface p-8 text-center text-[13px] text-muted">
        Panier vide — recherchez un produit ci-dessus, scannez un code-barres,
        ou utilisez l&apos;ajout rapide.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-card border border-line bg-surface">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="bg-subtle/60 text-left text-[10px] uppercase tracking-[0.08em] text-muted">
            <th className="px-3 py-2">Produit</th>
            <th className="px-3 py-2 text-right">PU</th>
            <th className="px-3 py-2 text-center">Qté</th>
            <th className="px-3 py-2 text-center">Rem.%</th>
            <th className="px-3 py-2 text-right">Total</th>
            <th className="w-10 px-2 py-2" />
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => {
            const active = l.key === selectedKey;
            return (
              <tr
                key={l.key}
                onClick={() => onSelect(l.key)}
                className={cn(
                  "cursor-pointer border-t border-line transition-colors",
                  active ? "bg-primary-soft" : "hover:bg-subtle/60",
                )}
              >
                <td className="max-w-[220px] px-3 py-2">
                  <p className="truncate font-medium text-ink">{l.name}</p>
                  {(l.reference || l.variant_name) && (
                    <p className="truncate text-[11px] italic text-faint">
                      {[l.reference, l.variant_name].filter(Boolean).join(" · ")}
                      {l.sell_by_length ? " · au mètre" : ""}
                    </p>
                  )}
                </td>
                <td className="px-3 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="number"
                    min={0}
                    value={l.unit_price}
                    onChange={(e) => onPrice(l.key, Number(e.target.value))}
                    className="h-10 w-24 rounded-control border border-line bg-surface px-2 text-right text-[13px] text-ink"
                  />
                </td>
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-center gap-1">
                    <button
                      type="button"
                      aria-label="Diminuer la quantité"
                      onClick={() => onQuantity(l.key, Math.max(0, +(l.quantity - 1).toFixed(3)))}
                      className="flex h-10 w-10 items-center justify-center rounded-control border border-line bg-surface text-muted active:bg-subtle"
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <input
                      type="number"
                      min={0}
                      step={l.sell_by_length ? "0.5" : "1"}
                      value={l.quantity}
                      onChange={(e) => onQuantity(l.key, Number(e.target.value))}
                      className="h-10 w-20 rounded-control border border-line bg-surface px-2 text-center text-[13px] font-semibold text-ink"
                    />
                    <button
                      type="button"
                      aria-label="Augmenter la quantité"
                      onClick={() => onQuantity(l.key, +(l.quantity + 1).toFixed(3))}
                      className="flex h-10 w-10 items-center justify-center rounded-control border border-line bg-surface text-muted active:bg-subtle"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                  {l.sell_by_length && (
                    <p className="mt-1 text-center text-xs text-gray-400">
                      {formatNumber(l.quantity, 2)} m
                    </p>
                  )}
                </td>
                <td className="px-3 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={l.discount_percent}
                    onChange={(e) => onDiscount(l.key, Number(e.target.value))}
                    className="h-10 w-16 rounded-control border border-line bg-surface px-2 text-center text-[13px] text-ink"
                  />
                </td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums text-ink">
                  {formatCurrency(posLineTotal(l))}
                </td>
                <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => onRemove(l.key)}
                    className="flex h-10 w-10 items-center justify-center rounded-control text-faint hover:bg-danger-soft hover:text-danger"
                    title="Retirer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

