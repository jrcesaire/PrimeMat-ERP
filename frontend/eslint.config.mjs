/**
 * Configuration ESLint (flat config) du frontend.
 *
 * Le projet est en ESLint 9 : `eslint.config.mjs` remplace `.eslintrc.json`.
 * On réutilise les règles officielles de Next.js (`next/core-web-vitals` +
 * `next/typescript`) via `FlatCompat`, qui sait lire les configurations
 * « legacy » exposées par `eslint-config-next`.
 */
import { dirname } from "path";
import { fileURLToPath } from "url";

import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "coverage/**",
      "next-env.d.ts",
      "**/*.config.js",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Les libellés d'interface sont en français : les apostrophes droites
      // et les guillemets typographiques sont volontaires.
      "react/no-unescaped-entities": "off",
      // --- Dette technique : règles rétrogradées en avertissements ---
      // Le projet passe pour la première fois sous ESLint : ~50 occurrences
      // historiques (`any` explicites, imports/variables inutilisés) restent à
      // résorber. Les laisser en « error » casserait la CI sans rapport avec
      // les développements en cours ; elles restent visibles en avertissement.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": "warn",
    },
  },
];

export default eslintConfig;
