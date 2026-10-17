/**
 * Hooks du module Comptabilité — configuration OHADA (Phase 1).
 *
 * Paramètres par pays, exercices comptables, taux de change,
 * contraintes OHADA et initialisation du plan comptable standard.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { apiClient } from "@/lib/api/client";

export const OHADA_KEYS = {
  parameters: "ohada-parameters",
  constraints: "ohada-constraints",
  fiscalYears: "ohada-fiscal-years",
  currentFiscalYear: "ohada-current-fiscal-year",
  exchangeRates: "ohada-exchange-rates",
  seedResult: "ohada-seed-result",
};

// --- Types (miroir des schémas backend) ---
export interface OHADAParameter {
  id: number;
  company_id: number;
  country_code: string;
  currency_code: string;
  rate_to_fx: number | null;
  fiscal_year_start: string | null;
  fiscal_year_end: string | null;
  tax_rate_percentage: number | null;
  is_active: boolean;
}

export interface OHADAParameterPayload {
  country_code: string;
  currency_code: string;
  rate_to_fx?: number | null;
  fiscal_year_start?: string | null;
  fiscal_year_end?: string | null;
  tax_rate_percentage?: number | null;
  is_active?: boolean;
}

export interface FiscalYear {
  id: number;
  company_id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
}

export interface FiscalYearPayload {
  name: string;
  start_date: string;
  end_date: string;
}

export interface ExchangeRate {
  id: number;
  company_id: number;
  base_currency: string;
  quote_currency: string;
  rate: number;
}

export interface ExchangeRatePayload {
  base_currency: string;
  quote_currency: string;
  rate: number;
}

export interface OHADACheckConstraint {
  can_open: boolean;
  message: string;
}

export interface SeedResult {
  created: number;
  total: number;
  journals_created: number;
}

export interface SettingValue {
  key: string;
  value: string;
}

// --- Paramètres OHADA (configuration par pays) ---
export function useOHADAParameters() {
  return useQuery({
    queryKey: [OHADA_KEYS.parameters],
    queryFn: async (): Promise<OHADAParameter[]> => {
      const res = await apiClient.get("/accounting/ohada/parameters");
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

export function useUpsertOHADAParameter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: OHADAParameterPayload): Promise<OHADAParameter> => {
      const res = await apiClient.put("/accounting/ohada/parameters", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.parameters] });
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.constraints] });
    },
  });
}

// --- Contraintes OHADA (paramètre actif + exercice ouvert) ---
export function useOHADAConstraints() {
  return useQuery({
    queryKey: [OHADA_KEYS.constraints],
    queryFn: async (): Promise<OHADACheckConstraint> => {
      const res = await apiClient.get("/accounting/ohada/constraints");
      return res.data;
    },
  });
}

// --- Exercices comptables ---
export function useFiscalYears(status?: string) {
  return useQuery({
    queryKey: [OHADA_KEYS.fiscalYears, status ?? "all"],
    queryFn: async (): Promise<FiscalYear[]> => {
      const res = await apiClient.get("/accounting/fiscal-years", {
        params: status ? { status } : undefined,
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

export function useCurrentFiscalYear() {
  return useQuery({
    queryKey: [OHADA_KEYS.currentFiscalYear],
    queryFn: async (): Promise<FiscalYear | null> => {
      const res = await apiClient.get("/accounting/fiscal-years/current");
      return res.data ?? null;
    },
    retry: false,
  });
}

export function useCreateFiscalYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: FiscalYearPayload): Promise<FiscalYear> => {
      const res = await apiClient.post("/accounting/fiscal-years", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.fiscalYears] });
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.currentFiscalYear] });
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.constraints] });
    },
  });
}

export function useCloseFiscalYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (yearId: number): Promise<FiscalYear> => {
      const res = await apiClient.post(`/accounting/fiscal-years/${yearId}/close`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.fiscalYears] });
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.currentFiscalYear] });
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.constraints] });
    },
  });
}

// --- Taux de change ---
export function useExchangeRates() {
  return useQuery({
    queryKey: [OHADA_KEYS.exchangeRates],
    queryFn: async (): Promise<ExchangeRate[]> => {
      const res = await apiClient.get("/accounting/exchange-rates");
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

export function useUpsertExchangeRate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ExchangeRatePayload): Promise<ExchangeRate> => {
      const res = await apiClient.put("/accounting/exchange-rates", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.exchangeRates] });
    },
  });
}

// --- Plan comptable OHADA (seed du modèle standard) ---
export function useSeedOhadaPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<SeedResult> => {
      const res = await apiClient.post("/accounting/accounts/seed");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OHADA_KEYS.seedResult] });
    },
  });
}

// --- Paramètres libres (forme juridique, activité NAF/OHADA) ---
export function useSetting(key: string) {
  return useQuery({
    queryKey: ["core-setting", key],
    queryFn: async (): Promise<SettingValue | null> => {
      try {
        const res = await apiClient.get(`/core/settings/${key}`);
        return res.data as SettingValue;
      } catch (error) {
        // Paramètre absent : valeur par défaut côté wizard
        if (error instanceof AxiosError && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}

export function useUpsertSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      key: string;
      value: string;
      type?: string;
      is_public?: boolean;
      description?: string;
    }): Promise<SettingValue> => {
      const res = await apiClient.post("/core/settings/", {
        type: "string",
        is_public: true,
        ...data,
      });
      return res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["core-setting", variables.key] });
    },
  });
}
