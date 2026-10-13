/**
 * Types du système de confirmation — clone du pattern `material-ui-confirm`
 * adapté à notre stack (shadcn/ui + Tailwind, textes FR).
 */
import type { ReactNode } from "react";

/** Origine de la résolution : explicite (boutons) ou naturelle (Échap / overlay / démontage). */
export type ConfirmReason = "confirm" | "cancel" | "natural";

/** Ton visuel du dialogue : danger (suppressions), warning (brouillon/clôture), info (confirmations). */
export type ConfirmTone = "danger" | "warning" | "info";

export interface ConfirmOptions {
  /** Titre du dialogue. Défaut : « Confirmer l'action ». */
  title?: string;
  /** Texte explicatif sous le titre. */
  description?: ReactNode;
  /** Contenu libre additionnel (sous la description). */
  content?: ReactNode;
  /** Libellé du bouton de confirmation. Défaut : « Confirmer ». */
  confirmLabel?: string;
  /** Libellé du bouton d'annulation. Défaut : « Annuler ». */
  cancelLabel?: string;
  /** Ton visuel. Défaut : « info ». */
  tone?: ConfirmTone;
  /**
   * Si faux, l'utilisateur ne peut pas fermer sans choisir
   * (Échap / overlay / croix désactivés). Défaut : true.
   */
  allowClose?: boolean;
  /** Masque le bouton d'annulation (confirmation obligatoire). Défaut : false. */
  hideCancelButton?: boolean;
  /**
   * Mot-clé à retaper pour activer la confirmation
   * (équivalent de `confirmationKeyword` de material-ui-confirm).
   */
  requireKeyword?: string;
  /** Libellé d'aide du champ mot-clé. */
  keywordLabel?: string;
  /**
   * Si fourni, une case à cocher obligatoire avec ce libellé
   * (équivalent de `acknowledgement` de material-ui-confirm).
   */
  acknowledgement?: string;
  /** Focus automatique sur le bouton de confirmation (validation au clavier). Défaut : true. */
  autoFocusConfirm?: boolean;
}

export interface ConfirmResult {
  confirmed: boolean;
  reason: ConfirmReason;
}

/** Signature du hook : `confirm(options)` retourne une promesse résolue dans tous les cas (API v4). */
export type ConfirmFn = (options?: ConfirmOptions) => Promise<ConfirmResult>;

export interface ConfirmRequest {
  id: number;
  resolve: (result: ConfirmResult) => void;
  title: string;
  description?: ReactNode;
  content?: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  tone: ConfirmTone;
  allowClose: boolean;
  hideCancelButton: boolean;
  requireKeyword?: string;
  keywordLabel?: string;
  acknowledgement?: string;
  autoFocusConfirm: boolean;
}
