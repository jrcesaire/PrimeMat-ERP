/**
 * Sélecteur de produit avec recherche — pour les lignes de devis / commande.
 *
 * - Affiche le produit choisi (nom + référence) ou un libellé d'invite.
 * - À l'ouverture : liste initiale issue des produits déjà chargés,
 *   puis recherche serveur par nom ou référence (débounce 250 ms).
 * - Navigation clavier (↑ / ↓ / Entrée / Échap) et fermeture au clic extérieur.
 * - Option « Ajout rapide » si le produit est introuvable.
 * - Le panneau est rendu dans un portail `document.body` en `position: fixed` :
 *   dans une cellule de tableau, un menu `absolute` est rogné par le Card en
 *   `overflow-hidden`, et les overrides `.dark .bg-white` (en `!important`)
 *   le rendent illisible. Le portail sort des deux contraintes.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronUp, PackagePlus, X } from "lucide-react";
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

/** Hauteur maximale du panneau du menu déroulant. */
const PANEL_MAX_H = 320;
/** Marge conservée entre le panneau et les bords de la fenêtre. */
const EDGE_GAP = 8;
/** En deçà de cette hauteur disponible, le panneau se retourne au-dessus. */
const FLIP_THRESHOLD = 220;
/** Largeur minimale du panneau (le texte long doit rester lisible). */
const PANEL_MIN_W = 320;

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
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const selected =
    products.find((p) => p.id === value) ??
    (created && created.id === value ? created : null);

  /**
   * Recalcule la position du panneau à partir du rectangle du déclencheur.
   * Largeur : au moins celle de la cellule, 320 px au minimum, bornée à la
   * fenêtre. Hauteur : contenu, plafonnée, et basculée au-dessus du
   * déclencheur s'il n'y a pas la place en dessous.
   */
  /**
   * Recalcule la position du panneau depuis le rectangle du déclencheur.
   * Largeur : au moins celle de la cellule et 320 px, bornée par la fenêtre.
   * Hauteur : plafonnée à la place disponible, et bascule au-dessus du
   * déclencheur s'il n'y a pas assez d'espace en dessous.
   */
  const updatePosition = useCallback(() => {
    const el = boxRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const panelW = Math.max(PANEL_MIN_W, r.width);
    const left = Math.max(EDGE_GAP, Math.min(r.left, vw - panelW - EDGE_GAP));
    const below = vh - r.bottom - EDGE_GAP;
    const above = r.top - EDGE_GAP;
    const flip = below < FLIP_THRESHOLD && above > below;
    const available = flip ? above : below;
    const maxHeight = Math.max(160, Math.min(PANEL_MAX_H, available));
    const top = flip
      ? Math.max(EDGE_GAP, r.top - maxHeight - 4)
      : Math.min(r.bottom + 4, vh - EDGE_GAP);
    setPos({ top, left });
    const panel = panelRef.current;
    if (panel) {
      panel.style.maxHeight = `${maxHeight}px`;
      panel.style.width = `${panelW}px`;
    }
  }, []);

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

  // Position initiale + recalcul au défilement / au redimensionnement.
  useEffect(() => {
    if (!open) return;
    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [open, updatePosition, results.length]);

  // Focus le champ de saisie quand le panneau s'ouvre — indispensable dans
  // un Dialog (Radix piège le focus, `autoFocus` seul n'est pas fiable).
  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
  }, [open]);

  // Fermeture au clic extérieur. Le panneau étant dans un portail, il vit
  // hors de `boxRef` : les deux conteneurs doivent être testés, sinon un clic
  // sur une suggestion fermerait la liste avant que son onClick ne s'exécute.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const t = e.target as Node;
      if (
        boxRef.current?.contains(t) ||
        panelRef.current?.contains(t)
      ) {
        return;
      }
      setOpen(false);
      setQuery("");
      setPos(null);
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
    <div ref={boxRef} className="relative w-full">
      {open ? (
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Rechercher un produit (nom ou référence)…"
        />
      ) : (
        <button
          type="button"
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            setOpen(true);
          }}
          className="flex h-8 w-full items-center gap-2 rounded-md border border-gray-300 bg-white px-2 text-left text-sm hover:border-primary focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
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
        </button>
      )}
      {/* Chevron : bascule l'ouverture / fermeture du panneau. */}
      {open ? (
        <ChevronUp
          className="h-4 w-4 shrink-0 text-gray-400 cursor-pointer hover:text-gray-600"
          onClick={(e) => {
            e.stopPropagation();
            setOpen(false);
          }}
        />
      ) : (
        <ChevronDown
          className="h-4 w-4 shrink-0 text-gray-400 cursor-pointer hover:text-gray-600"
          onClick={(e) => {
            e.stopPropagation();
            setOpen(true);
          }}
        />
      )}

      {/* Panneau en portail : échappe au `overflow-hidden` du Card et aux
          overrides `.dark .bg-white`. Position `fixed` calculée depuis le
          rectangle du déclencheur, donc jamais contraint par la cellule. */}
      {open &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            ref={panelRef}
            style={{
              top: pos?.top ?? -9999,
              left: pos?.left ?? -9999,
              visibility: pos ? "visible" : "hidden",
            }}
            className="picker-panel fixed z-[9999] overflow-y-auto overscroll-contain rounded-md border shadow-lg"
          >
            {results.length === 0 && (
              <p className="picker-empty px-3 py-2 text-sm">
                Aucun produit trouvé.
              </p>
            )}
            {results.map((p, i) => (
              <button
                key={p.id}
                type="button"
                data-active={i === highlight}
                onClick={() => pick(p)}
                onMouseEnter={() => setHighlight(i)}
                className="picker-item flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{p.name}</span>
                  <span className="picker-ref text-xs">
                    {p.reference}
                    {saleModeSuffix(p)}
                  </span>
                </span>
                <span className="picker-price shrink-0 text-xs">
                  {priceLabel(p)}
                </span>
              </button>
            ))}
            {allowCreate && (
              <div className="picker-footer border-t p-2">
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
          </div>,
          document.body,
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