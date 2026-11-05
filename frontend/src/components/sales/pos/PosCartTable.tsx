/**
 * Lignes du ticket de caisse.
 *
 * Présentées comme sur la maquette « GEA ERP » : une **liste verticale** et non
 * un tableau. Un tableau à six colonnes ne tenait pas dans la largeur du
 * panneau de ticket (340 px) — la colonne « Qté » débordait hors de la carte.
 *
 * Chaque ligne reste entièrement éditable : prix unitaire, remise en %,
 * quantité (pièces ou mètres) et suppression.
 */
"use client";

import { Minus, Package, Plus, Trash2 } from "lucide-react";
import { cn, formatCurrency, formatNumber } from "@/lib/utils";

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
      <div className="rounded-control border border-dashed border-line p-6 text-center text-[12px] text-muted">
        Panier vide — touchez un produit du catalogue pour l&apos;ajouter au
        ticket.
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {lines.map((line) => {
        const active = line.key === selectedKey;
        const detail = [line.reference, line.variant_name]
          .filter(Boolean)
          .join(" · ");

        return (
          <div
            key={line.key}
            onClick={() => onSelect(line.key)}
            className={cn(
              "cursor-pointer rounded-control border p-2.5 transition-colors",
              active
                ? "border-primary/40 bg-primary-soft"
                : "border-transparent hover:bg-subtle/70",
            )}
          >
            {/* Produit et montant de la ligne */}
            <div className="flex items-start gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-surface">
                <Package className="h-4 w-4 text-muted" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="line-clamp-2 text-[12px] font-medium leading-snug text-ink">
                    {line.name}
                  </p>
                  <span className="shrink-0 text-[12px] font-semibold tabular-nums text-ink">
                    {formatCurrency(posLineTotal(line))}
                  </span>
                </div>
                {(detail || line.sell_by_length) && (
                  <p className="mt-0.5 truncate text-[10px] text-faint">
                    {detail}
                    {line.sell_by_length ? `${detail ? " · " : ""}au mètre` : ""}
                  </p>
                )}
              </div>
            </div>

            {/* Prix unitaire, remise, quantité et suppression */}
            <div
              className="mt-2 flex items-center justify-between gap-2 pl-[42px]"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={0}
                  value={line.unit_price}
                  onChange={(e) => onPrice(line.key, Number(e.target.value))}
                  aria-label={`Prix unitaire — ${line.name}`}
                  title={
                    line.sell_by_length ? "Prix au mètre linéaire" : "Prix unitaire"
                  }
                  className="h-7 w-[62px] rounded-chip border border-line bg-surface px-1.5 text-right text-[11px] tabular-nums text-ink"
                />
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={line.discount_percent}
                  onChange={(e) => onDiscount(line.key, Number(e.target.value))}
                  aria-label={`Remise en pourcentage — ${line.name}`}
                  title="Remise sur la ligne (%)"
                  className="h-7 w-[36px] rounded-chip border border-line bg-surface px-1 text-center text-[11px] tabular-nums text-ink"
                />
                <span className="text-[10px] text-faint">%</span>
              </div>

              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  aria-label="Diminuer la quantité"
                  onClick={() =>
                    onQuantity(
                      line.key,
                      Math.max(0, +(line.quantity - 1).toFixed(3)),
                    )
                  }
                  className="flex h-7 w-7 items-center justify-center rounded-chip border border-line bg-surface text-muted active:bg-subtle"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <input
                  type="number"
                  min={0}
                  step={line.sell_by_length ? "0.5" : "1"}
                  value={line.quantity}
                  onChange={(e) => onQuantity(line.key, Number(e.target.value))}
                  aria-label={`Quantité — ${line.name}`}
                  className="h-7 w-[46px] rounded-chip border border-line bg-surface px-1 text-center text-[11px] font-semibold tabular-nums text-ink"
                />
                <button
                  type="button"
                  aria-label="Augmenter la quantité"
                  onClick={() =>
                    onQuantity(line.key, +(line.quantity + 1).toFixed(3))
                  }
                  className="flex h-7 w-7 items-center justify-center rounded-chip border border-line bg-surface text-muted active:bg-subtle"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  aria-label={`Retirer ${line.name} du ticket`}
                  onClick={() => onRemove(line.key)}
                  className="ml-0.5 flex h-7 w-7 items-center justify-center rounded-chip text-faint hover:bg-danger-soft hover:text-danger"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {line.sell_by_length && (
              <p className="mt-1 pl-[42px] text-[10px] text-faint">
                {formatNumber(line.quantity, 2)} m facturé
                {line.quantity > 1 ? "s" : ""}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
