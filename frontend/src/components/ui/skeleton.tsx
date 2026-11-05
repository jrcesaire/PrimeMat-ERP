/**
 * Squelettes de chargement.
 *
 * Remplacent les mentions « Chargement… » par une forme qui reprend la
 * silhouette du contenu attendu : l'écran ne « saute » plus à l'arrivée des
 * données et la structure de la page est perçue immédiatement.
 *
 * Toutes les formes s'appuient sur les jetons sémantiques : elles suivent donc
 * le thème clair comme le thème sombre.
 */
import { cn } from "@/lib/utils";

/** Bloc pulsant — brique de base de tous les squelettes. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-control bg-subtle", className)}
    />
  );
}

/** Largeurs alternées : une liste de blocs de même longueur paraîtrait figée. */
const ROW_WIDTHS = [
  "w-full",
  "w-11/12",
  "w-full",
  "w-10/12",
  "w-full",
  "w-9/12",
];

/**
 * Silhouette de lignes, sans cadre — à poser dans une carte ou un tableau
 * existant, là où l'écran affichait « Chargement… ».
 */
export function RowsSkeleton({
  rows = 6,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={cn("space-y-3 p-6", className)} aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={cn("h-4", ROW_WIDTHS[i % ROW_WIDTHS.length])} />
      ))}
    </div>
  );
}

/** Silhouette d'un tableau complet : cadre, en-tête et lignes. */
export function TableSkeleton({
  rows = 6,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-card border border-line bg-surface",
        className,
      )}
      aria-busy="true"
    >
      <div className="border-b border-line bg-subtle/60 px-4 py-3">
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="divide-y divide-line">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3.5">
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-3.5 flex-1" />
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="h-3.5 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Silhouette d'une grille de cartes (catalogue, contacts, lanceur…). */
export function CardsSkeleton({
  count = 8,
  className,
}: {
  count?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
        className,
      )}
      aria-busy="true"
    >
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-[148px] rounded-card" />
      ))}
    </div>
  );
}

/** Silhouette d'un bloc de contenu : titre puis quelques lignes. */
export function BlockSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("space-y-3 rounded-card border border-line bg-surface p-5", className)}
      aria-busy="true"
    >
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}