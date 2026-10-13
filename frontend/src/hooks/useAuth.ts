/**
 * Hooks pour l'authentification — utilise react-query.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient, handleApiError } from "@/lib/api/client";
import { setTokens, clearTokens, isAuthenticated } from "@/lib/auth/auth";
import { Company, LoginRequest, Token, UserWithRoles } from "@/lib/types";

// Keys pour react-query
export const QUERY_KEYS = {
  user: "user",
  companies: "companies",
  modules: "modules",
  permissions: "permissions",
};

export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LoginRequest): Promise<Token> => {
      const response = await apiClient.post("/core/auth/login", data);
      return response.data;
    },
    onSuccess: async (token) => {
      setTokens(token);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.user] });
      // Premier lancement : si l'entreprise n'est pas encore configurée,
      // on redirige vers l'étape 2 du wizard (profil entreprise).
      try {
        const res = await apiClient.get("/core/setup/status");
        const status = res.data as {
          needs_company?: boolean;
          company_code?: string | null;
        };
        if (status?.needs_company || !status?.company_code) {
          router.push("/setup/company");
          return;
        }
      } catch {
        // Statut indisponible — comportement normal
      }
      router.push("/");
    },
    onError: (error) => {
      const err = handleApiError(error);
      console.error("Login failed:", err.message);
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      try {
        await apiClient.post("/core/auth/logout");
      } catch {
        // La deconnexion locale doit aboutir meme si l endpoint echoue
      }
    },
    onSuccess: () => {
      clearTokens();
      queryClient.clear();
      router.push("/login");
      router.refresh();
    },
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: [QUERY_KEYS.user],
    queryFn: async (): Promise<UserWithRoles | null> => {
      if (!isAuthenticated()) return null;
      try {
        const response = await apiClient.get("/core/auth/me");
        return response.data;
      } catch (error) {
        if (error instanceof Error && "response" in error) {
          const axiosError = error as { response?: { status: number } };
          if (axiosError.response?.status === 401) {
            clearTokens();
            return null;
          }
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Vérifie une permission de l'utilisateur courant (code « ressource:action »).
 *
 * Masque les boutons sensibles (suppression paiement/facture/BL/devis) —
 * la sécurité réelle reste serveur (require_permission → 403).
 */
export function usePermission() {
  const { data: currentUser } = useCurrentUser();
  const permissions = currentUser?.permissions ?? [];
  const isSuper = currentUser?.is_superuser === true;
  return (code: string): boolean => isSuper || permissions.includes(code);
}

/**
 * Entreprise de l'utilisateur courant (logo, nom, coordonnées...).
 * Invalider COMPANY_KEY après une mise à jour (page Paramètres).
 */
export const COMPANY_KEY = ["core", "company"];

export function useCurrentCompany() {
  const { data: user } = useCurrentUser();
  return useQuery({
    queryKey: [...COMPANY_KEY, user?.company_id],
    queryFn: async (): Promise<Company | null> => {
      if (!user?.company_id) return null;
      const response = await apiClient.get(`/core/companies/${user.company_id}`);
      return response.data;
    },
    enabled: !!user?.company_id,
    staleTime: 1000 * 60 * 5,
  });
}
