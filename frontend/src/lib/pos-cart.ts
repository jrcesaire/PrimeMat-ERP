/**
 * Panier de la caisse — fonctions pures, testables isolément.
 *
 * Extraites de l'écran de vente pour que la règle métier « un produit = une
 * seule ligne de ticket » soit vérifiable par des tests unitaires, sans monter
 * tout le composant.
 */

/** Ligne du ticket de caisse. */
export interface PosCartLine {
  key: number;
  product_id: number;
  name: string;
  reference?: string | null;
  variant_name?: string | null;
  sell_by_length: boolean;
  /** Pièces ou mètres selon le produit. */
  quantity: number;
  unit_price: number;
  /** Remise par ligne (%). */
  discount_percent: number;
  category_id?: number | null;
}

/** Produit tel que le fournissent la grille tactile et la recherche. */
export interface PosCartProduct {
  id: number;
  name: string;
  reference?: string | null;
  category_id?: number | null;
  sell_by_length?: boolean;
  price_per_meter?: number | null;
  selling_price?: number | null;
}

/**
 * Ajoute un produit au ticket.
 *
 * **Un même produit ne doit jamais apparaître sur deux lignes** : s'il est déjà
 * présent, la quantité de sa ligne est incrémentée de 1. La règle vaut
 * également pour les articles vendus au mètre (quantité exprimée en mètres) —
 * c'est ce qui garantit qu'un clic répété « monte » la quantité au lieu
 * d'empiler des lignes identiques.
 *
 * Fonction pure : `lines` n'est jamais muté.
 */
export function addProductToCart(
  lines: PosCartLine[],
  product: PosCartProduct,
  nextKey: number,
): { lines: PosCartLine[]; selectedKey: number } {
  const existing = lines.find((line) => line.product_id === product.id);

  if (existing) {
    return {
      lines: lines.map((line) =>
        line.product_id === product.id
          ? { ...line, quantity: line.quantity + 1 }
          : line,
      ),
      selectedKey: existing.key,
    };
  }

  const sellByLength = Boolean(product.sell_by_length);
  return {
    lines: [
      ...lines,
      {
        key: nextKey,
        product_id: product.id,
        name: product.name,
        reference: product.reference ?? null,
        sell_by_length: sellByLength,
        quantity: 1,
        // Au mètre, le prix unitaire est le prix au mètre linéaire.
        unit_price: sellByLength
          ? (product.price_per_meter ?? 0)
          : (product.selling_price ?? 0),
        discount_percent: 0,
        category_id: product.category_id ?? null,
      },
    ],
    selectedKey: nextKey,
  };
}
