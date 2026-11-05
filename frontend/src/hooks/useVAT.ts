/**
 * Hooks du module Comptabilité — TVA déclarative.
 *
 * Fournit :
 * - useVATPreview        : aperçu (non enregistré) d'une période
 * - useVATReturns        : historique des déclarations (filtre par statut)
 * - useVATReturn         : détail d'une déclaration
 * - useCreateVATReturn   : création d'un brouillon
 * - useRecomputeVATReturn: recalcul d'un brouillon
 * - useSubmitVATReturn   : liquidation (solde des comptes de TVA)
 * - usePayVATReturn      : règlement de la TVA due (D 441 / C 521)
 * - useDeleteVATReturn   : suppression d'un brouillon
 */
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  VATPayRequest,
  VATPreview,
  VATReturn,
  VATReturnCreate,
} from "@/lib/types";

export const VAT_KEYS = {
  list: (status: string | null) => ["vat-returns", status ?? "all"] as const,
  detail: (returnId: number) => ["vat-return", returnId] as const,
  preview: (start: string, end: string) =>
    ["vat-preview", start, end] as const,
};

/**
 * Invalide toutes les données de TVA.
 *
 * Une déclaration touche à la fois l'historique, son détail et l'aperçu de la
 * période (l'écriture de liquidation modifie les soldes) : rafraîchir
 * l'ensemble évite les états incohérents à l'écran.
 */
function invalidateVAT(queryClient: QueryClient): void {
  for (const prefix of ["vat-returns", "vat-return", "vat-preview"]) {
    queryClient.invalidateQueries({ queryKey: [prefix] });
  }
}

/** Aperçu non enregistré : TVA collectée / déductible de la période. */
export function useVATPreview(periodStart: string, periodEnd: string) {
  return useQuery({
    queryKey: VAT_KEYS.preview(periodStart, periodEnd),
    queryFn: async (): Promise<VATPreview | null> => {
      if (!periodStart || !periodEnd) return null;
      const res = await apiClient.get("/accounting/vat-returns/preview", {
        params: { period_start: periodStart, period_end: periodEnd },
      });
      return res.data;
    },
    enabled: Boolean(periodStart && periodEnd && periodEnd >= periodStart),
  });
}

/** Historique des déclarations (filtre optionnel par statut). */
export function useVATReturns(status?: string) {
  return useQuery({
    queryKey: VAT_KEYS.list(status ?? null),
    queryFn: async (): Promise<VATReturn[]> => {
      const res = await apiClient.get("/accounting/vat-returns", {
        params: status ? { status } : undefined,
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

/** Détail d'une déclaration, avec son détail par compte. */
export function useVATReturn(returnId: number | null) {
  return useQuery({
    queryKey: VAT_KEYS.detail(returnId ?? 0),
    queryFn: async (): Promise<VATReturn | null> => {
      if (!returnId) return null;
      const res = await apiClient.get(`/accounting/vat-returns/${returnId}`);
      return res.data;
    },
    enabled: !!returnId,
  });
}

/** Crée une déclaration en brouillon (montants calculés sur la période). */
export function useCreateVATReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: VATReturnCreate): Promise<VATReturn> => {
      const res = await apiClient.post("/accounting/vat-returns", body);
      return res.data;
    },
    onSuccess: () => invalidateVAT(queryClient),
  });
}

/** Recalcule une déclaration en brouillon. */
export function useRecomputeVATReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (returnId: number): Promise<VATReturn> => {
      const res = await apiClient.post(
        `/accounting/vat-returns/${returnId}/recompute`,
      );
      return res.data;
    },
    onSuccess: () => invalidateVAT(queryClient),
  });
}

/** Soumet la déclaration : génère l'écriture de liquidation de la TVA. */
export function useSubmitVATReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (returnId: number): Promise<VATReturn> => {
      const res = await apiClient.post(
        `/accounting/vat-returns/${returnId}/submit`,
      );
      return res.data;
    },
    onSuccess: () => invalidateVAT(queryClient),
  });
}

/** Règle la TVA due (``D 441 / C 521``). */
export function usePayVATReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      returnId,
      data,
    }: {
      returnId: number;
      data: VATPayRequest;
    }): Promise<VATReturn> => {
      const res = await apiClient.post(
        `/accounting/vat-returns/${returnId}/pay`,
        data,
      );
      return res.data;
    },
    onSuccess: () => invalidateVAT(queryClient),
  });
}

/** Supprime une déclaration en brouillon. */
export function useDeleteVATReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (returnId: number): Promise<void> => {
      await apiClient.delete(`/accounting/vat-returns/${returnId}`);
    },
    onSuccess: () => invalidateVAT(queryClient),
  });
}
