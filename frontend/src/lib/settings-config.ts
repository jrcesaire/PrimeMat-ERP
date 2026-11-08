/**
 * Modèle de navigation des Paramètres — source unique de vérité.
 *
 * Deux niveaux :
 * 1. **Application** : les réglages transverses (Général, Documents, Catégories,
 *    Modules, Utilisateurs), rendus par `SettingsScreen` ;
 * 2. **Par module** : chaque application du lanceur (`APP_TILES`) devient un
 *    groupe qui accueille **ses** réglages. Un module sans réglage reste listé
 *    (« Aucun paramètre pour l'instant ») : l'emplacement est réservé, on sait
 *    où ranger les prochains écrans au lieu d'en inventer un nouveau.
 *
 * Le rail (`components/settings/settings-sidebar.tsx`) filtre ces entrées par
 * permission et par module actif, avec les mêmes règles que la sidebar du
 * tableau de bord.
 */
import {
  BookOpen,
  FileText,
  FolderTree,
  Plug,
  Settings as SettingsIcon,
  Store,
  Users,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import { APP_TILES } from "@/lib/module-registry";

export interface SettingsLink {
  key: string;
  label: string;
  /** Phrase affichée en infobulle (et réutilisable en description d'écran). */
  description: string;
  href: string;
  icon: LucideIcon;
  /** Une seule de ces permissions suffit (aucune = ouvert à tous). */
  permissions?: string[];
  /** Réservé au superadministrateur (ex. activation des modules). */
  superuserOnly?: boolean;
}

export interface SettingsGroup {
  key: string;
  label: string;
  icon: LucideIcon;
  /** Module backend dont dépend le groupe (`undefined` = toujours affiché). */
  module?: string;
  links: SettingsLink[];
}

/** Réglages transverses de l'application — toutes les entrées sont des écrans. */
export const SETTINGS_APP_GROUP: SettingsGroup = {
  key: "application",
  label: "Application",
  icon: SettingsIcon,
  links: [
    {
      key: "general",
      label: "Général",
      description: "Configuration de l'application et de l'entreprise",
      href: "/dashboard/settings/general",
      icon: SettingsIcon,
    },
    {
      key: "documents",
      label: "Documents",
      description: "Nomenclature des pièces, filigrane et conditions de vente",
      href: "/dashboard/settings/documents",
      icon: FileText,
    },
    {
      key: "categories",
      label: "Catégories",
      description: "Familles et sous-familles du catalogue",
      href: "/dashboard/settings/categories",
      icon: FolderTree,
      permissions: ["category:view"],
    },
    {
      key: "modules",
      label: "Modules",
      description: "Activation et désactivation des modules métier",
      href: "/dashboard/settings/modules",
      icon: Plug,
      superuserOnly: true,
    },
    {
      key: "users",
      label: "Utilisateurs",
      description: "Comptes utilisateurs, rôles et droits d'accès",
      href: "/dashboard/settings/users",
      icon: Users,
      permissions: ["user:view", "user:create"],
    },
  ],
};

/**
 * Réglages rattachés à une application du lanceur, par **clé de tuile**
 * (`APP_TILES[].key`). Les clés absentes n'ont simplement pas encore de réglage.
 */
export const SETTINGS_MODULE_LINKS: Record<string, SettingsLink[]> = {
  accounting: [
    {
      key: "accounting-assistant",
      label: "Assistant de configuration",
      description:
        "Référentiel comptable, exercice, régime fiscal et mentions légales",
      href: "/dashboard/settings/comptabilite/assistant",
      icon: Wand2,
      permissions: ["account:edit"],
    },
    {
      key: "accounting-settings",
      label: "Paramètres comptables",
      description: "Référentiel du plan comptable de l'entreprise",
      href: "/dashboard/settings/comptabilite/parametres",
      icon: BookOpen,
      permissions: ["account:view"],
    },
  ],
  pos: [
    {
      key: "pos-settings",
      label: "Réglages du point de vente",
      description:
        "Clôture de caisse, heure-valeur comptable et QR code des tickets",
      // Écran immersif du PoS (PRD §4.2.1) : il masque sidebar et header, d'où
      // sa route d'origine. Il est listé ici pour rester découvrable depuis les
      // Paramètres sans dupliquer la navigation.
      href: "/dashboard/sales/pos/reglages",
      icon: Store,
      permissions: ["pos:edit"],
    },
  ],
};

/** Un groupe par application du lanceur, dans l'ordre du lanceur. */
export const SETTINGS_MODULE_GROUPS: SettingsGroup[] = APP_TILES.filter(
  (tile) => !tile.always,
).map((tile) => ({
  key: tile.key,
  label: tile.label,
  icon: tile.icon,
  module: tile.module,
  links: SETTINGS_MODULE_LINKS[tile.key] ?? [],
}));

/** Le rail complet, dans l'ordre d'affichage. */
export const SETTINGS_GROUPS: SettingsGroup[] = [
  SETTINGS_APP_GROUP,
  ...SETTINGS_MODULE_GROUPS,
];

/** Toutes les routes de paramètres déclarées (dédupliquées, ordre conservé). */
export const SETTINGS_GROUP_HREFS: string[] = [
  ...new Set(SETTINGS_GROUPS.flatMap((group) => group.links.map((l) => l.href))),
];

/** Contexte d'autorisation du profil connecté. */
export interface SettingsAuthContext {
  isSuperuser: boolean;
  permissions: string[];
}

/**
 * Une entrée est-elle visible pour ce profil ?
 *
 * Le superadministrateur voit tout ; sinon la permission exigée doit figurer
 * dans ses droits (plusieurs permissions = l'une suffit).
 */
export function isSettingsLinkAllowed(
  link: SettingsLink,
  ctx: SettingsAuthContext,
): boolean {
  if (link.superuserOnly) return ctx.isSuperuser;
  if (ctx.isSuperuser) return true;
  if (!link.permissions || link.permissions.length === 0) return true;
  return link.permissions.some((permission) =>
    ctx.permissions.includes(permission),
  );
}
