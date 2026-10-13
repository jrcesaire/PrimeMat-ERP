/**
 * Éditeurs de ligne de devis — coupes BAC multi-longueurs et pièce standard.
 */
"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency, formatNumber } from "@/lib/utils";
import type { Product } from "@/lib/types";

export interface CutState {
  key: number;
  quantity: number;
  length: number;
}

export interface LineState {
  key: number;
  product_id: number | null;
  /** Variante du produit (aucune = produit de base). */
  variant_id: number | null;
  /** Libellé de variante (instantané) — affichage en édition. */
  variant_name: string | null;
  description: string;
  sell_by_length: boolean;
  standard_piece: boolean;
  quantity: number;
  unit_price: number;
  discount_percent: number;
  cuts: CutState[];
}

interface CutsEditorProps {
  line: LineState;
  onLineChange: (patch: Partial<LineState>) => void;
}

/** Éditeur des sous-lignes « quantité de pièces × longueur » (tôles BAC / au ml). */
export function CutsEditor({ line, onLineChange }: CutsEditorProps) {
  const price = Number(line.unit_price) || 0;

  const updateCut = (cutKey: number, patch: Partial<CutState>) =>
    onLineChange({
      cuts: line.cuts.map((c) => (c.key === cutKey ? { ...c, ...patch } : c)),
    });

  const removeCut = (cutKey: number) =>
    onLineChange({ cuts: line.cuts.filter((c) => c.key !== cutKey) });

  const addCut = () =>
    onLineChange({ cuts: [...line.cuts, { key: Date.now(), quantity: 1, length: 0 }] });

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-gray-500">
            <th className="pb-1">Qté pièces</th>
            <th className="pb-1">Longueur (m)</th>
            <th className="pb-1 text-right">Total partiel</th>
            <th className="pb-1"></th>
          </tr>
        </thead>
        <tbody>
          {line.cuts.map((cut) => (
            <tr key={cut.key}>
              <td className="py-1 pr-2">
                <Input
                  type="number"
                  min={1}
                  className="h-8 w-24"
                  value={cut.quantity}
                  onChange={(e) => updateCut(cut.key, { quantity: Number(e.target.value) })}
                />
              </td>
              <td className="py-1 pr-2">
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  className="h-8 w-28"
                  value={cut.length}
                  onChange={(e) => updateCut(cut.key, { length: Number(e.target.value) })}
                />
              </td>
              <td className="py-1 text-right text-gray-700">
                {formatCurrency(
                  (Number(cut.quantity) || 0) * (Number(cut.length) || 0) * price,
                )}
              </td>
              <td className="py-1 text-right">
                <button
                  onClick={() => removeCut(cut.key)}
                  className="text-gray-400 hover:text-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button
        size="sm"
        variant="outline"
        className="mt-2 flex items-center gap-1"
        onClick={addCut}
      >
        <Plus className="h-3.5 w-3.5" />
        Ajouter une longueur
      </Button>
    </div>
  );
}

interface StandardPieceEditorProps {
  line: LineState;
  product: Product | null;
  totalLength: number;
  subtotal: number;
  onLineChange: (patch: Partial<LineState>) => void;
}

/** Vente à la pièce standard (mode dual) — facturée au prorata du ml. */
export function StandardPieceEditor({
  line,
  product,
  totalLength,
  subtotal,
  onLineChange,
}: StandardPieceEditorProps) {
  return (
    <div className="flex items-end gap-3">
      <div className="w-40">
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Nombre de pièces
        </label>
        <Input
          type="number"
          min={1}
          value={line.quantity}
          onChange={(e) => onLineChange({ quantity: Number(e.target.value) })}
        />
      </div>
      <p className="pb-2.5 text-xs text-gray-500">
        {formatNumber(line.quantity)} × {formatNumber(product?.unit_length ?? 0, 2)} m ={" "}
        <strong>{formatNumber(totalLength, 2)} m</strong> → {formatCurrency(subtotal)}
      </p>
    </div>
  );
}