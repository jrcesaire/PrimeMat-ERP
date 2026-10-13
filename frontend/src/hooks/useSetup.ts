/**
 * Hooks de configuration initiale (premier lancement) — /core/setup.
 *
 * - useSetupStatus  : état public du premier lancement
 * - useSetupAdmin   : création entreprise + compte admin (base vierge)
 * - useSetupCompany : complétion du profil entreprise (admin connecté)
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const SETUP_KEY = "setup-status";

export interface SetupStatus {
  needs_admin: boolean;
  needs_company: boolean;
  company_name: string | null;
  company_code: string | null;
  currency_code: string | null;
}

export interface SetupAdminPayload {
  company_name: string;
  company_code: string;
  currency_code: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export function useSetupStatus() {
  return useQuery({
    queryKey: [SETUP_KEY],
    queryFn: async (): Promise<SetupStatus> => {
      const res = await apiClient.get("/core/setup/status");
      return res.data;
    },
    staleTime: 10_000,
    retry: false,
  });
}

export function useSetupAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SetupAdminPayload) => {
      const res = await apiClient.post("/core/setup/admin", data);
      return res.data as { message: string; email: string; company_code: string };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SETUP_KEY] });
    },
  });
}

export function useSetupCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      data: Partial<{
        name: string;
        establishment: string;
        slogan: string;
        phone: string;
        email: string;
        website: string;
        address_line1: string;
        address_city: string;
        ncc: string;
        rccm: string;
        share_capital: string;
      }>,
    ) => {
      const res = await apiClient.post("/core/setup/company", data);
      return res.data as { message: string; company_id: number };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SETUP_KEY] });
      queryClient.invalidateQueries({ queryKey: ["core", "company"] });
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });
}
