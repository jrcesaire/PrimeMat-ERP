/**
 * Référentiels de plan comptable — SYSCOHADA commercial et SYCEBNL.
 *
 * Les deux plans relèvent du même acte uniforme OHADA et partagent
 * l'arborescence des classes 1 à 9, mais diffèrent sur les comptes de capitaux
 * et sur la finalité :
 *
 * - **SYSCOHADA** — plan commercial (sociétés, entreprises individuelles) ;
 * - **SYCEBNL** — Système Comptable des Entités à But Non Lucratif
 *   (associations, ONG, fondations, projets).
 *
 * Le référentiel se choisit à l'initialisation (assistant de configuration)
 * puis reste modifiable dans les paramètres comptables, tant que la
 * comptabilité est vierge — un changement remplace tout le plan.
 */

export type ChartOfAccounts = "SYSCOHADA" | "SYCEBNL";

export interface ChartOption {
  value: ChartOfAccounts;
  /** Nom court, utilisé dans les listes et les badges. */
  label: string;
  /** Phrase d'identification affichée sous le nom. */
  summary: string;
  /** Comptes emblématiques du référentiel, montrés en exemple. */
  highlights: readonly string[];
}

export const CHART_OPTIONS: readonly ChartOption[] = [
  {
    value: "SYSCOHADA",
    label: "SYSCOHADA",
    summary: "Plan commercial — sociétés, entreprises individuelles",
    highlights: ["10 Capital social", "70 Ventes", "60 Achats"],
  },
  {
    value: "SYCEBNL",
    label: "SYCEBNL",
    summary: "Entités à but non lucratif — associations, ONG, projets",
    highlights: ["100 Dotation", "700 Revenus", "103 Droit d'entrée"],
  },
];

/** Référentiel appliqué par défaut, comme côté serveur. */
export const DEFAULT_CHART: ChartOfAccounts = "SYSCOHADA";

/** Référentiel correspondant à une valeur reçue de l'API, si elle est connue. */
export function chartOption(value?: string | null): ChartOption | undefined {
  return CHART_OPTIONS.find((option) => option.value === value);
}

/** Nom court d'un référentiel — repli sur le plan commercial si inconnu. */
export function chartLabel(value?: string | null): string {
  return chartOption(value)?.label ?? DEFAULT_CHART;
}

/** Vrai si la valeur désigne un référentiel géré par l'application. */
export function isChartOfAccounts(value?: string | null): value is ChartOfAccounts {
  return CHART_OPTIONS.some((option) => option.value === value);
}
