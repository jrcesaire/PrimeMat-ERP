/**
 * Hooks pour la nomenclature des documents (Paramètres → Documents).
 *
 * Config stockée dans le paramètre JSON `doc_nomenclature` :
 *   { quote: { prefix, padding, reset, suffix_type, suffix_custom }, ... }
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export interface DocNomenclature {
  prefix: string;
  padding: number;
  reset: "never" | "month" | "quarter" | "semester" | "year";
  suffix_type: "none" | "mmaa" | "aaaa" | "custom";
  suffix_custom: string;
}

export type NomenclatureMap = Record<string, DocNomenclature>;

export const NOMENCLATURE_KEY = ["settings", "doc_nomenclature"];

export const DOC_MODELS: { key: string; label: string }[] = [
  { key: "quote", label: "Devis" },
  { key: "order", label: "Commandes" },
  { key: "invoice", label: "Factures" },
  { key: "delivery", label: "Bons de livraison" },
  { key: "payment", label: "Reçus / Paiements" },
  { key: "expense", label: "Dépenses" },
  { key: "employee", label: "Matricules employés" },
  { key: "payroll_contract", label: "Contrats de travail" },
  { key: "payslip", label: "Bulletins de paie" },
  { key: "payroll_run", label: "Lots de paie" },
  { key: "journal", label: "Écritures comptables" },
  { key: "product", label: "Références produits" },
];

/** Libellé d'un type de séquence (repli : le code du modèle). */
export const DOC_MODEL_LABELS: Record<string, string> = Object.fromEntries(
  DOC_MODELS.map((m) => [m.key, m.label]),
);

/**
 * Module backend dont dépend chaque séquence : une séquence rattachée à un
 * module **désactivé** n'est pas listée dans Paramètres → Séquences.
 */
export const MODEL_MODULE: Record<string, string> = {
  quote: "sales",
  order: "sales",
  invoice: "invoicing",
  delivery: "delivery",
  payment: "payments",
  expense: "finance",
  journal: "accounting",
  product: "catalogue",
  employee: "payroll",
  payroll_contract: "payroll",
  payslip: "payroll",
  payroll_run: "payroll",
};

/** Séquence **en vigueur** : règle appliquée + état du compteur. */
export interface SequenceEntry {
  model: string;
  prefix: string;
  padding: number;
  reset: DocNomenclature["reset"];
  suffix_type: DocNomenclature["suffix_type"];
  suffix_custom: string;
  /** Vrai dès qu'un numéro a été émis (compteur existant). */
  in_use: boolean;
  last_number: number;
  /** Prochaine référence (aperçu, sans consommer le compteur). */
  next_reference: string;
}

export const SEQUENCES_KEY = ["settings", "sequences"];

export function useSequences() {
  return useQuery({
    queryKey: SEQUENCES_KEY,
    queryFn: async (): Promise<SequenceEntry[]> => {
      const res = await apiClient.get("/core/settings/sequences");
      return (res.data?.sequences ?? []) as SequenceEntry[];
    },
  });
}

export const DEFAULT_NOMENCLATURE: DocNomenclature = {
  prefix: "",
  padding: 6,
  reset: "year",
  suffix_type: "none",
  suffix_custom: "",
};

/**
 * Convertit la valeur brute du paramètre en nomenclature exploitable.
 *
 * Les anciennes versions enregistraient parfois une chaîne JSON doublement
 * encodée. Une valeur corrompue par un spread de chaîne produit quant à elle
 * un objet dont les clés sont des positions (`0`, `1`, …) : il ne faut surtout
 * pas l'exposer à l'interface, qui tenterait sinon de rendre des millions de
 * lignes. Dans ces cas, les valeurs par défaut du backend reprennent la main.
 */
export function asNomenclatureMap(value: unknown): NomenclatureMap {
  let data: unknown = value;
  for (let i = 0; i < 3 && typeof data === "string"; i += 1) {
    try {
      data = JSON.parse(data);
    } catch {
      return {};
    }
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  const entries = Object.entries(data as Record<string, unknown>);
  if (entries.length > 0 && entries.every(([key]) => /^\d+$/.test(key))) {
    return {};
  }
  return data as NomenclatureMap;
}

export function useNomenclature() {
  return useQuery({
    queryKey: NOMENCLATURE_KEY,
    queryFn: async (): Promise<NomenclatureMap> => {
      const res = await apiClient.get("/core/settings/doc_nomenclature");
      return asNomenclatureMap(res.data?.value);
    },
  });
}

export function useSaveNomenclature() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config: NomenclatureMap) => {
      await apiClient.post("/core/settings/", {
        key: "doc_nomenclature",
        // Le service sérialise une seule fois les paramètres de type « json ».
        value: config,
        type: "json",
        is_public: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOMENCLATURE_KEY });
      queryClient.invalidateQueries({ queryKey: SEQUENCES_KEY });
    },
  });
}

/** Aperçu local de la référence (sans toucher au compteur backend). */
export function previewReference(cfg: DocNomenclature): string {
  const now = new Date();
  const pad = Math.min(8, Math.max(3, cfg.padding || 6));
  const serial = "0".repeat(pad);
  let suffix = "";
  if (cfg.suffix_type === "mmaa") {
    suffix = `${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getFullYear()).slice(-2)}`;
  } else if (cfg.suffix_type === "aaaa") {
    suffix = String(now.getFullYear());
  } else if (cfg.suffix_type === "custom") {
    suffix = (cfg.suffix_custom || "").trim();
  }
  const prefix = (cfg.prefix || "").trim().replace(/^-+|-+$/g, "");
  const body = prefix ? `${prefix}-${serial}` : serial;
  return suffix ? `${body}-${suffix}` : body;
}
