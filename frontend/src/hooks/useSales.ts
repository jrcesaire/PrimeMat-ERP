/**
 * Hooks pour le module Ventes — devis, commandes.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  Quote,
  SalesOrder,
  QuoteCreate,
  QuoteUpdate,
  SalesOrderCreate,
  SalesOrderUpdate,
} from "@/lib/types";
import { STOCK_KEYS } from "@/hooks/useStock";

export const SALES_KEYS = {
  quotes: "sales-quotes",
  orders: "sales-orders",
};

// --- Quotes ---
export function useQuotes() {
  return useQuery({
    queryKey: [SALES_KEYS.quotes],
    queryFn: async (): Promise<Quote[]> => {
      const res = await apiClient.get("/sales/quotes");
      return res.data;
    },
  });
}

export function useQuote(quoteId: number) {
  return useQuery({
    queryKey: [SALES_KEYS.quotes, quoteId],
    queryFn: async (): Promise<Quote> => {
      const res = await apiClient.get(`/sales/quotes/${quoteId}`);
      return res.data;
    },
    enabled: !!quoteId,
  });
}

export function useCreateQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: QuoteCreate): Promise<Quote> => {
      const res = await apiClient.post("/sales/quotes", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
    },
  });
}

export function useConfirmQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (quoteId: number): Promise<SalesOrder> => {
      const res = await apiClient.post(`/sales/quotes/${quoteId}/confirm`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}

export function useUpdateQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: QuoteUpdate;
    }): Promise<Quote> => {
      const res = await apiClient.put(`/sales/quotes/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
    },
  });
}

export function useDeleteQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (quoteId: number): Promise<void> => {
      await apiClient.delete(`/sales/quotes/${quoteId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
    },
  });
}

/** Remet un devis confirmé au brouillon (annule la commande liée). */
export function useQuoteBackToDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (quoteId: number): Promise<Quote> => {
      const res = await apiClient.post(`/sales/quotes/${quoteId}/back-to-draft`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.quotes] });
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}

export function useUpdateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: SalesOrderUpdate;
    }): Promise<SalesOrder> => {
      const res = await apiClient.put(`/sales/orders/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}

export function useDeleteOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: number): Promise<void> => {
      await apiClient.delete(`/sales/orders/${orderId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}

/** Remet une commande confirmée au brouillon (libère les réservations). */
export function useOrderBackToDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: number): Promise<SalesOrder> => {
      const res = await apiClient.post(`/sales/orders/${orderId}/back-to-draft`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
      queryClient.invalidateQueries({ queryKey: [STOCK_KEYS.levels] });
    },
  });
}

// --- Orders ---
export function useOrders() {
  return useQuery({
    queryKey: [SALES_KEYS.orders],
    queryFn: async (): Promise<SalesOrder[]> => {
      const res = await apiClient.get("/sales/orders");
      return res.data;
    },
  });
}

export function useOrder(orderId: number) {
  return useQuery({
    queryKey: [SALES_KEYS.orders, orderId],
    queryFn: async (): Promise<SalesOrder> => {
      const res = await apiClient.get(`/sales/orders/${orderId}`);
      return res.data;
    },
    enabled: !!orderId,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SalesOrderCreate): Promise<SalesOrder> => {
      const res = await apiClient.post("/sales/orders", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}

export function useConfirmOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: number): Promise<any> => {
      const res = await apiClient.post(`/sales/orders/${orderId}/confirm`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SALES_KEYS.orders] });
    },
  });
}
