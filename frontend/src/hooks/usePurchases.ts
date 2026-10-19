/**
 * Hooks pour le module Achats — fournisseurs, demandes (DA),
 * bons de commande (BC), réceptions (BR), factures fournisseur.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  Supplier,
  SupplierCreate,
  SupplierUpdate,
  SupplierSuggest,
  PurchaseRequest,
  PurchaseRequestCreate,
  PurchaseRequestUpdate,
  PurchaseOrder,
  PurchaseOrderCreate,
  PurchaseOrderLine,
  PurchaseReception,
  PurchaseReceptionCreate,
  SupplierInvoice,
  SupplierInvoiceCreate,
  SupplierInvoicePay,
  MatchingResult,
} from "@/lib/types";

export const PURCHASES_KEYS = {
  suppliers: "purchases-suppliers",
  requests: "purchases-requests",
  orders: "purchases-orders",
  receptions: "purchases-receptions",
  invoices: "purchases-invoices",
  suggestions: "purchases-suggestions",
};

// --- Fournisseurs ---
export function useSuppliers(search?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.suppliers, search ?? ""],
    queryFn: async (): Promise<Supplier[]> => {
      const res = await apiClient.get("/purchases/suppliers", {
        params: search ? { search } : { limit: 200 },
      });
      return res.data;
    },
  });
}

export function useSupplier(supplierId: number | null) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.suppliers, supplierId],
    queryFn: async (): Promise<Supplier> => {
      const res = await apiClient.get(`/purchases/suppliers/${supplierId}`);
      return res.data;
    },
    enabled: !!supplierId,
  });
}

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SupplierCreate): Promise<Supplier> => {
      const res = await apiClient.post("/purchases/suppliers", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.suppliers] });
    },
  });
}

export function useUpdateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: SupplierUpdate;
    }): Promise<Supplier> => {
      const res = await apiClient.put(`/purchases/suppliers/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.suppliers] });
    },
  });
}

export function useDeleteSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (supplierId: number): Promise<void> => {
      await apiClient.delete(`/purchases/suppliers/${supplierId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.suppliers] });
    },
  });
}

/** Note un fournisseur (1 à 5). */
export function useRateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      rating,
    }: {
      id: number;
      rating: number;
    }): Promise<Supplier> => {
      const res = await apiClient.post(`/purchases/suppliers/${id}/rating`, {
        rating,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.suppliers] });
    },
  });
}

/** Suggestions de fournisseurs (dernier prix, note, délai). */
export function useSupplierSuggestions(query?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.suggestions, "suppliers", query ?? ""],
    queryFn: async (): Promise<SupplierSuggest[]> => {
      const res = await apiClient.get("/purchases/suppliers/suggestions", {
        params: query ? { query } : {},
      });
      return res.data;
    },
  });
}

/** Suggestions de produits/fournisseurs (historique de prix). */
export function usePriceSuggestions(query?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.suggestions, "products", query ?? ""],
    queryFn: async (): Promise<SupplierSuggest[]> => {
      const res = await apiClient.get("/purchases/suggestions", {
        params: query ? { query } : {},
      });
      return res.data;
    },
  });
}

// --- Demandes d'achat (DA) ---
export function usePurchaseRequests(status?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.requests, status ?? ""],
    queryFn: async (): Promise<PurchaseRequest[]> => {
      const res = await apiClient.get("/purchases/requests", {
        params: { ...(status ? { status } : {}), limit: 200 },
      });
      return res.data;
    },
  });
}

export function usePurchaseRequest(requestId: number | null) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.requests, requestId],
    queryFn: async (): Promise<PurchaseRequest> => {
      const res = await apiClient.get(`/purchases/requests/${requestId}`);
      return res.data;
    },
    enabled: !!requestId,
  });
}

export function useCreatePurchaseRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PurchaseRequestCreate): Promise<PurchaseRequest> => {
      const res = await apiClient.post("/purchases/requests", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
    },
  });
}

export function useUpdatePurchaseRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: PurchaseRequestUpdate;
    }): Promise<PurchaseRequest> => {
      const res = await apiClient.put(`/purchases/requests/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
    },
  });
}

function useRequestAction(path: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (requestId: number): Promise<PurchaseRequest> => {
      const res = await apiClient.post(`/purchases/requests/${requestId}/${path}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
    },
  });
}

export function useSubmitPurchaseRequest() {
  return useRequestAction("submit");
}

export function useApprovePurchaseRequest() {
  return useRequestAction("approve");
}

/** Rejette une DA (motif obligatoire côté backend). */
export function useRejectPurchaseRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      reason,
    }: {
      id: number;
      reason: string;
    }): Promise<PurchaseRequest> => {
      const res = await apiClient.post(`/purchases/requests/${id}/reject`, {
        reason,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
    },
  });
}

/** Supprime une DA rejetée (POST /delete → 204). */
export function useDeletePurchaseRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (requestId: number): Promise<void> => {
      await apiClient.post(`/purchases/requests/${requestId}/delete`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
    },
  });
}

// --- Bons de commande (BC) ---
export function usePurchaseOrders(status?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.orders, status ?? ""],
    queryFn: async (): Promise<PurchaseOrder[]> => {
      const res = await apiClient.get("/purchases/orders", {
        params: { ...(status ? { status } : {}), limit: 200 },
      });
      return res.data;
    },
  });
}

export function usePurchaseOrder(orderId: number | null) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.orders, orderId],
    queryFn: async (): Promise<PurchaseOrder> => {
      const res = await apiClient.get(`/purchases/orders/${orderId}`);
      return res.data;
    },
    enabled: !!orderId,
  });
}

/** Lignes d'un BC (utile pour pré-remplir BR / facture). */
export function usePurchaseOrderLines(orderId: number | null) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.orders, orderId, "lines"],
    queryFn: async (): Promise<PurchaseOrderLine[]> => {
      const res = await apiClient.get(`/purchases/orders/${orderId}/lines`);
      return res.data;
    },
    enabled: !!orderId,
  });
}

export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PurchaseOrderCreate): Promise<PurchaseOrder> => {
      const res = await apiClient.post("/purchases/orders", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
    },
  });
}

/** Convertit une DA approuvée en BC brouillon (→ 201). */
export function useConvertRequestToOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (requestId: number): Promise<PurchaseOrder> => {
      const res = await apiClient.post(
        `/purchases/orders/${requestId}/convert-from-request`,
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.requests] });
    },
  });
}

function useOrderAction(path: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: number): Promise<PurchaseOrder> => {
      const res = await apiClient.post(`/purchases/orders/${orderId}/${path}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.receptions] });
    },
  });
}

export function useSubmitPurchaseOrder() {
  return useOrderAction("submit");
}

export function useConfirmPurchaseOrder() {
  return useOrderAction("confirm");
}

export function useCancelPurchaseOrder() {
  return useOrderAction("cancel");
}

// --- Réceptions (BR) ---
export function usePurchaseReceptions(orderId?: number) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.receptions, orderId ?? ""],
    queryFn: async (): Promise<PurchaseReception[]> => {
      const res = await apiClient.get("/purchases/receptions", {
        params: { ...(orderId ? { order_id: orderId } : {}), limit: 200 },
      });
      return res.data;
    },
  });
}

export function useCreatePurchaseReception() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PurchaseReceptionCreate): Promise<PurchaseReception> => {
      const res = await apiClient.post("/purchases/receptions", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.receptions] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
    },
  });
}

/** Valide une BR (mouvement de stock + statut BC mis à jour). */
export function useValidatePurchaseReception() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (receptionId: number): Promise<PurchaseReception> => {
      const res = await apiClient.post(
        `/purchases/receptions/${receptionId}/validate`,
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.receptions] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.orders] });
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.invoices] });
    },
  });
}

// --- Factures fournisseur ---
export function useSupplierInvoices(status?: string) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.invoices, status ?? ""],
    queryFn: async (): Promise<SupplierInvoice[]> => {
      const res = await apiClient.get("/purchases/invoices", {
        params: { ...(status ? { status } : {}), limit: 200 },
      });
      return res.data;
    },
  });
}

export function useSupplierInvoice(invoiceId: number | null) {
  return useQuery({
    queryKey: [PURCHASES_KEYS.invoices, invoiceId],
    queryFn: async (): Promise<SupplierInvoice> => {
      const res = await apiClient.get(`/purchases/invoices/${invoiceId}`);
      return res.data;
    },
    enabled: !!invoiceId,
  });
}

export function useCreateSupplierInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SupplierInvoiceCreate): Promise<SupplierInvoice> => {
      const res = await apiClient.post("/purchases/invoices", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.invoices] });
    },
  });
}

/** Rapprochement 3 voies (BC / BR / facture) → MatchingResult. */
export function useMatchSupplierInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: number): Promise<MatchingResult> => {
      const res = await apiClient.post(`/purchases/invoices/${invoiceId}/match`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.invoices] });
    },
  });
}

/** Comptabilise la facture (écriture ACH : D 601 / C 401). */
export function usePostSupplierInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: number): Promise<SupplierInvoice> => {
      const res = await apiClient.post(`/purchases/invoices/${invoiceId}/post`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.invoices] });
    },
  });
}

/** Enregistre un règlement (écriture BAN : D 401 / C 511). */
export function usePaySupplierInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: SupplierInvoicePay;
    }): Promise<SupplierInvoice> => {
      const res = await apiClient.post(`/purchases/invoices/${id}/pay`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PURCHASES_KEYS.invoices] });
    },
  });
}



