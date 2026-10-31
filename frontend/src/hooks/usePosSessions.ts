/**
 * Hooks pour la gestion des sessions de caisse (Point de Vente).
 *
 * Endpoints backend : /api/v1/sales/pos/sessions*
 *   GET    /sales/pos/sessions          — liste (paginée, entreprise courante)
 *   GET    /sales/pos/sessions/{id}     — détail
 *   POST   /sales/pos/sessions          — ouverture
 *   POST   /sales/pos/sessions/{id}/close — clôture
 *   PUT    /sales/pos/sessions/{id}     — maj (notes, session ouverte uniquement)
 */
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  PosSession,
  PosSessionCreate,
  PosSessionClose,
  PosSessionCloseReport,
  PosSessionsPage,
  PosFundMovement,
  PosFundMovementCreate,
  PosFundMovementsPage,
} from "@/lib/types";

export const POS_SESSION_KEYS = {
  sessions: "pos-sessions",
  session: (id: number) => ["pos-sessions", "detail", id],
};

/** Liste des sessions de caisse de l'entreprise courante. */
export function usePosSessions(skip = 0, limit = 50) {
  return useQuery({
    queryKey: [POS_SESSION_KEYS.sessions, skip, limit],
    queryFn: async (): Promise<PosSessionsPage> => {
      const res = await apiClient.get(
        `/sales/pos/sessions?skip=${skip}&limit=${limit}`,
      );
      return res.data;
    },
  });
}

/** Détail d'une session de caisse. */
export function usePosSession(sessionId: number | null) {
  return useQuery({
    queryKey: POS_SESSION_KEYS.session(sessionId ?? 0),
    queryFn: async (): Promise<PosSession> => {
      const res = await apiClient.get(`/sales/pos/sessions/${sessionId}`);
      return res.data;
    },
    enabled: sessionId != null,
  });
}

/** Ouvrir une nouvelle session de caisse. */
export function useOpenPosSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PosSessionCreate): Promise<PosSession> => {
      const res = await apiClient.post(`/sales/pos/sessions`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POS_SESSION_KEYS.sessions] });
    },
  });
}

/** Clôturer une session de caisse ouverte. */
export function useClosePosSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: PosSessionClose;
    }): Promise<PosSession> => {
      const res = await apiClient.post(`/sales/pos/sessions/${id}/close`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POS_SESSION_KEYS.sessions] });
    },
  });
}

/** Mettre à jour une session ouverte (notes uniquement). */
export function useUpdatePosSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: { notes?: string | null };
    }): Promise<PosSession> => {
      const res = await apiClient.put(`/sales/pos/sessions/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POS_SESSION_KEYS.sessions] });
    },
  });
}

/** Récupère le rapport de clôture d'une session de caisse. */
export function usePosSessionCloseReport(sessionId: number | null) {
  return useQuery({
    queryKey: ["pos-sessions", "close-report", sessionId],
    queryFn: async (): Promise<PosSessionCloseReport> => {
      const res = await apiClient.get(
        `/sales/pos/sessions/${sessionId}/close-report`,
      );
      return res.data;
    },
    enabled: sessionId != null,
  });
}

// ------------------------------------------------------------------ #
// Mouvements de fonds manuels (PRD §4.1.2 §5)
// ------------------------------------------------------------------ #

export const POS_FUND_MOVEMENT_KEYS = {
  movements: (sessionId?: number) =>
    sessionId
      ? ["pos-fund-movements", "session", sessionId]
      : ["pos-fund-movements"],
};

/** Liste des mouvements de fonds d'une session (ou de l'entreprise si sessionId omis). */
export function usePosFundMovements(
  sessionId: number | null,
  skip = 0,
  limit = 50
) {
  return useQuery({
    queryKey: [...POS_FUND_MOVEMENT_KEYS.movements(sessionId ?? undefined), skip, limit],
    queryFn: async (): Promise<PosFundMovementsPage> => {
      const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
      if (sessionId) params.set("session_id", String(sessionId));
      const res = await apiClient.get(`/sales/pos/fund-movements?${params}`);
      return res.data;
    },
    enabled: true,
  });
}

/** Créer un mouvement de fonds (dépôt ou retrait) en caisse. */
export function useCreatePosFundMovement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PosFundMovementCreate): Promise<PosFundMovement> => {
      const res = await apiClient.post(`/sales/pos/fund-movements`, data);
      return res.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: POS_FUND_MOVEMENT_KEYS.movements(variables.session_id),
      });
    },
  });
}