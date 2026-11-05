/**
 * Composant ProgressBar — barre de répartition (maquette : « Vos canaux de
 * vente »). Affiche un libellé, une valeur et un pourcentage alignés, puis la
 * barre colorée.
 */
import { cn } from "@/lib/utils";

export function ProgressBar({
  label,
  value,
  percent,
  tone = "primary",
  className,
}: {
  label: string;
  /** Valeur affichée à droite du libellé (déjà formatée). */
  value: string;
  /** Part remplie, entre 0 et 100. */
  percent: number;
  tone?: "primary" | "success" | "warning" | "muted";
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, percent));
  const fill = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    muted: "bg-ghost",
  }[tone];

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] font-medium text-ink">{label}</span>
        <span className="flex items-baseline gap-3">
          <span className="text-[13px] font-semibold tabular-nums text-ink">
            {value}
          </span>
          <span className="w-10 text-right text-[12px] tabular-nums text-faint">
            {Math.round(clamped)} %
          </span>
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
        <div
          className={cn("h-full rounded-full transition-[width]", fill)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}