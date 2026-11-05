/**
 * Composant EmptyState — état vide d'une liste, d'un tableau ou d'un formulaire.
 *
 * Reprend la mise en page de la maquette : icône encadrée, titre, précision,
 * et action facultative.
 */
import { cn } from "@/lib/utils";
import type { ElementType } from "react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ElementType;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center px-6 py-12 text-center", className)}>
      {Icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-control bg-subtle">
          <Icon className="h-6 w-6 text-faint" />
        </div>
      )}
      <p className="text-[13px] font-semibold text-ink">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-[12px] text-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}