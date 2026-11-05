/**
 * Tests du panier de la caisse (`src/lib/pos-cart.ts`).
 *
 * Verrouille la règle « un produit = une seule ligne de ticket » : un clic
 * répété sur une tuile doit incrémenter la quantité, y compris pour les
 * articles vendus au mètre (régression corrigée : ils empilaient des lignes
 * identiques).
 */
import { addProductToCart, type PosCartLine, type PosCartProduct } from "./pos-cart";

const unitProduct: PosCartProduct = {
  id: 1,
  name: "Ciment CPJ 50kg",
  reference: "CIM-001",
  selling_price: 4500,
};

const lengthProduct: PosCartProduct = {
  id: 2,
  name: "Tôle emboss selflock",
  reference: "PRD-79BC2AEC",
  sell_by_length: true,
  price_per_meter: 1800,
};

describe("addProductToCart", () => {
  it("crée une ligne pour un produit absent du ticket", () => {
    const { lines, selectedKey } = addProductToCart([], unitProduct, 1);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatchObject({
      key: 1,
      product_id: 1,
      name: "Ciment CPJ 50kg",
      quantity: 1,
      unit_price: 4500,
      sell_by_length: false,
    });
    expect(selectedKey).toBe(1);
  });

  it("incrémente la quantité au lieu d'empiler des lignes identiques", () => {
    let cart = addProductToCart([], unitProduct, 1);
    cart = addProductToCart(cart.lines, unitProduct, 2);
    cart = addProductToCart(cart.lines, unitProduct, 3);

    expect(cart.lines).toHaveLength(1);
    expect(cart.lines[0].quantity).toBe(3);
    // La ligne existante est resélectionnée, pas la nouvelle clé.
    expect(cart.selectedKey).toBe(1);
  });

  it("applique la même règle aux articles vendus au mètre", () => {
    let cart = addProductToCart([], lengthProduct, 1);
    cart = addProductToCart(cart.lines, lengthProduct, 2);

    expect(cart.lines).toHaveLength(1);
    expect(cart.lines[0].quantity).toBe(2);
    expect(cart.lines[0].unit_price).toBe(1800);
    expect(cart.lines[0].sell_by_length).toBe(true);
  });

  it("conserve une ligne par produit distinct", () => {
    let cart = addProductToCart([], unitProduct, 1);
    cart = addProductToCart(cart.lines, lengthProduct, 2);
    cart = addProductToCart(cart.lines, unitProduct, 3);

    expect(cart.lines).toHaveLength(2);
    expect(cart.lines.map((line) => line.quantity)).toEqual([2, 1]);
  });

  it("ne mute pas le tableau d'entrée", () => {
    const initial: PosCartLine[] = [];
    addProductToCart(initial, unitProduct, 1);
    expect(initial).toHaveLength(0);
  });

  it("retombe sur 0 quand le prix n'est pas renseigné", () => {
    const { lines } = addProductToCart([], { id: 9, name: "Sans prix" }, 1);
    expect(lines[0].unit_price).toBe(0);
    expect(lines[0].reference).toBeNull();
  });
});
