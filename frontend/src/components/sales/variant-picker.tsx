/**
 * Sélecteur de variante de produit — pour les lignes de devis / commande.
 *
 * - Rendu conditionnel : le composant ne s'affiche que si le produit
 *   sélectionné possède au moins une variante active (sinon la ligne reste
 *   un simple produit, sans champ parasite).
 * - Le libellé (`name_suffix`) sert d'intitulé ; le prix éventuellement
 *   défini par la variante est appliqué par le parent via `onChange`.
 */
"use client";

import { useVariants } from "@/hooks/useCatalogue";
import type { ProductVariant } from "@/lib/types";

interface Props {
  /** Produit concerné (``null`` = aucune ligne produit → rien à afficher). */
  productId: number | null;
  /** Variante sélectionnée (``null`` = produit de base). */
  value: number | null;
  /** Appelé avec la variante choisie (ou ``null`` après retour au produit). */
  onChange: (variantId: number | null, variant: ProductVariant | null) => void;
  disabled?: boolean;
}

export function VariantPicker({
  productId,
  value,
  onChange,
  disabled = false,
}: Props) {
  const { data: variants = [], isLoading } = useVariants(productId ?? 0);

  const active = variants.filter((v) => v.is_active !== false);
  // Pas de produit, chargement en cours ou aucune variante → pas de champ.
  if (!productId || isLoading || active.length === 0) return null;

  return (
    <select
      aria-label="Variante du produit"
      disabled={disabled}
      className="mt-1 h-7 w-full max-w-xs rounded-md border border-gray-300 bg-white px-2 text-xs text-gray-700 focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
      value={value ?? ""}
      onChange={(e) => {
        const raw = e.target.value;
        const id = raw ? Number(raw) : null;
        onChange(id, active.find((v) => v.id === id) ?? null);
      }}
    >
      <option value="">Variante : aucune (produit de base)</option>
      {active.map((v) => (
        <option key={v.id} value={v.id}>
          {v.name_suffix}
          {v.reference ? ` (${v.reference})` : ""}
        </option>
      ))}
    </select>
  );
}
