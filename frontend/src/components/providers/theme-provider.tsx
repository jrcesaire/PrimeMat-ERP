/**
 * Theme Provider — gestion du thème couleur personnalisable.
 *
 * Permet de changer les couleurs primaires/secondaires de l'application
 * via le LocalStorage et le context React.
 */
"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = {
  primary: string;
  secondary: string;
  accent: string;
};

type ThemeContextType = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const defaultTheme: Theme = {
  primary: "221 83% 53%", // bleu Material
  secondary: "142 48% 47%", // vert
  accent: "34 100% 50%", // orange
};

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
} | undefined>(undefined);

const THEME_KEY = "erp-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);

  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.primary && parsed.secondary) {
          setThemeState({ ...defaultTheme, ...parsed });
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  const setTheme = (newTheme: Theme) => {
    const merged = { ...defaultTheme, ...newTheme };
    setThemeState(merged);
    localStorage.setItem(THEME_KEY, JSON.stringify(merged));

    // Apply CSS variables
    const root = document.documentElement;
    root.style.setProperty("--primary-hue", merged.primary);
    root.style.setProperty("--secondary-hue", merged.secondary);
    root.style.setProperty("--accent-hue", merged.accent);
  };

  useEffect(() => {
    // Apply saved theme on mount
    const root = document.documentElement;
    root.style.setProperty("--primary-hue", theme.primary);
    root.style.setProperty("--secondary-hue", theme.secondary);
    root.style.setProperty("--accent-hue", theme.accent);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}

// Available theme presets
export const themePresets: Record<string, Theme> = {
  default: {
    primary: "221 83% 53%",
    secondary: "142 48% 47%",
    accent: "34 100% 50%",
  },
  ocean: {
    primary: "210 100% 50%",
    secondary: "197 73% 45%",
    accent: "32 100% 50%",
  },
  forest: {
    primary: "142 48% 47%",
    secondary: "210 50% 50%",
    accent: "34 100% 50%",
  },
  sunset: {
    primary: "30 95% 55%",
    secondary: "0 85% 60%",
    accent: "34 100% 50%",
  },
  royal: {
    primary: "255 73% 48%",
    secondary: "270 70% 55%",
    accent: "34 100% 50%",
  },
};
