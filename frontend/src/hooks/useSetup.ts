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
  /** Tous les champs obligatoires sont renseignés. */
  company_complete: boolean;
  /** Champs obligatoires manquants, prêts à afficher. */
  missing_fields: { field: string; label: string }[];
  /** Libellés seuls des champs manquants. */
  missing_labels: string[];
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

export interface SetupCompanyPayload {
  name?: string;
  establishment?: string;
  slogan?: string;
  phone?: string;
  email?: string;
  website?: string;
  logo?: string;
  street?: string;
  city?: string;
  country?: string;
  ncc?: string;
  rccm?: string;
  share_capital?: string;
  greffe?: string;
  importer_code?: string;
  social_security_code?: string;
  activity_code?: string;
  closing_date?: string;
  fiscal_year_months?: number;
  cgv?: string;
}

export interface SetupCompanyResult {
  message: string;
  company_id: number;
  /** L'entreprise porte désormais toutes les mentions obligatoires. */
  company_complete: boolean;
  missing_fields: { field: string; label: string }[];
  missing_labels: string[];
}

export function useSetupCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SetupCompanyPayload) => {
      const res = await apiClient.post("/core/setup/company", data);
      return res.data as SetupCompanyResult;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SETUP_KEY] });
      queryClient.invalidateQueries({ queryKey: ["core", "company"] });
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });
}

/**
 * Reporte l'étape de configuration initiale.
 *
 * L'utilisateur n'est plus ramené au formulaire à la connexion, mais la
 * création d'un devis ou d'une facture reste refusée (409) tant que les
 * mentions obligatoires manquent — l'écran revient alors.
 */
export function useSkipSetupCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/core/setup/company/skip");
      return res.data as { message: string; company_id: number };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SETUP_KEY] });
    },
  });
}
