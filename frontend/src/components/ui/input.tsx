/**
 * Composant Input — champ de saisie.
 *
 * Design « GEA ERP » : rayon 7 px, bordure neutre, anneau de focus primaire.
 * Les couleurs de focus suivent le thème personnalisable.
 */
import { cn } from "@/lib/utils";
import { forwardRef } from "react";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-control border border-line bg-surface px-3 py-2 text-[13px] text-ink placeholder:text-ghost focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";
