/**
 * Theme Toggle — interrupteur on/off du mode sombre.
 */
"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/providers/theme-provider";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const { mode, toggleMode } = useTheme();
  const isDark = mode === "dark";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      onClick={toggleMode}
      title={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
      className={cn(
        "relative inline-flex h-7 w-13 shrink-0 items-center rounded-full transition-colors duration-200",
        isDark ? "bg-slate-600" : "bg-gray-200"
      )}
      style={{ width: 52 }}
    >
      <span
        className={cn(
          "flex h-5.5 w-5.5 items-center justify-center rounded-full bg-white shadow transition-transform duration-200",
          isDark ? "translate-x-7" : "translate-x-1"
        )}
        style={{ height: 22, width: 22 }}
      >
        {isDark ? (
          <Moon className="h-3.5 w-3.5 text-slate-700" />
        ) : (
          <Sun className="h-3.5 w-3.5 text-amber-500" />
        )}
      </span>
    </button>
  );
}
