/**
 * Hooks pour les utilisateurs — listes de choix (contact commercial...).
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { User } from "@/lib/types";

export const USERS_KEYS = {
  salespersons: "users-salespersons",
};

/**
 * Utilisateurs actifs pouvant être désignés comme contact commercial
 * (admin / manager / commerciaux) — `GET /core/users/salespersons`.
 */
export function useSalespersons() {
  return useQuery({
    queryKey: [USERS_KEYS.salespersons],
    queryFn: async (): Promise<User[]> => {
      const res = await apiClient.get("/core/users/salespersons");
      return res.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}