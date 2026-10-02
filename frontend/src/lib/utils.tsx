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

/** Libellés et classes des statuts de documents. */
export const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  draft: { label: "Brouillon", className: "bg-gray-100 text-gray-700" },
  confirmed: { label: "Confirmé", className: "bg-blue-100 text-blue-800" },
  posted: { label: "Confirmée", className: "bg-blue-100 text-blue-800" },
  partially_paid: { label: "Partiellement payée", className: "bg-amber-100 text-amber-800" },
  paid: { label: "Payée", className: "bg-green-100 text-green-800" },
  pending: { label: "En attente", className: "bg-yellow-100 text-yellow-800" },
  in_progress: { label: "En cours", className: "bg-indigo-100 text-indigo-800" },
  reserved: { label: "Réservé", className: "bg-indigo-100 text-indigo-800" },
  shipped: { label: "Expédié", className: "bg-cyan-100 text-cyan-800" },
  delivered: { label: "Livré", className: "bg-green-100 text-green-800" },
  completed: { label: "Terminé", className: "bg-green-100 text-green-800" },
  cancelled: { label: "Annulé", className: "bg-red-100 text-red-700" },
  converted: { label: "Converti", className: "bg-purple-100 text-purple-800" },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_LABELS[status] ?? { label: status, className: "bg-gray-100 text-gray-700" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.className}`}>
      {cfg.label}
    </span>
  );
}
