/**
 * Configuration Jest du frontend.
 *
 * S'appuie sur `next/jest`, qui fournit la transformation SWC (TS/TSX) et la
 * résolution des alias `@/*` depuis `tsconfig.json` — aucun `ts-jest` ni
 * `babel.config.js` supplémentaire n'est nécessaire.
 *
 * Environnement : `node`. Les suites actuelles testent de la logique pure
 * (formatage, store du mode immersif PoS, modèle de navigation). Pour tester
 * des composants React, installer `jest-environment-jsdom`,
 * `@testing-library/react` et `@testing-library/jest-dom`, puis passer
 * `testEnvironment` à `"jsdom"` et renseigner `setupFilesAfterEach`.
 */
const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const customJestConfig = {
  testEnvironment: "node",
  clearMocks: true,
  testMatch: ["<rootDir>/src/**/*.test.ts", "<rootDir>/src/**/*.test.tsx"],
  collectCoverageFrom: [
    "src/lib/**/*.{ts,tsx}",
    "!src/lib/**/*.test.{ts,tsx}",
  ],
  coverageDirectory: "coverage",
};

module.exports = createJestConfig(customJestConfig);
