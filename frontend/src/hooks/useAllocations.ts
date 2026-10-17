/**
 * Hooks du module Comptabilité — lettrage tiers (rapprochement paiement ↔ facture).
 *
 * Fournit :
 * - useCreateAllocation   : création d'un lettrage (allocation)
 * useAllocationsForInvoice : lettrages d'une facture donnée
 * useAllocationsForPayment : lettrages d'un paiement donné
 * useAllocationSummary   : résumé factures avec solde restant à lettrer
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const ALLOCATION_KEYS = {
  summary: "accounting-allocation-summary",
  forInvoice: (invoiceId: number) => ["accounting-allocations", "invoice", invoiceId],
  forPayment: (paymentId: number) => ["accounting-allocations", "payment", paymentId],
};

// --- Types (réponses API) ---
export interface InvoiceAllocation {
  id: number;
  company_id: number;
  invoice_id: number;
  payment_id: number;
  allocated_amount: number;
  allocation_date: string;
  notes: string | null;
}

export interface InvoiceAllocationCreate {
  invoice_id: number;
  payment_id: number;
  allocated_amount: number;
  allocation_date: string;
  notes?: string;
}

export interface InvoiceAllocationSummary {
  invoice_id: number;
  invoice_reference: string;
  amount_total: number;
  allocated_amount: number;
  remaining_amount: number;
}

// --- Créer un lettrage ---
export function useCreateAllocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: InvoiceAllocationCreate): Promise<InvoiceAllocation> => {
      const res = await apiClient.post("/accounting/allocations", body);
      return res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [ALLOCATION_KEYS.summary],
      });
      queryClient.invalidateQueries({
        queryKey: ALLOCATION_KEYS.forInvoice(variables.invoice_id),
      });
      queryClient.invalidateQueries({
        queryKey: ALLOCATION_KEYS.forPayment(variables.payment_id),
      });
    },
  });
}

// --- Lettrages d'une facture ---
export function useAllocationsForInvoice(invoiceId: number | null) {
  return useQuery({
    queryKey: ALLOCATION_KEYS.forInvoice(invoiceId ?? 0),
    queryFn: async (): Promise<InvoiceAllocation[]> => {
      if (!invoiceId) return [];
      const res = await apiClient.get(
        `/accounting/allocations/invoice/${invoiceId}`
      );
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled: !!invoiceId,
  });
}

// --- Lettrages d'un paiement ---
export function useAllocationsForPayment(paymentId: number | null) {
  return useQuery({
    queryKey: ALLOCATION_KEYS.forPayment(paymentId ?? 0),
    queryFn: async (): Promise<InvoiceAllocation[]> => {
      if (!paymentId) return [];
      const res = await apiClient.get(
        `/accounting/allocations/payment/${paymentId}`
      );
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled: !!paymentId,
  });
}

// --- Résumé des factures avec solde restant ---
export function useAllocationSummary(partnerId?: number) {
  return useQuery({
    queryKey: [ALLOCATION_KEYS.summary, partnerId],
    queryFn: async (): Promise<InvoiceAllocationSummary[]> => {
      const res = await apiClient.get("/accounting/allocations/summary", {
        params: partnerId ? { partner_id: partnerId } : undefined,
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}
