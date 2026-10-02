/**
 * Sélecteur de produit avec recherche — pour les lignes de devis / commande.
 *
 * - Affiche le produit choisi (nom + référence) ou un libellé d'invite.
 * - À l'ouverture : liste initiale issue des produits déjà chargés,
 *   puis recherche serveur par nom ou référence (débounce 250 ms).
 * - Navigation clavier (↑ / ↓ / Entrée / Échap) et fermeture au clic extérieur.
 * - Option « Ajout rapide » si le produit est introuvable.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, PackagePlus, X } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/lib/utils";
import type { Product } from "@/lib/types";
import { QuickProductDialog } from "./quick-product-dialog";

interface Props {
  /** Identifiant du produit sélectionné (``null`` = aucune sélection). */
  value: number | null;
  /** Liste déjà chargée (affichage instantané + résolution du libellé). */
  products: Product[];
  /** Appelé avec le produit choisi (ou ``null`` après effacement). */
  onChange: (productId: number | null, product: Product | null) => void;
  disabled?: boolean;
  /** Proposer la création rapide lorsque la recherche ne donne rien. */
  allowCreate?: boolean;
}

/** Suffixe de mode de vente affiché à côté du nom. */
function saleModeSuffix(p: Product): string {
  if (p.sale_mode === "length") return " · au mètre";
  if (p.sale_mode === "dual") return " · ml / pièce";
  return "";
}

/** Prix de vente affiché à droite de la suggestion. */
function priceLabel(p: Product): string {
  if (p.sale_mode === "length" || p.sale_mode === "dual") {
    const ml = Number(p.price_per_meter) || 0;
    if (ml > 0) return `${formatCurrency(ml)}/ml`;
  }
  return formatCurrency(Number(p.selling_price) || 0);
}

export function ProductPicker({
  value,
  products,
  onChange,
  disabled = false,
  allowCreate = true,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [highlight, setHighlight] = useState(0);
  const [quickOpen, setQuickOpen] = useState(false);
  const [created, setCreated] = useState<Product | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  const selected =
    products.find((p) => p.id === value) ??
    (created && created.id === value ? created : null);

  // Recherche serveur (débouncée) — liste initiale si aucune saisie.
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (!q) {
      setResults(products.slice(0, 8));
      setHighlight(0);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const res = await apiClient.get(
          `/catalogue/products?search=${encodeURIComponent(q)}&limit=8`,
        );
        setResults(res.data ?? []);
        setHighlight(0);
      } catch {
        setResults([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query, open, products]);

  // Fermeture au clic extérieur.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const pick = (p: Product) => {
    setCreated(p);
    onChange(p.id, p);
    setOpen(false);
    setQuery("");
  };

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCreated(null);
    onChange(null, null);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setOpen(false);
      setQuery("");
      return;
    }
    if (results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[highlight]) pick(results[highlight]);
    }
  };

  return (
    <div ref={boxRef} className="relative">
      {open ? (
        <Input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Rechercher un produit (nom ou référence)…"
        />
      ) : (
        <button
          type="button"
          disabled={disabled}
          onClick={() => setOpen(true)}
          className="flex h-8 w-full max-w-xs items-center gap-2 rounded-md border border-gray-300 bg-white px-2 text-left text-sm hover:border-primary focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
        >
          <span className="min-w-0 flex-1 truncate">
            {selected ? (
              <>
                <span className="text-gray-800">{selected.name}</span>
                <span className="ml-1.5 text-xs text-gray-400">
                  {selected.reference}
                </span>
              </>
            ) : (
              <span className="text-gray-400">— Choisir un produit —</span>
            )}
          </span>
          {selected && !disabled && (
            <span
              role="button"
              tabIndex={-1}
              title="Retirer le produit"
              onClick={clear}
              className="shrink-0 text-gray-400 hover:text-red-600"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          )}
          <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />
        </button>
      )}

      {open && (
        <div className="absolute z-30 mt-1 max-h-72 w-full min-w-72 overflow-auto rounded-md border border-gray-200 bg-white shadow-lg">
          {results.length === 0 && (
            <p className="px-3 py-2 text-sm text-gray-500">Aucun produit trouvé.</p>
          )}
          {results.map((p, i) => (
            <button
              key={p.id}
              type="button"
              onClick={() => pick(p)}
              onMouseEnter={() => setHighlight(i)}
              className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                i === highlight ? "bg-blue-50" : "hover:bg-gray-50"
              }`}
            >
              <span className="min-w-0">
                <span className="block truncate font-medium text-gray-800">
                  {p.name}
                </span>
                <span className="text-xs text-gray-400">
                  {p.reference}
                  {saleModeSuffix(p)}
                </span>
              </span>
              <span className="shrink-0 text-xs text-gray-500">{priceLabel(p)}</span>
            </button>
          ))}
          {allowCreate && (
            <div className="border-t border-gray-100 p-2">
              <Button
                size="sm"
                type="button"
                className="flex w-full items-center gap-2"
                onClick={() => setQuickOpen(true)}
              >
                <PackagePlus className="h-4 w-4" />
                {query.trim()
                  ? `Produit introuvable ? Ajout rapide « ${query.trim()} »`
                  : "Produit introuvable ? Ajout rapide"}
              </Button>
            </div>
          )}
        </div>
      )}

      {quickOpen && (
        <QuickProductDialog
          initialName={query.trim()}
          onClose={() => setQuickOpen(false)}
          onCreated={(p) => {
            setQuickOpen(false);
            pick(p);
          }}
        />
      )}
    </div>
  );
}