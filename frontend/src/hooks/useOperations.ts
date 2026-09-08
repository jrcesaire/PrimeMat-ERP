/**
 * Hooks des modules opérationnels — facturation, paiements,
 * livraison, dépenses.
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const OPERATIONS_KEYS = {
  invoices: "invoices",
  payments: "payments",
  deliveries: "deliveries",
  expenses: "expenses",
};

// --- Types minimaux (réponses API) ---
export interface InvoiceLine {
  id: number;
  invoice_id: number;
  product_id: number | null;
  description: string | null;
  quantity: number;
  sell_by_length: boolean;
  unit_price: number;
  subtotal: number;
  cuts?: { id: number; quantity: number; length: number }[];
}

export interface Invoice {
  id: number;
  reference: string;
  order_id: number | null;
  partner_id: number;
  status: string;
  invoice_date: string;
  due_date: string | null;
  currency_code: string;
  amount_untaxed: number;
  tax_amount: number;
  amount_total: number;
  paid_amount: number;
  notes?: string | null;
  lines: InvoiceLine[];
}

export interface Payment {
  id: number;
  reference: string;
  payment_type: string;
  direction: string;
  partner_id: number | null;
  invoice_id: number | null;
  method: string;
  amount: number;
  payment_date: string;
  status: string;
}

export interface DeliveryNote {
  id: number;
  reference: string;
  order_id: number | null;
  partner_id: number;
  status: string;
  expected_date: string | null;
  shipped_date: string | null;
  delivered_date: string | null;
  lines?: {
    id: number;
    product_id: number | null;
    description: string | null;
    quantity_ordered: number;
    quantity_delivered: number;
    unit: string | null;
  }[];
}

export interface Expense {
  id: number;
  reference: string;
  label: string;
  category: string;
  amount: number;
  expense_date: string | null;
  payment_method: string;
  supplier_id: number | null;
  notes: string | null;
}

// --- Factures ---
export function useInvoices() {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.invoices],
    queryFn: async (): Promise<Invoice[]> => {
      const res = await apiClient.get("/invoicing/invoices");
      return res.data;
    },
  });
}

export function useInvoice(invoiceId: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.invoices, invoiceId],
    queryFn: async (): Promise<Invoice> => {
      const res = await apiClient.get(`/invoicing/invoices/${invoiceId}`);
      return res.data;
    },
    enabled: !!invoiceId,
  });
}

export function useCreateInvoiceFromOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      orderId,
      dueDays = 0,
    }: {
      orderId: number;
      dueDays?: number;
    }): Promise<Invoice> => {
      const res = await apiClient.post("/invoicing/invoices/from-order", {
        order_id: orderId,
        due_days: dueDays,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

// --- Paiements ---
export function usePayments() {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.payments],
    queryFn: async (): Promise<Payment[]> => {
      const res = await apiClient.get("/payments/payments");
      return res.data;
    },
  });
}

export function useCreatePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      partner_id: number;
      invoice_id?: number | null;
      method?: string;
      amount: number;
      direction?: string;
      notes?: string;
    }): Promise<Payment> => {
      const res = await apiClient.post("/payments/payments", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.payments] });
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

// --- Livraisons ---
export function useDeliveryNotes() {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.deliveries],
    queryFn: async (): Promise<DeliveryNote[]> => {
      const res = await apiClient.get("/delivery/notes");
      return res.data;
    },
  });
}

export function useDeliveryNote(deliveryId: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.deliveries, deliveryId],
    queryFn: async (): Promise<DeliveryNote> => {
      const res = await apiClient.get(`/delivery/notes/${deliveryId}`);
      return res.data;
    },
    enabled: !!deliveryId,
  });
}

export function useCreateDeliveryFromOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      order_id: number;
      expected_date?: string | null;
      notes?: string | null;
    }): Promise<DeliveryNote> => {
      const res = await apiClient.post("/delivery/notes/from-order", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.deliveries] });
    },
  });
}

export function useUpdateDeliveryStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      deliveryId,
      status,
    }: {
      deliveryId: number;
      status: string;
    }): Promise<DeliveryNote> => {
      const res = await apiClient.post(`/delivery/notes/${deliveryId}/status`, {
        status,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.deliveries] });
    },
  });
}

// --- Dépenses ---
export function useExpenses() {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.expenses],
    queryFn: async (): Promise<Expense[]> => {
      const res = await apiClient.get("/finance/expenses");
      return res.data;
    },
  });
}

export function useExpense(expenseId: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.expenses, expenseId],
    queryFn: async (): Promise<Expense> => {
      const res = await apiClient.get(`/finance/expenses/${expenseId}`);
      return res.data;
    },
    enabled: !!expenseId,
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      label: string;
      category?: string;
      amount: number;
      expense_date?: string | null;
      payment_method?: string;
      notes?: string | null;
    }): Promise<Expense> => {
      const res = await apiClient.post("/finance/expenses", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.expenses] });
    },
  });
}
