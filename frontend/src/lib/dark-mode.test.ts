/**
 * Garde-fou du mode sombre.
 *
 * Le thème repose sur une convention : les couleurs codées en dur du code
 * historique sont rattrapées par le bloc « repli » de `globals.css`. Deux
 * régressions silencieuses sont possibles, et ce test les empêche :
 *
 * 1. `darkMode: "class"` disparaît de `tailwind.config.js` — Tailwind compile
 *    alors ses variantes `dark:` en `@media (prefers-color-scheme: dark)` : les
 *    modales suivent le système d'exploitation au lieu du bouton de
 *    l'application, d'où un champ de saisie sombre dans une fenêtre claire ;
 * 2. une famille de fond pastel (`bg-green-50`…) perd sa contrepartie sombre —
 *    le texte, lui, reste éclairci : clair sur clair, soit 1,1:1, invisible.
 *
 * Le test lit les fichiers de source : il ne rend rien, il vérifie le contrat.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

const frontend = join(__dirname, "..", "..");
const read = (relative: string) => readFileSync(join(frontend, relative), "utf8");

const config = read("tailwind.config.js");
const css = read("src/app/globals.css");

/** Familles de fond pastel effectivement utilisées par l'interface. */
const FAMILLES_PASTEL = [
  "red-50",
  "red-100",
  "rose-50",
  "pink-100",
  "green-50",
  "green-100",
  "emerald-50",
  "emerald-100",
  "teal-50",
  "lime-100",
  "cyan-50",
  "amber-50",
  "amber-100",
  "yellow-50",
  "orange-100",
  "blue-50",
  "blue-100",
  "sky-100",
  "indigo-50",
  "violet-100",
  "purple-50",
];

describe("mode sombre", () => {
  it("est piloté par la classe `dark`, pas par la préférence système", () => {
    expect(config).toMatch(/darkMode:\s*["']class["']/);
    expect(css).not.toContain("prefers-color-scheme");
  });

  it("assombrit chaque famille de fond pastel de l'interface", () => {
    for (const famille of FAMILLES_PASTEL) {
      expect(css).toContain(`.dark .bg-${famille}`);
    }
  });

  it("éclaircit les couleurs de texte qui accompagnent ces fonds", () => {
    const textes = [
      "red-600",
      "red-700",
      "rose-700",
      "green-600",
      "green-700",
      "green-800",
      "emerald-700",
      "amber-700",
      "amber-800",
      "orange-700",
      "blue-600",
      "blue-700",
      "indigo-700",
      "purple-800",
    ];
    for (const texte of textes) {
      expect(css).toContain(`.dark .text-${texte}`);
    }
  });

  it("couvre les séparateurs, bordures et placeholders du code historique", () => {
    expect(css).toContain(".dark .divide-gray-200 > :not([hidden])");
    expect(css).toContain(".dark .border-gray-400");
    expect(css).toContain(".dark .placeholder\\:text-gray-400::placeholder");
    expect(css).toContain(".dark .bg-gray-100");
  });

  it("laisse le panneau du sélecteur de produit en foncé sur fond clair", () => {
    expect(css).toContain(".picker-panel .hover\\:text-red-600:hover");
  });
});
