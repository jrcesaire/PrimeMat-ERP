/**
 * Composant Badge — pastille d'état.
 *
 * Les variantes `success` / `warning` / `danger` / `info` / `neutral` reposent
 * sur les jetons sémantiques et s'adaptent donc au mode sombre.
 */
import { cn } from "@/lib/utils";
import { HTMLAttributes } from "react";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "warning"
  | "info"
  | "neutral";

const VARIANTS: Record<BadgeVariant, string> = {
  default: "border-transparent bg-ink text-surface",
  secondary: "border-transparent bg-subtle text-muted",
  destructive: "border-transparent bg-danger text-white",
  outline: "border-line text-muted",
  success: "border-transparent bg-success-soft text-success",
  warning: "border-transparent bg-warning-soft text-warning",
  info: "border-transparent bg-primary-soft text-primary",
  neutral: "border-transparent bg-subtle text-muted",
};

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-chip border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}