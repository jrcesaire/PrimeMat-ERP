/**
 * Configuration Tailwind — jetons de design « GEA ERP ».
 *
 * Deux familles de couleurs :
 * 1. Thématiques (`primary`/`secondary`/`accent`) pilotées par des variables HSL
 *    que l'utilisateur peut changer (cf. `ThemeSelector`) ;
 * 2. Neutres sémantiques (`ink`, `muted`, `line`, `canvas`, `surface`…) définis
 *    dans `globals.css` et **redéfinis en mode sombre** : les composants écrits
 *    avec ces jetons s'adaptent donc automatiquement aux deux thèmes.
 *
 * Le design de la maquette est « flat » : aucune ombre portée, tout repose sur
 * des bordures de 1 px (`--line`).
 */
const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "hsl(var(--primary-hue) / <alpha-value>)",
        secondary: "hsl(var(--secondary-hue) / <alpha-value>)",
        accent: "hsl(var(--accent-hue) / <alpha-value>)",
        "primary-hover": "hsl(var(--primary-hue) / 0.85)",
        "primary-light": "hsl(var(--primary-hue) / 0.15)",
        "primary-dark": "hsl(var(--primary-hue) / 0.75)",
        "secondary-hover": "hsl(var(--secondary-hue) / 0.85)",
        "secondary-light": "hsl(var(--secondary-hue) / 0.15)",

        // --- Neutres sémantiques (clair / sombre via `globals.css`) ---
        ink: "hsl(var(--ink) / <alpha-value>)",
        muted: "hsl(var(--muted) / <alpha-value>)",
        faint: "hsl(var(--faint) / <alpha-value>)",
        ghost: "hsl(var(--ghost) / <alpha-value>)",
        line: "hsl(var(--line) / <alpha-value>)",
        canvas: "hsl(var(--canvas) / <alpha-value>)",
        surface: "hsl(var(--surface) / <alpha-value>)",
        subtle: "hsl(var(--subtle) / <alpha-value>)",
        /** Fond très clair de la couleur primaire (état actif, chips). */
        "primary-soft": "hsl(var(--primary-hue) / 0.10)",

        // --- États ---
        success: "hsl(var(--success) / <alpha-value>)",
        "success-soft": "hsl(var(--success-soft) / <alpha-value>)",
        warning: "hsl(var(--warning) / <alpha-value>)",
        "warning-soft": "hsl(var(--warning-soft) / <alpha-value>)",
        danger: "hsl(var(--danger) / <alpha-value>)",
        "danger-soft": "hsl(var(--danger-soft) / <alpha-value>)",
      },
      borderRadius: {
        /** Cartes et panneaux. */
        card: "10px",
        /** Champs, boutons et entrées de navigation. */
        control: "7px",
        /** Pastilles et chips. */
        chip: "5px",
      },
      fontFamily: {
        sans: ["var(--font-inter)", ...defaultTheme.fontFamily.sans],
      },
      boxShadow: {
        /** Bordure seule — remplace `shadow-sm` sur les cartes. */
        card: "0 0 0 1px hsl(var(--line))",
        /** Menus et popovers. */
        pop: "0 10px 30px -12px rgb(37 38 61 / 0.22)",
      },
    },
  },
  plugins: [],
};

