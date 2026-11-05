/**
 * Tests des utilitaires partagés (`src/lib/utils.tsx`).
 *
 * Les séparateurs de milliers produits par `Intl` varient selon la version
 * d'ICU embarquée (espace fine insécable U+202F, insécable U+00A0 ou simple) :
 * `normalizeSpaces` les ramène à un espace ordinaire pour rendre les
 * assertions déterministes.
 */
import {
  cn,
  formatCurrency,
  formatDate,
  formatNumber,
  lastRouteSegment,
  STATUS_LABELS,
} from "./utils";

/** Remplace tous les espaces spéciaux par un espace ordinaire. */
function normalizeSpaces(value: string): string {
  return value.replace(/[\u00a0\u202f\u2009]/g, " ");
}

describe("cn", () => {
  it("concatène les classes", () => {
    expect(cn("flex", "gap-2")).toBe("flex gap-2");
  });

  it("ignore les valeurs falsy", () => {
    expect(cn("flex", false && "hidden", undefined, null, "gap-2")).toBe(
      "flex gap-2",
    );
  });

  it("arbitre les classes Tailwind en conflit (dernier gagnant)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-sm", "text-lg")).toBe("text-lg");
  });
});

describe("formatCurrency", () => {
  it("formate un montant avec la devise par défaut", () => {
    expect(normalizeSpaces(formatCurrency(1_200_000))).toBe("1 200 000 FCFA");
  });

  it("accepte une devise explicite", () => {
    expect(normalizeSpaces(formatCurrency(1500, "XOF"))).toBe("1 500 XOF");
  });

  it("traite null / undefined comme 0", () => {
    expect(normalizeSpaces(formatCurrency(null))).toBe("0 FCFA");
    expect(normalizeSpaces(formatCurrency(undefined))).toBe("0 FCFA");
  });

  it("accepte une chaîne numérique", () => {
    expect(normalizeSpaces(formatCurrency("2500"))).toBe("2 500 FCFA");
  });
});

describe("formatNumber", () => {
  it("formate sans décimale par défaut", () => {
    expect(normalizeSpaces(formatNumber(12_345.678))).toBe("12 346");
  });

  it("respecte le nombre de décimales demandé", () => {
    expect(normalizeSpaces(formatNumber(12.3456, 2))).toBe("12,35");
  });
});

describe("formatDate", () => {
  it("retourne un tiret pour une valeur absente", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
    expect(formatDate("")).toBe("—");
  });

  it("retourne la valeur brute si la date est invalide", () => {
    expect(formatDate("pas-une-date")).toBe("pas-une-date");
  });

  it("formate une date ISO en JJ/MM/AAAA", () => {
    expect(formatDate("2026-05-12T10:30:00Z")).toMatch(/^\d{2}\/\d{2}\/\d{4}$/);
  });
});

describe("lastRouteSegment", () => {
  it("retourne le dernier segment d'une route de module", () => {
    expect(lastRouteSegment("/dashboard/sales/orders")).toBe("orders");
    expect(lastRouteSegment("/dashboard/purchases/demandes")).toBe("demandes");
  });

  it("ignore les barres obliques finales", () => {
    expect(lastRouteSegment("/dashboard/sales/orders/")).toBe("orders");
    expect(lastRouteSegment("/dashboard/treasury//")).toBe("treasury");
  });

  it("gère les valeurs vides", () => {
    expect(lastRouteSegment(null)).toBe("");
    expect(lastRouteSegment(undefined)).toBe("");
    expect(lastRouteSegment("")).toBe("");
    expect(lastRouteSegment("/")).toBe("");
  });
});

describe("STATUS_LABELS", () => {
  it("fournit un libellé et un style pour les statuts clés", () => {
    for (const status of ["draft", "posted", "paid", "cancelled", "validated"]) {
      const config = STATUS_LABELS[status];
      expect(config).toBeDefined();
      expect(config.label.length).toBeGreaterThan(0);
      expect(config.className).toContain("bg-");
    }
  });

  it("couvre les statuts du cycle de vie d'une déclaration de TVA", () => {
    expect(STATUS_LABELS.draft.label).toBe("Brouillon");
    expect(STATUS_LABELS.paid.label).toBe("Payée");
  });
});
