/**
 * Hooks pour les réglages du Point de Vente (PoS).
 *
 * Endpoints backend : /api/v1/sales/pos/settings
 *   GET  /sales/pos/settings — réglages PoS de l'entreprise courante
 *   PUT  /sales/pos/settings — mise à jour partielle (permission « pos:edit »)
 *
 * PRD « Improvements module PoS » §4.2.2.6 : la tuile « Réglages » du
 * dashboard PoS ne regroupe que les paramètres du Point de Vente.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { PosSettings, PosSettingsUpdate } from "@/lib/types";

export const POS_SETTINGS_KEYS = {
  settings: "pos-settings",
};

/** Réglages du Point de Vente (heures de clôture, URL du ticket). */
export function usePosSettings() {
  return useQuery({
    queryKey: [POS_SETTINGS_KEYS.settings],
    queryFn: async (): Promise<PosSettings> => {
      const res = await apiClient.get(`/sales/pos/settings`);
      return res.data;
    },
  });
}

/** Enregistre les réglages du Point de Vente (Administrateur / Gérant). */
export function useUpdatePosSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PosSettingsUpdate): Promise<PosSettings> => {
      const res = await apiClient.put(`/sales/pos/settings`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POS_SETTINGS_KEYS.settings] });
    },
  });
}
