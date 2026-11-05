/**
 * Composant Tabs — onglets soulignés (style maquette « GEA ERP »).
 *
 * L'onglet actif est marqué par un trait de 2 px de la couleur primaire et un
 * libellé coloré ; les autres restent en texte secondaire. Un compteur
 * facultatif peut être affiché entre parenthèses (ex. « Devis (41) »).
 */
"use client";

import { cn } from "@/lib/utils";

export interface TabItem<T extends string> {
  key: T;
  label: string;
  /** Nombre d'éléments affiché à côté du libellé. */
  count?: number;
}

export function Tabs<T extends string>({
  value,
  onChange,
  items,
  className,
}: {
  value: T;
  onChange: (value: T) => void;
  items: TabItem<T>[];
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn("flex flex-wrap items-center gap-6 border-b border-line", className)}
    >
      {items.map((item) => {
        const active = item.key === value;
        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.key)}
            className={cn(
              "-mb-px flex items-center gap-1 border-b-2 pb-2.5 pt-1 text-[13px] font-medium transition-colors",
              active
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-ink",
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span className={cn(active ? "text-primary/70" : "text-faint")}>
                ({item.count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}