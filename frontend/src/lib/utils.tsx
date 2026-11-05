/** Utilitaires pour les classes CSS. */
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formate un montant avec devise (séparateurs d'espaces, défaut FCFA). */
export function formatCurrency(amount: number | string | null | undefined, currency = "FCFA"): string {
  const n = Number(amount ?? 0);
  const symbol = currency || "FCFA";
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n) + " " + symbol;
}

/** Formate un nombre simple (quantités, mètres...). */
export function formatNumber(value: number | string | null | undefined, decimals = 0): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: decimals }).format(n);
}

/** Formate une date ISO en JJ/MM/AAAA. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR");
}

/**
 * Dernier segment d'un chemin d'URL.
 *
 * Sert aux sous-routes de module : « /dashboard/sales/orders » → « orders »,
 * ce qui permet à une page d'ouvrir le bon onglet ou la bonne vue.
 */
export function lastRouteSegment(pathname: string | null | undefined): string {
  const clean = (pathname ?? "").replace(/\/+$/, "");
  return clean.split("/").filter(Boolean).pop() ?? "";
}

/**
 * Tons sémantiques des pastilles d'état.
 *
 * Reposent sur les jetons de `globals.css` : une pastille écrite avec ces
 * classes s'adapte automatiquement au mode sombre (fond `*-soft`, texte plein).
 */
export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

export const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-subtle text-muted",
  info: "bg-primary-soft text-primary",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
};

/** Libellés, ton et classes des statuts de documents. */
export const STATUS_LABELS: Record<
  string,
  { label: string; tone: Tone; className: string }
> = {
  draft: { label: "Brouillon", tone: "neutral", className: TONE_CLASSES.neutral },
  confirmed: { label: "Confirmé", tone: "info", className: TONE_CLASSES.info },
  posted: { label: "Confirmée", tone: "info", className: TONE_CLASSES.info },
  partially_paid: {
    label: "Partiellement payée",
    tone: "warning",
    className: TONE_CLASSES.warning,
  },
  paid: { label: "Payée", tone: "success", className: TONE_CLASSES.success },
  pending: { label: "En attente", tone: "warning", className: TONE_CLASSES.warning },
  in_progress: { label: "En cours", tone: "info", className: TONE_CLASSES.info },
  reserved: { label: "Réservé", tone: "info", className: TONE_CLASSES.info },
  shipped: { label: "Expédié", tone: "info", className: TONE_CLASSES.info },
  delivered: { label: "Livré", tone: "success", className: TONE_CLASSES.success },
  completed: { label: "Terminé", tone: "success", className: TONE_CLASSES.success },
  cancelled: { label: "Annulé", tone: "danger", className: TONE_CLASSES.danger },
  converted: { label: "Converti", tone: "info", className: TONE_CLASSES.info },
  // --- Achats ---
  submitted: { label: "Soumis", tone: "info", className: TONE_CLASSES.info },
  approved: { label: "Approuvé", tone: "success", className: TONE_CLASSES.success },
  rejected: { label: "Rejeté", tone: "danger", className: TONE_CLASSES.danger },
  partially_received: {
    label: "Partiellement reçu",
    tone: "warning",
    className: TONE_CLASSES.warning,
  },
  received: { label: "Reçu", tone: "success", className: TONE_CLASSES.success },
  done: { label: "Terminé", tone: "success", className: TONE_CLASSES.success },
  validated: { label: "Validé", tone: "success", className: TONE_CLASSES.success },
  match_ok: { label: "Rapproché", tone: "success", className: TONE_CLASSES.success },
  qty_diff: { label: "Écart quantité", tone: "warning", className: TONE_CLASSES.warning },
  price_diff: { label: "Écart prix", tone: "warning", className: TONE_CLASSES.warning },
  no_reference: {
    label: "Sans référence",
    tone: "danger",
    className: TONE_CLASSES.danger,
  },
};

/** Pastille d'état d'un document — style « pill » de la maquette. */
export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_LABELS[status] ?? {
    label: status,
    tone: "neutral" as Tone,
    className: TONE_CLASSES.neutral,
  };
  return (
    <span
      className={`inline-flex items-center rounded-chip px-2.5 py-0.5 text-[11px] font-medium ${cfg.className}`}
    >
      {cfg.label}
    </span>
  );
}
