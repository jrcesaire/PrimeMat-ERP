/**
 * Hooks du module Comptabilité — régime fiscal (TEE / RME / RSI / RNI, Côte d'Ivoire).
 *
 * Fournit :
 * - useFiscalRegime    : lecture du régime actuel + alerte dépassement de seuil
 * - useUpdateFiscalRegime : mise à jour manuelle du régime (jamais automatique)
 * - useDetectCATreshold : détection de dépassement de CA (alerte uniquement)
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const FISCAL_REGIME_KEY = "accounting-fiscal-regime";

export interface TaxRegimeRead {
  company_id: number;
  tax_regime: string | null;
  suggested_tax_regime: string | null;
  ca_threshold: number | null;
  ca_exceeds_threshold: boolean;
  tva_blocked: boolean;
}

export interface TaxRegimeUpdate {
  tax_regime: string;
}

export interface RegimeInfo {
  code: string;
  label: string;
  description: string;
  ca_threshold: number | null;
  tva_blocked: boolean;
}

export const REGIMES: RegimeInfo[] = [
  {
    code: "TEE",
    label: "TEE — Taxe d'État de l'Entreprenant",
    description: "CA ≤ 50 000 000 FCFA — TVA bloquée (franchise)",
    ca_threshold: 50_000_000,
    tva_blocked: true,
  },
  {
    code: "RME",
    label: "RME — Régime de la Micro-Entreprise",
    description: "50 M < CA ≤ 200 M FCFA — TVA bloquée",
    ca_threshold: 200_000_000,
    tva_blocked: true,
  },
  {
    code: "RSI",
    label: "RSI — Réel Simplifié d'Imposition",
    description: "200 M < CA ≤ 500 M FCFA — TVA autorisée",
    ca_threshold: 500_000_000,
    tva_blocked: false,
  },
  {
    code: "RNI",
    label: "RNI — Réel Normal d'Imposition",
    description: "CA > 500 M FCFA — TVA autorisée",
    ca_threshold: null,
    tva_blocked: false,
  },
];

// --- Lecture du régime fiscal ---

export function useFiscalRegime() {
  return useQuery({
    queryKey: [FISCAL_REGIME_KEY],
    queryFn: async (): Promise<TaxRegimeRead> => {
      const res = await apiClient.get("/accounting/fiscal-regime");
      return res.data;
    },
  });
}

// --- Mise à jour manuelle du régime fiscal ---

export function useUpdateFiscalRegime() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: TaxRegimeUpdate): Promise<TaxRegimeRead> => {
      const res = await apiClient.put("/accounting/fiscal-regime", body);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [FISCAL_REGIME_KEY] });
    },
  });
}

// --- Détection de dépassement de seuil CA (alerte uniquement) ---

export function useDetectCATreshold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (caAnnualTTC: number): Promise<TaxRegimeRead> => {
      const res = await apiClient.post(
        "/accounting/fiscal-regime/detect-ca",
        {},
        { params: { ca_annual_ttc: caAnnualTTC } },
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [FISCAL_REGIME_KEY] });
    },
  });
}

export const REGIME_BY_CODE: Record<string, RegimeInfo> = Object.fromEntries(
  REGIMES.map((r) => [r.code, r]),
);