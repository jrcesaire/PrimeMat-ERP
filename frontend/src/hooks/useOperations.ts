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
  journals: "journals",
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
  journal_code: string | null;
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
export function useInvoices(orderId?: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.invoices, orderId ?? "all"],
    queryFn: async (): Promise<Invoice[]> => {
      const res = await apiClient.get("/invoicing/invoices", {
        params: orderId ? { order_id: orderId } : undefined,
      });
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
      mode = "full",
      value = null,
      post = false,
    }: {
      orderId: number;
      dueDays?: number;
      /** "full" : totale/solde — "down_payment_percent" / "down_payment_fixed" : acompte */
      mode?: "full" | "down_payment_percent" | "down_payment_fixed";
      value?: number | null;
      post?: boolean;
    }): Promise<Invoice> => {
      const res = await apiClient.post("/invoicing/invoices/from-order", {
        order_id: orderId,
        due_days: dueDays,
        mode,
        value,
        post,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

/** Résultat du parcours « Créer facture » depuis un devis. */
export interface QuoteInvoiceResult {
  quote_id: number;
  quote_reference: string;
  order_id: number;
  order_reference: string;
  invoice_id: number;
  invoice_reference: string;
  invoice_status: string;
  created: boolean;
}

/**
 * Crée la facture d'un devis confirmé (parcours de vente, étape 2).
 *
 * Idempotent côté serveur : si la commande liée est déjà facturée, la facture
 * existante est renvoyée avec `created = false` — le bouton sert alors de
 * « Voir la facture ».
 */
export function useCreateInvoiceFromQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      quoteId,
      mode = "full",
      value = null,
      dueDays = 0,
      post = false,
    }: {
      quoteId: number;
      mode?: "full" | "down_payment_percent" | "down_payment_fixed";
      value?: number | null;
      dueDays?: number;
      post?: boolean;
    }): Promise<QuoteInvoiceResult> => {
      const res = await apiClient.post(`/sales/quotes/${quoteId}/invoice`, {
        mode,
        value,
        due_days: dueDays,
        post,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

/** Confirme une facture brouillon (brouillon → comptabilisée). */
export function usePostInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: number): Promise<Invoice> => {
      const res = await apiClient.post(`/invoicing/invoices/${invoiceId}/post`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

/** Remet une facture confirmée en brouillon (refusé si un paiement existe). */
export function useResetInvoiceToDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: number): Promise<Invoice> => {
      const res = await apiClient.post(
        `/invoicing/invoices/${invoiceId}/reset-to-draft`
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

/** Annule une facture non payée (la commande redevient facturable). */
export function useCancelInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId: number): Promise<Invoice> => {
      const res = await apiClient.post(`/invoicing/invoices/${invoiceId}/cancel`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
    },
  });
}

// --- Paiements ---
export function usePayments(invoiceId?: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.payments, invoiceId ?? "all"],
    queryFn: async (): Promise<Payment[]> => {
      const res = await apiClient.get("/payments/payments", {
        params: invoiceId ? { invoice_id: invoiceId } : undefined,
      });
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
      payment_date?: string;
      journal_code?: string | null;
      direction?: string;
      notes?: string;
    }): Promise<Payment> => {
      const res = await apiClient.post("/payments/payments", data);
      return res.data;
    },
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.payments] });
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
      if (payment.invoice_id) {
        queryClient.invalidateQueries({
          queryKey: [OPERATIONS_KEYS.invoices, payment.invoice_id],
        });
      }
    },
  });
}

// --- Clôture de vente (dernière étape du parcours de vente) ---
export function useCloseOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: number) => {
      const res = await apiClient.post(`/sales/orders/${orderId}/close`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] });
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.invoices] });
      queryClient.invalidateQueries({ queryKey: [OPERATIONS_KEYS.deliveries] });
    },
  });
}

// --- Journaux comptables (registres caisse / banque / Mobile Money…) ---
export interface Journal {
  id: number;
  code: string;
  name: string;
  journal_type: string;
  is_active: boolean;
}

export function useJournals() {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.journals],
    queryFn: async (): Promise<Journal[]> => {
      const res = await apiClient.get("/accounting/journals");
      return res.data;
    },
    staleTime: 5 * 60_000,
  });
}

// --- Livraisons ---
export function useDeliveryNotes(orderId?: number) {
  return useQuery({
    queryKey: [OPERATIONS_KEYS.deliveries, orderId ?? "all"],
    queryFn: async (): Promise<DeliveryNote[]> => {
      const res = await apiClient.get("/delivery/notes", {
        params: orderId ? { order_id: orderId } : undefined,
      });
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
