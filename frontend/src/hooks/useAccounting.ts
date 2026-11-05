/**
 * Hooks du module Comptabilité — états financiers SYSCOHADA.
 *
 * Balance de vérification, compte de résultat, bilan, écritures
 * du journal et rattrapage comptable (backfill).
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  CreditNote,
  CreditNoteApply,
  CreditNoteCreate,
  CreditNoteIssue,
} from "@/lib/types";

export const ACCOUNTING_KEYS = {
  trialBalance: "accounting-trial-balance",
  incomeStatement: "accounting-income-statement",
  balanceSheet: "accounting-balance-sheet",
  journalEntries: "accounting-journal-entries",
  agedBalance: "accounting-aged-balance",
  cashFlow: "accounting-cash-flow",
};

// --- Types (réponses API) ---
export interface TrialBalanceLine {
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  balance: number;
}

export interface TrialBalance {
  lines: TrialBalanceLine[];
  total_debit: number;
  total_credit: number;
  balanced: boolean;
}

export interface IncomeStatementLine {
  label: string;
  codes: string[];
  amount: number;
}

export interface IncomeStatement {
  income: IncomeStatementLine[];
  expenses: IncomeStatementLine[];
  total_income: number;
  total_expenses: number;
  net_income: number;
}

export interface BalanceSheetLine {
  label: string;
  amount: number;
}

// --- Balance âgée ---
export interface AgedBalanceLine {
  partner_id: number;
  partner_name: string;
  invoice_count: number;
  total_due: number;
  not_due: number;
  d0_30: number;
  d31_60: number;
  d61_90: number;
  d90_plus: number;
}

export interface AgedBalanceTotals {
  total_due: number;
  not_due: number;
  d0_30: number;
  d31_60: number;
  d61_90: number;
  d90_plus: number;
}

export interface AgedBalance {
  partner_type: "customer" | "supplier";
  as_of: string;
  lines: AgedBalanceLine[];
  totals: AgedBalanceTotals;
  total_due: number;
}

// --- Cash-flow ---
export interface CashFlowAccount {
  account_code: string;
  account_name: string;
  opening_balance: number;
  inflows: number;
  outflows: number;
  net_flow: number;
  closing_balance: number;
}

export interface CashFlow {
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  inflows: number;
  outflows: number;
  net_flow: number;
  closing_balance: number;
  by_account: CashFlowAccount[];
}

export interface BalanceSheet {
  assets: BalanceSheetLine[];
  liabilities: BalanceSheetLine[];
  total_assets: number;
  total_liabilities: number;
  net_income: number;
}

export interface JournalEntryLine {
  account_code: string;
  label: string | null;
  debit: number;
  credit: number;
}

export interface JournalEntry {
  id: number;
  reference: string;
  entry_date: string;
  journal_code: string;
  source_type: string | null;
  source_id: number | null;
  description: string | null;
  total_debit: number;
  total_credit: number;
  status: string;
  lines: JournalEntryLine[];
}

// --- Balance de vérification ---
export function useTrialBalance() {
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.trialBalance],
    queryFn: async (): Promise<TrialBalance> => {
      const res = await apiClient.get("/accounting/financial/trial-balance");
      return res.data;
    },
  });
}

// --- Compte de résultat ---
export function useIncomeStatement() {
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.incomeStatement],
    queryFn: async (): Promise<IncomeStatement> => {
      const res = await apiClient.get(
        "/accounting/financial/income-statement"
      );
      return res.data;
    },
  });
}

// --- Bilan ---
export function useBalanceSheet() {
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.balanceSheet],
    queryFn: async (): Promise<BalanceSheet> => {
      const res = await apiClient.get("/accounting/financial/balance-sheet");
      return res.data;
    },
  });
}

// --- Balance âgée ---
export function useAgedBalance(
  params?: { partner_type?: "customer" | "supplier"; as_of?: string }
) {
  const partnerType = params?.partner_type ?? "customer";
  const asOf = params?.as_of;
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.agedBalance, partnerType, asOf ?? null],
    queryFn: async (): Promise<AgedBalance> => {
      const res = await apiClient.get("/accounting/financial/aged-balance", {
        params: {
          partner_type: partnerType,
          ...(asOf ? { as_of: asOf } : {}),
        },
      });
      return res.data;
    },
  });
}

// --- Cash-flow ---
export function useCashFlow(params?: { date_from?: string; date_to?: string }) {
  const dateFrom = params?.date_from;
  const dateTo = params?.date_to;
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.cashFlow, dateFrom ?? null, dateTo ?? null],
    queryFn: async (): Promise<CashFlow> => {
      const res = await apiClient.get("/accounting/financial/cash-flow", {
        params: {
          ...(dateFrom ? { date_from: dateFrom } : {}),
          ...(dateTo ? { date_to: dateTo } : {}),
        },
      });
      return res.data;
    },
  });
}

// --- Écritures du journal ---
export function useJournalEntries(limit = 50) {
  return useQuery({
    queryKey: [ACCOUNTING_KEYS.journalEntries, limit],
    queryFn: async (): Promise<JournalEntry[]> => {
      const res = await apiClient.get("/accounting/journal-entries", {
        params: { limit },
      });
      return Array.isArray(res.data) ? res.data : res.data.items ?? [];
    },
  });
}

// --- Rattrapage comptable (comptabilise les flux non traités) ---
export function useBackfill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<{
      total: number;
      created: Record<string, number>;
      message: string;
    }> => {
      const res = await apiClient.post("/accounting/post/backfill");
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [ACCOUNTING_KEYS.trialBalance],
      });
      queryClient.invalidateQueries({
        queryKey: [ACCOUNTING_KEYS.incomeStatement],
      });
      queryClient.invalidateQueries({
        queryKey: [ACCOUNTING_KEYS.balanceSheet],
      });
    },
  });
}

// --------------------------------------------------------------------------- //
// Avoirs / notes de crédit
// --------------------------------------------------------------------------- //
export const CREDIT_NOTE_KEYS = {
  list: "accounting-credit-notes",
};

/**
 * Liste des avoirs de l'entreprise.
 * Params optionnels : status, partner_id, type (customer|supplier).
 */
export function useCreditNotes(params?: {
  status?: string;
  partner_id?: number;
  type?: string;
}) {
  return useQuery({
    queryKey: [CREDIT_NOTE_KEYS.list, params ?? {}],
    queryFn: async (): Promise<CreditNote[]> => {
      const res = await apiClient.get("/accounting/credit-notes", { params });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

/** Créer un avoir (brouillon). */
export function useCreateCreditNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreditNoteCreate): Promise<CreditNote> => {
      const res = await apiClient.post("/accounting/credit-notes", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CREDIT_NOTE_KEYS.list] });
    },
  });
}

/** Émettre (comptabiliser) un avoir : draft → issued. */
export function useIssueCreditNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: CreditNoteIssue;
    }): Promise<CreditNote> => {
      const res = await apiClient.post(
        `/accounting/credit-notes/${id}/issue`,
        data
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CREDIT_NOTE_KEYS.list] });
    },
  });
}

/** Imputer un avoir sur une facture : issued → applied. */
export function useApplyCreditNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: CreditNoteApply;
    }): Promise<CreditNote> => {
      const res = await apiClient.post(
        `/accounting/credit-notes/${id}/apply`,
        data
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CREDIT_NOTE_KEYS.list] });
    },
  });
}

// --------------------------------------------------------------------------- //
// États auxiliaires — grand livre auxiliaire, chéancier, grand livre par compte
// --------------------------------------------------------------------------- //
export const AUXILIARY_KEYS = {
  partnerLedger: (partnerId: number, from: string, to: string) =>
    ["accounting-partner-ledger", partnerId, from, to] as const,
  paymentSchedule: (partnerType: string, asOf: string, horizon: number) =>
    ["accounting-payment-schedule", partnerType, asOf, horizon] as const,
  accountLedger: (accountCode: string, from: string, to: string) =>
    ["accounting-account-ledger", accountCode, from, to] as const,
};

/** Mouvement du grand livre auxiliaire d'un tiers. */
export interface PartnerLedgerLine {
  entry_id: number;
  reference: string;
  entry_date: string;
  journal_code: string;
  account_code: string;
  account_name: string;
  label: string | null;
  debit: number;
  credit: number;
  /** Solde progressif du tiers après ce mouvement. */
  balance: number;
}

export interface PartnerLedger {
  partner_id: number;
  partner_name: string;
  partner_code: string | null;
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  total_debit: number;
  total_credit: number;
  closing_balance: number;
  lines: PartnerLedgerLine[];
}

/** Échéance du chéancier. */
export interface PaymentScheduleLine {
  partner_id: number;
  partner_name: string;
  reference: string;
  invoice_date: string;
  due_date: string;
  amount_due: number;
  /** Négatif = en retard. */
  days_remaining: number;
  bucket: "overdue" | "d0_30" | "d31_60" | "d61_90" | "d90_plus";
}

export interface PaymentSchedule {
  partner_type: "customer" | "supplier";
  as_of: string;
  horizon_days: number;
  lines: PaymentScheduleLine[];
  totals: Record<string, number>;
  total: number;
}

/** Mouvement du grand livre d'un compte. */
export interface AccountLedgerMovement {
  entry_id: number;
  reference: string;
  entry_date: string;
  journal_code: string;
  label: string | null;
  debit: number;
  credit: number;
  balance: number;
}

export interface AccountLedger {
  account_code: string;
  account_name: string;
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  closing_balance: number;
  total_debit: number;
  total_credit: number;
  movements: AccountLedgerMovement[];
}

/** Grand livre auxiliaire d'un tiers : mouvements et solde progressif. */
export function usePartnerLedger(
  partnerId: number | null,
  dateFrom = "",
  dateTo = "",
) {
  return useQuery({
    queryKey: AUXILIARY_KEYS.partnerLedger(partnerId ?? 0, dateFrom, dateTo),
    queryFn: async (): Promise<PartnerLedger | null> => {
      if (!partnerId) return null;
      const res = await apiClient.get("/accounting/financial/partner-ledger", {
        params: {
          partner_id: partnerId,
          ...(dateFrom ? { date_from: dateFrom } : {}),
          ...(dateTo ? { date_to: dateTo } : {}),
        },
      });
      return res.data;
    },
    enabled: !!partnerId,
  });
}

/** Chéancier : échéances à venir et retards des factures non soldées. */
export function usePaymentSchedule(
  partnerType: "customer" | "supplier" = "customer",
  asOf = "",
  horizonDays = 90,
) {
  return useQuery({
    queryKey: AUXILIARY_KEYS.paymentSchedule(partnerType, asOf, horizonDays),
    queryFn: async (): Promise<PaymentSchedule | null> => {
      const res = await apiClient.get(
        "/accounting/financial/payment-schedule",
        {
          params: {
            partner_type: partnerType,
            horizon_days: horizonDays,
            ...(asOf ? { as_of: asOf } : {}),
          },
        },
      );
      return res.data;
    },
  });
}

/** Grand livre d'un compte du plan (mouvements chronologiques + cumul). */
export function useAccountLedger(
  accountCode: string,
  dateFrom = "",
  dateTo = "",
) {
  return useQuery({
    queryKey: AUXILIARY_KEYS.accountLedger(accountCode, dateFrom, dateTo),
    queryFn: async (): Promise<AccountLedger | null> => {
      if (!accountCode) return null;
      const res = await apiClient.get(
        `/accounting/financial/ledger/${accountCode}`,
        {
          params: {
            ...(dateFrom ? { date_from: dateFrom } : {}),
            ...(dateTo ? { date_to: dateTo } : {}),
          },
        },
      );
      return res.data;
    },
    enabled: Boolean(accountCode),
  });
}

// --------------------------------------------------------------------------- //
// Journal d'audit comptable
// --------------------------------------------------------------------------- //
export const AUDIT_KEYS = {
  list: (action: string, from: string, to: string) =>
    ["accounting-audit-logs", action, from, to] as const,
};

/** Entrée du journal d'audit comptable. */
export interface AuditLogEntry {
  id: number;
  company_id: number | null;
  user_id: number | null;
  /** `journal_entry.created` | `journal_entry.posted` */
  action: string;
  entity_type: string;
  entity_id: number | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

/**
 * Journal d'audit des écritures comptables (lecture seule).
 *
 * ``action`` filtre sur le type d'opération (``journal_entry.posted`` pour ne
 * voir que les publications, par exemple).
 */
export function useAccountingAuditLogs(
  action = "",
  dateFrom = "",
  dateTo = "",
) {
  return useQuery({
    queryKey: AUDIT_KEYS.list(action, dateFrom, dateTo),
    queryFn: async (): Promise<AuditLogEntry[]> => {
      const res = await apiClient.get("/accounting/audit-logs", {
        params: {
          entity_type: "journal_entry",
          ...(action ? { action } : {}),
          ...(dateFrom ? { date_from: dateFrom } : {}),
          ...(dateTo ? { date_to: dateTo } : {}),
        },
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}