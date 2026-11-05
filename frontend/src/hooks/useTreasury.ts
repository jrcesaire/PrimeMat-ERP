/**
 * Hooks du module Trésorerie — comptes, relevés bancaires et rapprochement
 * (Phase 2 PRD ; backend `app/modules/finance` → `/finance/treasury/*`).
 *
 * Fournit :
 * - useTreasuryAccounts      : comptes de trésorerie (banque / caisse / mobile money)
 * - useCreateTreasuryAccount : création d'un compte
 * - useUpdateTreasuryAccount : mise à jour d'un compte
 * - useDeleteTreasuryAccount : suppression d'un compte (relevés en cascade)
 * - useStatements            : relevés d'un compte
 * - useStatement             : détail d'un relevé (avec ses lignes)
 * - useCreateStatement       : création d'un relevé
 * - useAddStatementLine      : ajout d'une ligne au relevé (montant signé)
 * - useDeleteStatementLine   : suppression d'une ligne non rapprochée
 * - useCloseStatement        : clôture d'un relevé (verrouille ses lignes)
 * - useAutoReconcile         : rapprochement automatique du relevé
 * - useReconcileLine         : rapprochement manuel ligne de relevé ↔ écriture
 * - useUnreconcileLine       : retrait d'un rapprochement
 * - useReconciliationReport  : état de rapprochement du compte
 */
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  BankStatement,
  BankStatementCreate,
  BankStatementLine,
  BankStatementLineCreate,
  ReconciliationReport,
  ReconcileResult,
  TreasuryAccount,
  TreasuryAccountCreate,
  TreasuryAccountUpdate,
} from "@/lib/types";

export const TREASURY_KEYS = {
  accounts: (activeOnly: boolean) => ["treasury-accounts", activeOnly] as const,
  statements: (accountId: number) => ["treasury-statements", accountId] as const,
  statement: (statementId: number) => ["treasury-statement", statementId] as const,
  reconciliation: (accountId: number) =>
    ["treasury-reconciliation", accountId] as const,
};

/**
 * Invalide toutes les données de trésorerie.
 *
 * Les volumes sont faibles (quelques comptes, quelques relevés) : un
 * rapprochement modifie à la fois les relevés, leurs lignes et le rapport
 * du compte. Rafraîchir l'ensemble évite les états incohérents à l'écran.
 */
function invalidateTreasury(queryClient: QueryClient): void {
  for (const prefix of [
    "treasury-accounts",
    "treasury-statements",
    "treasury-statement",
    "treasury-reconciliation",
  ]) {
    queryClient.invalidateQueries({ queryKey: [prefix] });
  }
}

// --------------------------------------------------------------------------- //
// Comptes de trésorerie
// --------------------------------------------------------------------------- //

/** Comptes de trésorerie de l'entreprise. */
export function useTreasuryAccounts(activeOnly = false) {
  return useQuery({
    queryKey: TREASURY_KEYS.accounts(activeOnly),
    queryFn: async (): Promise<TreasuryAccount[]> => {
      const res = await apiClient.get("/finance/treasury/accounts", {
        params: { active_only: activeOnly },
      });
      return Array.isArray(res.data) ? res.data : [];
    },
  });
}

/** Créer un compte de trésorerie (code unique par entreprise). */
export function useCreateTreasuryAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: TreasuryAccountCreate): Promise<TreasuryAccount> => {
      const res = await apiClient.post("/finance/treasury/accounts", body);
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Mettre à jour un compte de trésorerie. */
export function useUpdateTreasuryAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: TreasuryAccountUpdate;
    }): Promise<TreasuryAccount> => {
      const res = await apiClient.put(`/finance/treasury/accounts/${id}`, data);
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Supprimer un compte de trésorerie (ses relevés partent en cascade). */
export function useDeleteTreasuryAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      await apiClient.delete(`/finance/treasury/accounts/${id}`);
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

// --------------------------------------------------------------------------- //
// Relevés bancaires
// --------------------------------------------------------------------------- //

/** Relevés d'un compte de trésorerie (du plus récent au plus ancien). */
export function useStatements(accountId: number | null) {
  return useQuery({
    queryKey: TREASURY_KEYS.statements(accountId ?? 0),
    queryFn: async (): Promise<BankStatement[]> => {
      if (!accountId) return [];
      const res = await apiClient.get(
        `/finance/treasury/accounts/${accountId}/statements`,
      );
      return Array.isArray(res.data) ? res.data : [];
    },
    enabled: !!accountId,
  });
}

/** Détail d'un relevé, avec ses lignes. */
export function useStatement(statementId: number | null) {
  return useQuery({
    queryKey: TREASURY_KEYS.statement(statementId ?? 0),
    queryFn: async (): Promise<BankStatement | null> => {
      if (!statementId) return null;
      const res = await apiClient.get(
        `/finance/treasury/statements/${statementId}`,
      );
      return res.data;
    },
    enabled: !!statementId,
  });
}

/** Créer un relevé bancaire (soldes d'ouverture / clôture). */
export function useCreateStatement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      accountId,
      data,
    }: {
      accountId: number;
      data: BankStatementCreate;
    }): Promise<BankStatement> => {
      const res = await apiClient.post(
        `/finance/treasury/accounts/${accountId}/statements`,
        data,
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Ajouter une ligne à un relevé ouvert (montant signé : + encaissement). */
export function useAddStatementLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      statementId,
      data,
    }: {
      statementId: number;
      data: BankStatementLineCreate;
    }): Promise<BankStatementLine> => {
      const res = await apiClient.post(
        `/finance/treasury/statements/${statementId}/lines`,
        data,
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Supprimer une ligne non rapprochée d'un relevé ouvert. */
export function useDeleteStatementLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (lineId: number): Promise<void> => {
      await apiClient.delete(`/finance/treasury/lines/${lineId}`);
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Clôturer un relevé (verrouille ses lignes : plus de saisie ni de rapprochement). */
export function useCloseStatement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (statementId: number): Promise<BankStatement> => {
      const res = await apiClient.post(
        `/finance/treasury/statements/${statementId}/close`,
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

// --------------------------------------------------------------------------- //
// Rapprochement
// --------------------------------------------------------------------------- //

/**
 * Rapprochement automatique : apparie chaque ligne non rapprochée avec la
 * première écriture de même montant à ±5 jours (règle appliquée par le backend).
 */
export function useAutoReconcile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (statementId: number): Promise<ReconcileResult> => {
      const res = await apiClient.post(
        `/finance/treasury/statements/${statementId}/auto-reconcile`,
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Rapprocher manuellement une ligne de relevé et une ligne d'écriture. */
export function useReconcileLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      lineId,
      entryLineId,
    }: {
      lineId: number;
      entryLineId: number;
    }): Promise<BankStatementLine> => {
      const res = await apiClient.post(
        `/finance/treasury/lines/${lineId}/reconcile`,
        { entry_line_id: entryLineId },
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** Retirer le rapprochement d'une ligne (relevé ouvert uniquement). */
export function useUnreconcileLine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (lineId: number): Promise<BankStatementLine> => {
      const res = await apiClient.post(
        `/finance/treasury/lines/${lineId}/unreconcile`,
      );
      return res.data;
    },
    onSuccess: () => invalidateTreasury(queryClient),
  });
}

/** État de rapprochement d'un compte : soldes + lignes en attente des deux côtés. */
export function useReconciliationReport(accountId: number | null) {
  return useQuery({
    queryKey: TREASURY_KEYS.reconciliation(accountId ?? 0),
    queryFn: async (): Promise<ReconciliationReport | null> => {
      if (!accountId) return null;
      const res = await apiClient.get(
        `/finance/treasury/accounts/${accountId}/reconciliation`,
      );
      return res.data;
    },
    enabled: !!accountId,
  });
}
