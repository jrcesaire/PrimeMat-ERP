/**
 * Composant Chip — pastille de filtre ou de navigation secondaire.
 *
 * Deux usages dans la maquette :
 * - **filtres** (Ventes : « Tous », « Brouillons », « Confirmés ») ;
 * - **navigation secondaire** (Comptabilité : « Lettrage », « Avoirs », …).
 *
 * L'état actif est un aplat de la couleur primaire, l'état inactif une surface
 * blanche bordée.
 */
"use client";

import { cn } from "@/lib/utils";

export function Chip({
  active = false,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-chip px-3 text-[13px] font-medium transition-colors",
        active
          ? "bg-primary text-white"
          : "border border-line bg-surface text-muted hover:bg-subtle hover:text-ink",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/** Rangée de chips — espacement uniforme et défilement horizontal si besoin. */
export function ChipGroup({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {children}
    </div>
  );
}