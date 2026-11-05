/**
 * Hooks du module Comptabilité — immobilisations et amortissements.
 *
 * Fournit :
 * - useFixedAssets          : liste des immobilisations (filtre par statut)
 * - useFixedAsset           : fiche d'une immobilisation + plan d'amortissement
 * - useFixedAssetSummary    : synthèse comptable (cumul, VNC, reste à doter)
 * - useCreateFixedAsset     : création (plan d'amortissement généré)
 * - useUpdateFixedAsset     : mise à jour (plan recalculé si nécessaire)
 * - useDeleteFixedAsset     : suppression (refusée si des dotations sont comptabilisées)
 * - useGenerateDepreciation : comptabilise les dotations échues (D 681 / C 28x)
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
  DepreciationRunResult,
  FixedAsset,
  FixedAssetCreate,
  FixedAssetSummary,
  FixedAssetUpdate,
} from "@/lib/types";

export const FIXED_ASSET_KEYS = {
  list: (status: string | null) => ["fixed-assets", status ?? "all"] as const,
  detail: (assetId: number) => ["fixed-asset", assetId] as const,
  summary: (assetId: number) => ["fixed-asset-summary", assetId] as const,
};

/**
 * Invalide toutes les données d'immobilisations.
 *
 * Les volumes sont faibles et une seule action (création, recalcul du plan,
 * comptabilisation d'une dotation) touche à la fois la liste, la fiche et la
 * synthèse : rafraîchir l'ensemble évite les états incohérents à l'écran.
 */
function invalidateFixedAssets(queryClient: QueryClient): void {
  for (const prefix of ["fixed-assets", "fixed-asset", "fixed-asset-summary"]) {
    queryClient.invalidateQueries({ queryKey: [prefix] });
  }
}

/** Immobilisations de l'entreprise (filtre optionnel par statut). */
export function useFixedAssets(status?: string) {
  return useQuery({
    queryKey: FIXED_ASSET_KEYS.list(status ?? null),
    queryFn: async (): Promise<FixedAsset[]> => {
      const res = await apiClient.get("/accounting/fixed-assets", {
        params: status ? { status } : undefined,
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

/** Fiche d'une immobilisation, avec son plan d'amortissement. */
export function useFixedAsset(assetId: number | null) {
  return useQuery({
    queryKey: FIXED_ASSET_KEYS.detail(assetId ?? 0),
    queryFn: async (): Promise<FixedAsset | null> => {
      if (!assetId) return null;
      const res = await apiClient.get(`/accounting/fixed-assets/${assetId}`);
      return res.data;
    },
    enabled: !!assetId,
  });
}

/** Synthèse comptable : cumul des dotations, VNC, reste à comptabiliser. */
export function useFixedAssetSummary(assetId: number | null) {
  return useQuery({
    queryKey: FIXED_ASSET_KEYS.summary(assetId ?? 0),
    queryFn: async (): Promise<FixedAssetSummary | null> => {
      if (!assetId) return null;
      const res = await apiClient.get(
        `/accounting/fixed-assets/${assetId}/summary`,
      );
      return res.data;
    },
    enabled: !!assetId,
  });
}

/** Créer une immobilisation (le plan d'amortissement est généré). */
export function useCreateFixedAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: FixedAssetCreate): Promise<FixedAsset> => {
      const res = await apiClient.post("/accounting/fixed-assets", body);
      return res.data;
    },
    onSuccess: () => invalidateFixedAssets(queryClient),
  });
}

/** Mettre à jour une immobilisation (plan recalculé si les paramètres changent). */
export function useUpdateFixedAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: FixedAssetUpdate;
    }): Promise<FixedAsset> => {
      const res = await apiClient.put(`/accounting/fixed-assets/${id}`, data);
      return res.data;
    },
    onSuccess: () => invalidateFixedAssets(queryClient),
  });
}

/** Supprimer une immobilisation (refusée si des dotations sont comptabilisées). */
export function useDeleteFixedAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (assetId: number): Promise<void> => {
      await apiClient.delete(`/accounting/fixed-assets/${assetId}`);
    },
    onSuccess: () => invalidateFixedAssets(queryClient),
  });
}

/**
 * Comptabilise les dotations échues (``D 681 / C 28x``).
 *
 * ``asOf`` limite la comptabilisation aux échéances arrivées à terme à cette
 * date ; par défaut le backend retient la date du jour.
 */
export function useGenerateDepreciation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assetId,
      asOf,
    }: {
      assetId: number;
      asOf?: string;
    }): Promise<DepreciationRunResult> => {
      const res = await apiClient.post(
        `/accounting/fixed-assets/${assetId}/generate-depreciation`,
        { as_of: asOf ?? null },
      );
      return res.data;
    },
    onSuccess: () => invalidateFixedAssets(queryClient),
  });
}
