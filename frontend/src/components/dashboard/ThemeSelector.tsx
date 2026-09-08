/**
 * Theme Selector — permet de changer le thème couleur de l'application.
 */
"use client";

import { useTheme, themePresets } from "@/components/providers/theme-provider";
import { Paintbrush } from "lucide-react";

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center gap-2">
      <Paintbrush className="h-4 w-4 text-gray-500" />
      <select
        value={Object.keys(themePresets).find(
          (key) =>
            themePresets[key].primary === theme.primary &&
            themePresets[key].secondary === theme.secondary,
        ) || "default"}
        onChange={(e) => setTheme(themePresets[e.target.value])}
        className="text-sm text-gray-700 bg-white border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="default">Bleu (défaut)</option>
        <option value="ocean">Océan</option>
        <option value="forest">Forêt</option>
        <option value="sunset">Coucher de soleil</option>
        <option value="royal">Royal</option>
      </select>
    </div>
  );
}
