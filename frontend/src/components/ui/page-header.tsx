/**
 * Composant PageHeader — en-tête standard d'un écran de module.
 *
 * Structure de la maquette : un sur-titre (« eyebrow ») coloré et en capitales,
 * le titre de la page, une phrase de contexte, puis les actions alignées à
 * droite. Utilisé en tête de chaque page pour homogénéiser les modules.
 */
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  className,
}: {
  /** Sur-titre en capitales (ex. « GESTION COMMERCIALE »). */
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-4",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-primary">
            {eyebrow}
          </p>
        )}
        <h1 className="mt-1 text-[28px] font-semibold leading-tight text-ink">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1 text-[13px] text-muted">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  );
}