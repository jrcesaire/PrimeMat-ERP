/**
 * Hooks du module Reporting — agrégats BI pour les graphiques.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const REPORTING_KEYS = {
  kpis: "reporting-kpis",
  salesTrend: "reporting-sales-trend",
  topProducts: "reporting-top-products",
  topPartners: "reporting-top-partners",
  invoiceStatus: "reporting-invoice-status",
  paymentsByMethod: "reporting-payments-by-method",
  expensesByCategory: "reporting-expenses-by-category",
};

export interface ReportingKpis {
  total_invoiced: number;
  total_collected: number;
  total_expenses: number;
  cash_flow: number;
  outstanding: number;
  invoice_count: number;
  orders_total: number;
  orders_confirmed: number;
  orders_draft: number;
  pending_delivery_qty: number;
  gross_margin: number;
}

export interface SalesTrendPoint {
  month: string;
  invoiced: number;
  collected: number;
  expenses: number;
}

export interface TopProduct {
  product: string;
  category: string;
  revenue: number;
  quantity: number;
}

export interface TopPartner {
  partner: string;
  revenue: number;
  invoice_count: number;
}

export interface InvoiceStatusItem {
  status: string;
  count: number;
  amount: number;
}

export interface PaymentMethodItem {
  method: string;
  amount: number;
  count: number;
}

export interface ExpenseCategoryItem {
  category: string;
  amount: number;
  count: number;
}

export function useReportingKpis() {
  return useQuery({
    queryKey: [REPORTING_KEYS.kpis],
    queryFn: async (): Promise<ReportingKpis> => {
      const res = await apiClient.get("/reporting/kpis");
      return res.data;
    },
  });
}

export function useSalesTrend(months = 6) {
  return useQuery({
    queryKey: [REPORTING_KEYS.salesTrend, months],
    queryFn: async (): Promise<SalesTrendPoint[]> => {
      const res = await apiClient.get(`/reporting/sales-trend?months=${months}`);
      return res.data;
    },
  });
}

export function useTopProducts(limit = 10) {
  return useQuery({
    queryKey: [REPORTING_KEYS.topProducts, limit],
    queryFn: async (): Promise<TopProduct[]> => {
      const res = await apiClient.get(`/reporting/top-products?limit=${limit}`);
      return res.data;
    },
  });
}

export function useTopPartners(limit = 10) {
  return useQuery({
    queryKey: [REPORTING_KEYS.topPartners, limit],
    queryFn: async (): Promise<TopPartner[]> => {
      const res = await apiClient.get(`/reporting/top-partners?limit=${limit}`);
      return res.data;
    },
  });
}

export function useInvoiceStatus() {
  return useQuery({
    queryKey: [REPORTING_KEYS.invoiceStatus],
    queryFn: async (): Promise<InvoiceStatusItem[]> => {
      const res = await apiClient.get("/reporting/invoice-status");
      return res.data;
    },
  });
}

export function usePaymentsByMethod() {
  return useQuery({
    queryKey: [REPORTING_KEYS.paymentsByMethod],
    queryFn: async (): Promise<PaymentMethodItem[]> => {
      const res = await apiClient.get("/reporting/payments-by-method");
      return res.data;
    },
  });
}

export function useExpensesByCategory() {
  return useQuery({
    queryKey: [REPORTING_KEYS.expensesByCategory],
    queryFn: async (): Promise<ExpenseCategoryItem[]> => {
      const res = await apiClient.get("/reporting/expenses-by-category");
      return res.data;
    },
  });
}
