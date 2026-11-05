/**
 * Tests du champ numérique (`src/components/ui/number-input.tsx`).
 *
 * Verrouille les deux règles de saisie francophones :
 * - les zéros de tête disparaissent à la frappe (« 01 » → « 1 ») ;
 * - le point du pavé numérique vaut la virgule décimale (« 0.1 » → « 0,1 »).
 */
import {
  formatNumericInput,
  parseNumericInput,
  sanitizeNumericInput,
} from "./number-input";

describe("sanitizeNumericInput", () => {
  it("supprime les zéros de tête", () => {
    expect(sanitizeNumericInput("01")).toBe("1");
    expect(sanitizeNumericInput("007")).toBe("7");
    expect(sanitizeNumericInput("00")).toBe("0");
  });

  it("conserve le zéro qui précède la virgule", () => {
    expect(sanitizeNumericInput("0,5")).toBe("0,5");
    expect(sanitizeNumericInput("00,5")).toBe("0,5");
    expect(sanitizeNumericInput("0.5")).toBe("0,5");
  });

  it("interprète le point du pavé numérique comme une virgule", () => {
    expect(sanitizeNumericInput("0.1")).toBe("0,1");
    expect(sanitizeNumericInput("12.75")).toBe("12,75");
    expect(sanitizeNumericInput("1.")).toBe("1,");
  });

  it("n'accepte qu'une seule virgule", () => {
    expect(sanitizeNumericInput("1,2,3")).toBe("1,23");
    expect(sanitizeNumericInput("1.2.3")).toBe("1,23");
  });

  it("écarte les caractères non numériques", () => {
    expect(sanitizeNumericInput("12abc")).toBe("12");
    expect(sanitizeNumericInput("abc")).toBe("");
    expect(sanitizeNumericInput("1 500")).toBe("1500");
  });

  it("ne garde le signe négatif qu'en tête", () => {
    expect(sanitizeNumericInput("-5")).toBe("-5");
    expect(sanitizeNumericInput("5-2")).toBe("52");
  });

  it("laisse une saisie vide inchangée", () => {
    expect(sanitizeNumericInput("")).toBe("");
  });
});

describe("parseNumericInput", () => {
  it("lit la virgule comme séparateur décimal", () => {
    expect(parseNumericInput("0,1")).toBe(0.1);
    expect(parseNumericInput("12,75")).toBe(12.75);
  });

  it("retombe sur 0 pour une saisie incomplète", () => {
    expect(parseNumericInput("")).toBe(0);
    expect(parseNumericInput("-")).toBe(0);
    expect(parseNumericInput("1,")).toBe(1);
  });
});

describe("formatNumericInput", () => {
  it("affiche la virgule décimale", () => {
    expect(formatNumericInput(0.5)).toBe("0,5");
    expect(formatNumericInput(1500)).toBe("1500");
  });

  it("rend une chaîne vide pour une valeur absente", () => {
    expect(formatNumericInput(null)).toBe("");
    expect(formatNumericInput(undefined)).toBe("");
    expect(formatNumericInput(Number.NaN)).toBe("");
  });
});
