/**
 * Briques de tableau — style maquette « GEA ERP ».
 *
 * Le tableau est présenté dans une carte bordée : en-tête en capitales
 * discrètes, lignes séparées par un filet de 1 px, et pied de tableau affichant
 * le nombre de lignes avec la pagination.
 *
 * Ces briques sont volontairement **présentationnelles** : les pages gardent la
 * main sur leurs données et leur logique, et adoptent le style progressivement.
 */
import { cn } from "@/lib/utils";

/** Conteneur bordé d'un tableau (ou de tout contenu tabulaire). */
export function TableShell({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-card border border-line bg-surface",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Cellule d'en-tête — capitales 10 px, texte secondaire. */
export function Th({
  className,
  children,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-[0.06em] text-muted",
        className,
      )}
      {...props}
    >
      {children}
    </th>
  );
}

/** Cellule de corps — taille 13 px, alignement à ajuster par la page. */
export function Td({
  className,
  children,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("px-4 py-3 text-[13px] text-ink", className)} {...props}>
      {children}
    </td>
  );
}

/** Ligne d'en-tête d'un tableau. */
export function TableHeadRow({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <tr
      className={cn(
        "border-b border-line bg-subtle/60 text-left",
        className,
      )}
    >
      {children}
    </tr>
  );
}

/** Ligne de corps — survol discret, séparateur bas. */
export function TableRow({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-line transition-colors last:border-0 hover:bg-subtle/60",
        className,
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

/**
 * Pied de tableau : nombre de lignes affichées et pagination.
 * Affiché uniquement lorsque la page fournit `total` ou `pageCount`.
 */
export function TableFootBar({
  shown,
  total,
  page,
  pageCount,
  onPageChange,
  className,
}: {
  /** Nombre de lignes rendues. */
  shown: number;
  /** Total disponible (facultatif) — ajouté après « au total ». */
  total?: number;
  page?: number;
  pageCount?: number;
  onPageChange?: (page: number) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-[11px] text-muted",
        className,
      )}
    >
      <span>
        {shown} ligne{shown > 1 ? "s" : ""} affichée{shown > 1 ? "s" : ""}
        {typeof total === "number" && total > shown ? ` sur ${total}` : ""}
      </span>
      {page !== undefined && pageCount !== undefined && pageCount > 1 && (
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Page précédente"
            disabled={page <= 1}
            onClick={() => onPageChange?.(page - 1)}
            className="flex h-6 w-6 items-center justify-center rounded-chip hover:bg-subtle disabled:opacity-40"
          >
            ‹
          </button>
          <span className="tabular-nums">
            {page} / {pageCount}
          </span>
          <button
            type="button"
            aria-label="Page suivante"
            disabled={page >= pageCount}
            onClick={() => onPageChange?.(page + 1)}
            className="flex h-6 w-6 items-center justify-center rounded-chip hover:bg-subtle disabled:opacity-40"
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
}