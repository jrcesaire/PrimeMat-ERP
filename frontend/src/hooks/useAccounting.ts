/**
 * Hooks du module Comptabilité — états financiers SYSCOHADA.
 *
 * Balance de vérification, compte de résultat, bilan, écritures
 * du journal et rattrapage comptable (backfill).
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export const ACCOUNTING_KEYS = {
  trialBalance: "accounting-trial-balance",
  incomeStatement: "accounting-income-statement",
  balanceSheet: "accounting-balance-sheet",
  journalEntries: "accounting-journal-entries",
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
      queryClient.invalidateQueries({
        queryKey: [ACCOUNTING_KEYS.journalEntries],
      });
    },
  });
}