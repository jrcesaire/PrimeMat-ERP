/**
 * Presets métier FR pour le système de confirmation.
 *
 * Usage : `const { confirmed } = await confirm(confirmDeleteOptions("le devis DEV-1"));`
 */
import type { ConfirmOptions } from "./types";

/** Suppression standard (ton danger, réversible ou non). */
export function confirmDeleteOptions(label: string): ConfirmOptions {
  return {
    title: `Supprimer « ${label} » ?`,
    description:
      "Cette action est irréversible. L'élément supprimé ne pourra pas être récupéré.",
    confirmLabel: "Supprimer",
    cancelLabel: "Annuler",
    tone: "danger",
  };
}

/** Suppression sensible : exige de retaper le nom exact (équivalent `confirmationKeyword`). */
export function confirmHardDeleteOptions(
  label: string,
  keyword: string = label,
): ConfirmOptions {
  return {
    ...confirmDeleteOptions(label),
    title: `Supprimer définitivement « ${label} » ?`,
    description:
      "Pour confirmer, retapez le nom exact de l'élément ci-dessous. Cette action est irréversible.",
    requireKeyword: keyword,
    keywordLabel: `Tapez « ${keyword} » pour confirmer`,
  };
}

/** Remise au brouillon (le document pourra être modifié puis confirmé à nouveau). */
export function confirmBackToDraftOptions(label: string): ConfirmOptions {
  return {
    title: `Remettre « ${label} » au brouillon ?`,
    description: "Le document pourra être modifié puis confirmé à nouveau.",
    confirmLabel: "Remettre au brouillon",
    cancelLabel: "Annuler",
    tone: "warning",
  };
}

/** Confirmation / validation d'un document. */
export function confirmPostOptions(label: string): ConfirmOptions {
  return {
    title: `Confirmer « ${label} » ?`,
    description:
      "Le document confirmé ne pourra plus être modifié sans remise au brouillon.",
    confirmLabel: "Confirmer",
    cancelLabel: "Annuler",
    tone: "info",
  };
}

/** Clôture de vente. */
export function confirmCloseOptions(label: string): ConfirmOptions {
  return {
    title: `Clôturer « ${label} » ?`,
    description: "La vente clôturée sera archivée. Cette action est irréversible.",
    confirmLabel: "Clôturer",
    cancelLabel: "Annuler",
    tone: "warning",
  };
}
