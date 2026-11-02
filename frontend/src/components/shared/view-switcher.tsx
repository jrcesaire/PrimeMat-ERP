/**
 * Sélecteur de vue d'un module à deux écrans (« Créer » / « Liste »).
 *
 * Reprend le style des onglets déjà utilisés dans les pages de module
 * (soulignement de l'onglet actif), pour rester cohérent d'un écran à l'autre.
 */
"use client";

import { cn } from "@/lib/utils";

export interface ViewSwitcherOption<T extends string> {
  key: T;
  label: string;
}

export function ViewSwitcher<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (value: T) => void;
  options: ViewSwitcherOption<T>[];
}) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-gray-200">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          onClick={() => onChange(option.key)}
          aria-current={value === option.key}
          className={cn(
            "px-4 py-2 text-sm font-medium transition-colors",
            value === option.key
              ? "border-b-2 border-gray-900 text-gray-900"
              : "text-gray-500 hover:text-gray-800",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
