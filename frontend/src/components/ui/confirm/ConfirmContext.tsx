/**
 * Contexte partagé du système de confirmation (séparé du provider
 * pour respecter la règle React 19 : pas d'export non-composant
 * depuis un fichier marqué "use client" avec composants).
 */
"use client";

import { createContext } from "react";

import type { ConfirmFn } from "./types";

export const ConfirmContext = createContext<ConfirmFn | null>(null);
