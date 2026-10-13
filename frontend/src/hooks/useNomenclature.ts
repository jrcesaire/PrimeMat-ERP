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
  { key: "journal", label: "Écritures comptables" },
];

export const DEFAULT_NOMENCLATURE: DocNomenclature = {
  prefix: "",
  padding: 6,
  reset: "year",
  suffix_type: "none",
  suffix_custom: "",
};

export function useNomenclature() {
  return useQuery({
    queryKey: NOMENCLATURE_KEY,
    queryFn: async (): Promise<NomenclatureMap> => {
      const res = await apiClient.get("/core/settings/doc_nomenclature");
      return (res.data?.value ?? {}) as NomenclatureMap;
    },
  });
}

export function useSaveNomenclature() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config: NomenclatureMap) => {
      await apiClient.post("/core/settings/", {
        key: "doc_nomenclature",
        value: JSON.stringify(config),
        type: "json",
        is_public: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOMENCLATURE_KEY });
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
