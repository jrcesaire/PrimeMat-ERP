/**
 * Définition du sous-menu « Paramètres ».
 *
 * Source unique de vérité, partagée par :
 * - la sidebar (`components/layout/sidebar.tsx`) qui déplie le sous-menu sous
 *   l'entrée « Paramètres » ;
 * - la navigation secondaire du layout `app/dashboard/settings/layout.tsx`.
 *
 * Chaque section correspond à une sous-route `/dashboard/settings/<section>`
 * rendue par `SettingsScreen` (`components/settings/settings-screen.tsx`).
 */
"use client";

import { useCurrentUser } from "@/hooks/useAuth";
import type { SettingsSection } from "@/components/settings/settings-screen";

export interface SettingsNavItem {
  section: SettingsSection;
  label: string;
  href: string;
}

export const SETTINGS_NAV: SettingsNavItem[] = [
  { section: "general", label: "Général", href: "/dashboard/settings/general" },
  { section: "documents", label: "Documents", href: "/dashboard/settings/documents" },
  { section: "categories", label: "Catégories", href: "/dashboard/settings/categories" },
  { section: "modules", label: "Modules", href: "/dashboard/settings/modules" },
  { section: "users", label: "Utilisateurs", href: "/dashboard/settings/users" },
];

/**
 * Sections accessibles au profil connecté.
 *
 * Les règles reprennent celles de `SettingsScreen` : les modules sont réservés
 * au superadministrateur, les catégories et les utilisateurs aux profils qui
 * détiennent les permissions correspondantes. Les autres sections sont
 * ouvertes à tous.
 */
export function useSettingsNav(): SettingsNavItem[] {
  const { data: currentUser } = useCurrentUser();
  // Profil pas encore chargé (premier rendu / SSR) : on n'applique aucun filtre
  // pour éviter un clignotement du sous-menu.
  if (!currentUser) return SETTINGS_NAV;
  const isSuperuser = currentUser.is_superuser === true;
  if (isSuperuser) return SETTINGS_NAV;

  const permissions = currentUser.permissions ?? [];
  const allowed = new Set<SettingsSection>(["general", "documents"]);
  if (permissions.includes("category:view")) allowed.add("categories");
  if (permissions.includes("user:view") || permissions.includes("user:create")) {
    allowed.add("users");
  }
  return SETTINGS_NAV.filter((item) => allowed.has(item.section));
}
