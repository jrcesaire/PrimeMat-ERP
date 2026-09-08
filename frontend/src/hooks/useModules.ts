/**
 * Hook pour récupérer les modules depuis le Core.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { ModuleInfo } from "@/lib/types";

export function useModules() {
  return useQuery({
    queryKey: ["modules"],
    queryFn: async (): Promise<ModuleInfo[]> => {
      const res = await apiClient.get("/core/system/modules");
      return res.data;
    },
  });
}

/**
 * État simplifié des modules — accessible à tout utilisateur authentifié.
 * Utilisé par le lanceur d'applications du tableau de bord.
 */
export interface ModuleState {
  name: string;
  status: string;
  is_active: boolean;
}

export function useModuleStates() {
  return useQuery({
    queryKey: ["module-states"],
    queryFn: async (): Promise<ModuleState[]> => {
      const res = await apiClient.get("/core/system/modules/active");
      return res.data;
    },
    staleTime: 60_000,
  });
}

export function useModuleActions() {
  const queryClient = useQueryClient();

  const install = useMutation({
    mutationFn: (name: string) =>
      apiClient.post(`/core/system/modules/${name}/install`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["modules"] }),
  });

  const activate = useMutation({
    mutationFn: (name: string) =>
      apiClient.post(`/core/system/modules/${name}/activate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["modules"] }),
  });

  const deactivate = useMutation({
    mutationFn: (name: string) =>
      apiClient.post(`/core/system/modules/${name}/deactivate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["modules"] }),
  });

  return { install, activate, deactivate };
}
