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
    onSuccess: (token) => {
      setTokens(token);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.user] });
      router.push("/dashboard");
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
      await apiClient.post("/core/auth/logout");
    },
    onSuccess: () => {
      clearTokens();
      queryClient.clear();
      router.push("/login");
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
