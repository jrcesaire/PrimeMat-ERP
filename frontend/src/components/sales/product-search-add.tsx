/**
 * Recherche produit par nom pour le Point de vente.
 *
 * - Dès la 1ʳᵉ lettre tapée : suggestions depuis la base produits
 *   (nom ou référence) → clic ou Entrée = ajout au panier
 * - Produit inexistant → « Ajout rapide » (dialog minimal : nom prérempli
 *   + prix de vente, catégorie facultative) puis le produit créé est
 *   ajouté automatiquement au panier, sans interrompre la vente.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { PackagePlus } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import type { Product } from "@/lib/types";
import { QuickProductDialog } from "./quick-product-dialog";

interface Props {
  onAdd: (product: Product) => void;
  /** Filtre les suggestions par catégorie (null = Tout). */
  categoryId?: number | null;
}

export function ProductSearchAdd({ onAdd, categoryId }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [quickOpen, setQuickOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setOpen(false);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ limit: String(8) });
        if (categoryId) params.set("category_id", String(categoryId));
        if (q) params.set("search", q);
        const res = await apiClient.get(`/catalogue/products?${params.toString()}`);
        setResults(res.data ?? []);
        setHighlight(0);
        setOpen(true);
      } catch {
        setResults([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const add = (p: Product) => {
    onAdd(p);
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[highlight]) add(results[highlight]);
    }
  };

  return (
    <div ref={boxRef} className="relative">
      <Input
        autoFocus
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (query.trim()) setOpen(true);
        }}
        onKeyDown={onKeyDown}
        placeholder="Tapez le nom du produit (ex. ciment, fer à béton…)"
      />
      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
          {results.length === 0 && (
            <p className="px-3 py-2 text-sm text-gray-500">Aucun produit trouvé.</p>
          )}
          {results.map((p, i) => (
            <button
              key={p.id}
              type="button"
              onClick={() => add(p)}
              onMouseEnter={() => setHighlight(i)}
              className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm ${
                i === highlight ? "bg-blue-50" : "hover:bg-gray-50"
              }`}
            >
              <span className="font-medium text-gray-800">
                {p.name}
                <span className="ml-2 text-xs text-gray-400">{p.reference}</span>
              </span>
              <span className="text-xs text-gray-500">
                {p.sell_by_length
                  ? `${formatCurrency(p.price_per_meter ?? 0)}/ml`
                  : formatCurrency(p.selling_price ?? 0)}
              </span>
            </button>
          ))}
          <div className="border-t border-gray-100 p-2">
            <Button
              size="sm"
              className="flex w-full items-center gap-2"
              onClick={() => setQuickOpen(true)}
            >
              <PackagePlus className="h-4 w-4" />
              Produit introuvable ? Ajout rapide « {query.trim()} »
            </Button>
          </div>
        </div>
      )}
      {quickOpen && (
        <QuickProductDialog
          initialName={query.trim()}
          onClose={() => setQuickOpen(false)}
          onCreated={(p) => {
            setQuickOpen(false);
            add(p);
          }}
        />
      )}
    </div>
  );
}