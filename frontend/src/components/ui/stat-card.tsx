/**
 * Composant StatCard — indicateur clé du tableau de bord.
 *
 * Reprend la carte KPI de la maquette : libellé et pastille de couleur, valeur
 * principale, puis un écart (« ↗ 12,8 % ») accompagné d'une précision.
 */
import { cn, TONE_CLASSES, type Tone } from "@/lib/utils";

export function StatCard({
  label,
  value,
  /** Couleur de la pastille d'angle (repère visuel de la série). */
  dot = "primary",
  /** Variation affichée dans la pastille, ex. « ↗ 12,8 % ». */
  delta,
  deltaTone = "success",
  /** Précision à droite de la variation, ex. « vs mois précédent ». */
  hint,
  /** Valeur de repli quand la mesure n'est pas disponible. */
  placeholder = "—",
  className,
}: {
  label: string;
  value?: string | number | null;
  dot?: "primary" | "success" | "warning" | "danger";
  delta?: string;
  deltaTone?: Tone;
  hint?: string;
  placeholder?: string;
  className?: string;
}) {
  const dotClass = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-danger",
  }[dot];

  return (
    <div
      className={cn(
        "rounded-card border border-line bg-surface p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] text-muted">{label}</p>
        <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", dotClass)} />
      </div>
      <p className="mt-3 text-[26px] font-semibold leading-none tabular-nums text-ink">
        {value ?? placeholder}
      </p>
      {(delta || hint) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {delta && (
            <span
              className={cn(
                "inline-flex items-center rounded-chip px-2 py-0.5 text-[11px] font-medium",
                TONE_CLASSES[deltaTone],
              )}
            >
              {delta}
            </span>
          )}
          {hint && <span className="text-[11px] text-faint">{hint}</span>}
        </div>
      )}
    </div>
  );
}