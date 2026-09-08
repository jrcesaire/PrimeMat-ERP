/**
 * Hooks pour le module CRM — partenaires, contacts, sites.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Partner, Site, PartnerCreate } from "@/lib/types";

export const CRM_KEYS = {
  partners: "crm-partners",
  sites: "crm-sites",
};

export function usePartners(role?: string) {
  return useQuery({
    queryKey: [CRM_KEYS.partners, role],
    queryFn: async (): Promise<Partner[]> => {
      const params = new URLSearchParams();
      if (role) params.append("role", role);
      const res = await apiClient.get(`/crm/partners?${params.toString()}`);
      return res.data;
    },
  });
}

export function usePartner(partnerId: number) {
  return useQuery({
    queryKey: [CRM_KEYS.partners, partnerId],
    queryFn: async (): Promise<Partner> => {
      const res = await apiClient.get(`/crm/partners/${partnerId}`);
      return res.data;
    },
    enabled: !!partnerId,
  });
}

export function useClients() {
  return usePartners("client");
}

export function useSuppliers() {
  return usePartners("supplier");
}

export function useSites() {
  return useQuery({
    queryKey: [CRM_KEYS.sites],
    queryFn: async (): Promise<Site[]> => {
      const res = await apiClient.get("/crm/sites");
      return res.data;
    },
  });
}

export function useCreatePartner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PartnerCreate): Promise<Partner> => {
      const res = await apiClient.post("/crm/partners", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CRM_KEYS.partners] });
    },
  });
}

export function useUpdatePartner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: Partial<PartnerCreate>;
    }): Promise<Partner> => {
      const res = await apiClient.put(`/crm/partners/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CRM_KEYS.partners] });
    },
  });
}