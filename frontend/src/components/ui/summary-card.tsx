/**
 * Composant SummaryCard — panneau récapitulatif du rail droit.
 *
 * Reprend le bloc « Récapitulatif » de la maquette : titre et pastille d'état,
 * lignes libellé / valeur, total mis en avant, puis encart d'aide facultatif.
 */
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export interface SummaryRow {
  label: string;
  /** Valeur déjà formatée (montant, texte ou tiret). */
  value: string;
  /** Met la valeur en évidence (montant négatif, remise…). */
  emphasis?: boolean;
}

export function SummaryCard({
  title,
  badge,
  rows,
  totalLabel,
  totalValue,
  note,
  children,
  className,
}: {
  title: string;
  badge?: React.ReactNode;
  rows?: SummaryRow[];
  totalLabel?: string;
  totalValue?: string;
  /** Encart d'aide affiché sous le total. */
  note?: { title: string; description: string };
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-card border border-line bg-surface p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-[17px] font-semibold text-ink">{title}</h2>
        {badge}
      </div>

      {rows && rows.length > 0 && (
        <dl className="mt-5 space-y-3">
          {rows.map((row) => (
            <div key={row.label} className="flex items-baseline justify-between gap-3">
              <dt className="text-[13px] text-muted">{row.label}</dt>
              <dd
                className={cn(
                  "text-[13px] tabular-nums",
                  row.emphasis ? "font-semibold text-ink" : "text-ink",
                )}
              >
                {row.value}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {totalLabel && (
        <div className="mt-4 flex items-baseline justify-between gap-3 border-t border-line pt-4">
          <span className="text-[15px] font-semibold text-ink">{totalLabel}</span>
          <span className="text-[20px] font-semibold tabular-nums text-ink">
            {totalValue}
          </span>
        </div>
      )}

      {children}

      {note && (
        <div className="mt-4 rounded-control bg-subtle p-3">
          <p className="text-[11px] font-semibold text-ink">{note.title}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-muted">
            {note.description}
          </p>
        </div>
      )}
    </div>
  );
}

/** Panneau latéral à fond teinté (ex. « Vos fournisseurs »). */
export function AccentCard({
  icon: Icon,
  title,
  children,
  className,
}: {
  icon?: React.ElementType;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-card border border-primary/15 bg-primary-soft p-5",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-4 w-4 text-primary" />}
        <h3 className="text-[15px] font-semibold text-primary">{title}</h3>
      </div>
      <div className="mt-3 space-y-2 text-[13px] text-ink">{children}</div>
    </div>
  );
}

export { Badge };