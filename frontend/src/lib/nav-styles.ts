/**
 * Styles partagés des rails de navigation.
 *
 * Le rail du tableau de bord (`components/layout/sidebar.tsx`) et celui des
 * Paramètres (`components/settings/settings-sidebar.tsx`) doivent être
 * **visuellement identiques**. Ces constantes sont leur seule définition de
 * classes : les faire diverger devient impossible.
 */

/** Ligne d'entrée : une entrée = un lien (+ un chevron facultatif). */
export const NAV_ENTRY_ROW = "flex items-center rounded-control transition-colors";

/** Entrée de la page courante (ou d'une de ses sous-pages). */
export const NAV_ENTRY_ACTIVE = "bg-primary-soft text-primary";

/** Entrée au repos. */
export const NAV_ENTRY_IDLE = "text-muted hover:bg-subtle hover:text-ink";

/** Lien d'une entrée (occupe la ligne, icône + libellé). */
export const NAV_ENTRY_LINK =
  "flex flex-1 items-center gap-3 px-3 py-2 text-[11px] font-medium";

/** Icône d'une entrée. */
export const NAV_ENTRY_ICON = "h-[18px] w-[18px] shrink-0";

/** Intitulé de groupe (capitales discrètes). */
export const NAV_GROUP_LABEL =
  "px-3 pb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-faint";
