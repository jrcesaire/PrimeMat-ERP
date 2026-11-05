/**
 * Champ numérique « à la française ».
 *
 * Remplace `<input type="number">` dans les modules de gestion commerciale et
 * financière (quantités, prix, remises, paiements, montants comptables).
 *
 * Deux règles de saisie, alignées sur l'usage francophone :
 * 1. **Zéros de tête supprimés à la volée** — taper « 0 » puis « 1 » donne
 *    « 1 » et non « 01 » ;
 * 2. **Le point vaut la virgule** — sur le pavé numérique, `.` est la marque
 *    décimale : « 0.1 » s'affiche et se lit « 0,1 ».
 *
 * Les fonctions de nettoyage et de conversion sont pures et exportées : elles
 * sont couvertes par des tests unitaires.
 */
"use client";

import { forwardRef, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Nettoie une saisie en cours de frappe.
 *
 * - convertit le point décimal en virgule ;
 * - ne conserve que les chiffres, une seule virgule et un signe négatif en
 *   tête ;
 * - supprime les zéros de tête, **sans toucher au « 0 » qui précède la
 *   virgule** (« 0,5 » reste « 0,5 »).
 */
export function sanitizeNumericInput(raw: string): string {
  // Le point du pavé numérique est la marque décimale → virgule.
  let value = raw.replace(/\./g, ",");
  // Ne garder que chiffres, virgule et signe.
  value = value.replace(/[^0-9,-]/g, "");
  // Une seule virgule : les suivantes sont ignorées.
  const firstComma = value.indexOf(",");
  if (firstComma >= 0) {
    value =
      value.slice(0, firstComma + 1) + value.slice(firstComma + 1).replace(/,/g, "");
  }
  // Le signe négatif ne peut être qu'en tête.
  const negative = value.startsWith("-");
  value = (negative ? "-" : "") + value.replace(/-/g, "");
  // Zéros de tête : « 01 » → « 1 », « 007 » → « 7 », mais « 0,5 » inchangé.
  value = value.replace(/^(-?)0+(?=\d)/, "$1");
  return value;
}

/** Convertit une saisie nettoyée en nombre (0 si la saisie est incomplète). */
export function parseNumericInput(raw: string): number {
  const normalized = raw.replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** Prépare une valeur numérique pour l'affichage (virgule décimale). */
export function formatNumericInput(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return String(value).replace(".", ",");
}

export type NumberInputProps = Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "type"
> & {
  /** Valeur courante — une chaîne est acceptée (états historiques). */
  value: number | string | null | undefined;
  /**
   * Reçoit la valeur numérique **et** la saisie nettoyée telle qu'affichée.
   * Le second paramètre permet aux formulaires dont l'état est une chaîne de
   * distinguer un champ vide (chaîne vide) d'un zéro saisi.
   */
  onChange: (value: number, raw: string) => void;
};

export const NumberInput = forwardRef<HTMLInputElement, NumberInputProps>(
  ({ value, onChange, className, onFocus, onBlur, ...props }, ref) => {
    // Tant que le champ a le focus, on affiche exactement ce que l'utilisateur
    // a tapé (« 1, » doit rester « 1, » le temps de finir la décimale).
    const [draft, setDraft] = useState<string | null>(null);
    const numeric =
      typeof value === "string"
        ? value.trim() === ""
          ? null
          : parseNumericInput(value)
        : value;
    const shown = draft ?? formatNumericInput(numeric);

    return (
      <input
        {...props}
        ref={ref}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        value={shown}
        onChange={(event) => {
          const next = sanitizeNumericInput(event.target.value);
          setDraft(next);
          onChange(parseNumericInput(next), next);
        }}
        onFocus={(event) => {
          setDraft(formatNumericInput(numeric));
          onFocus?.(event);
        }}
        onBlur={(event) => {
          setDraft(null);
          onBlur?.(event);
        }}
        className={cn(
          "flex h-10 w-full rounded-control border border-line bg-surface px-3 py-2 text-[13px] text-ink placeholder:text-ghost focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
      />
    );
  },
);
NumberInput.displayName = "NumberInput";
