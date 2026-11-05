/**
 * Sidebar de navigation — liste les modules et leurs pages.
 *
 * Design « GEA ERP » : fond blanc bordé, emblème coloré, carte « Organisation »,
 * puis les modules **groupés par sections** (Espace de travail, Gestion
 * commerciale, Finances). Les modules riches conservent leur **sous-menu
 * dépliable** : le chevron est un contrôle distinct du lien (deux cibles de
 * clic), et plusieurs sous-menus peuvent rester ouverts à la fois.
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useCurrentCompany, useCurrentUser, usePermission } from "@/hooks/useAuth";
import { useSettingsNav } from "@/components/settings/settings-nav";
import { ChevronDown, Store } from "lucide-react";
import {
  NAV_ITEMS,
  NAV_SECTIONS,
  isNavGroup,
  visibleNavModules,
  type NavChild,
} from "@/lib/nav-config";
import { NavSubmenu } from "@/components/layout/nav-submenu";

/** Vrai si l'un des liens du sous-menu mène à la route courante. */
function containsRoute(items: NavChild[], route: string): boolean {
  return items.some((child) =>
    isNavGroup(child) ? containsRoute(child.items, route) : child.href === route,
  );
}

export function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname();
  const { data: company } = useCurrentCompany();
  // Sections accessibles du module Paramètres (sous-menu dépliable).
  const settingsNav = useSettingsNav();
  // Sous-menus filtrés par permission : une entrée n'est proposée que si
  // l'utilisateur détient le droit exigé par la page (cf. `lib/nav-config`).
  const { data: currentUser } = useCurrentUser();
  const can = usePermission();
  // Profil pas encore chargé (premier rendu / SSR) : aucun filtrage, pour
  // éviter un clignotement des sous-menus.
  const filterReady = Boolean(currentUser);
  const isAllowed = (permission?: string) =>
    !permission || !filterReady || can(permission);
  // Entrées dont le sous-menu est déplié (plusieurs peuvent l'être à la fois).
  const [openSections, setOpenSections] = useState<string[]>([]);

  const route = (pathname ?? "").replace(/\/+$/, "") || "/";

  // À l'arrivée sur une page d'un module, son sous-menu s'ouvre automatiquement ;
  // l'utilisateur peut ensuite le replier (la flèche est un contrôle distinct du
  // lien, elle ne navigue pas).
  useEffect(() => {
    const opened = NAV_ITEMS.filter(
      (item) =>
        item.children &&
        (route === item.href || containsRoute(item.children, route)),
    ).map((item) => item.href);
    if (opened.length === 0) return;
    setOpenSections((prev) => Array.from(new Set([...prev, ...opened])));
  }, [route]);

  const toggleSection = (href: string) =>
    setOpenSections((prev) =>
      prev.includes(href) ? prev.filter((h) => h !== href) : [...prev, href],
    );

  /** « Tableau de bord » ne doit pas rester actif sur les autres pages. */
  const isRouteActive = (href: string) =>
    href === "/dashboard"
      ? route === "/dashboard"
      : route === href || route.startsWith(`${href}/`);

  // Modules affichés : `visibleNavModules` retire ceux dont la page d'accueil
  // est interdite, sauf s'il reste une page accessible dans leur sous-menu (un
  // vendeur garde ainsi « Achats » pour « Besoins (ventes) » sans
  // `purchase:view`). Les sections de « Paramètres » viennent de
  // `useSettingsNav` (déjà filtrées par permission).
  const modules = visibleNavModules(
    isAllowed,
    settingsNav.map((section) => ({ label: section.label, href: section.href })),
  );

  // Répartition par section, dans l'ordre de `NAV_SECTIONS`. Les modules sans
  // section (Reporting, Paramètres) sont affichés seuls, après les groupes.
  const { groups, standalone } = useMemo(() => {
    const byKey = NAV_SECTIONS.map((section) => ({
      ...section,
      modules: [] as typeof modules,
    }));
    const orphans: typeof modules = [];
    for (const entry of modules) {
      const group = entry.item.section
        ? byKey.find((g) => g.key === entry.item.section)
        : undefined;
      if (group) group.modules.push(entry);
      else orphans.push(entry);
    }
    return {
      groups: byKey.filter((g) => g.modules.length > 0),
      standalone: orphans,
    };
  }, [modules]);

  /** Une entrée de navigation (module) — lien + chevron facultatif. */
  const renderEntry = ({
    item,
    children: subItems,
  }: (typeof modules)[number]) => {
    const isActive = isRouteActive(item.href);
    // Un module dont toutes les pages sont interdites n'a pas de chevron.
    const hasSub = subItems.length > 0;
    const subExpanded = openSections.includes(item.href);
    return (
      <div key={item.href}>
        {/* Ligne du menu : le lien navigue, la flèche déplie (deux cibles
            de clic distinctes). */}
        <div
          className={cn(
            "flex items-center rounded-control transition-colors",
            isActive
              ? "bg-primary-soft text-primary"
              : "text-muted hover:bg-subtle hover:text-ink",
          )}
        >
          <Link
            href={item.href}
            title={item.label}
            aria-label={item.label}
            className={cn(
              "flex flex-1 items-center gap-3 px-3 py-2 text-[11px] font-medium",
              collapsed && "justify-center px-0",
            )}
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" />
            {!collapsed && <span className="truncate">{item.label}</span>}
          </Link>

          {!collapsed && hasSub && (
            <button
              type="button"
              onClick={() => toggleSection(item.href)}
              aria-expanded={subExpanded}
              aria-label={
                subExpanded
                  ? `Replier le menu ${item.label}`
                  : `Déplier le menu ${item.label}`
              }
              title={subExpanded ? "Replier" : "Déplier"}
              className={cn(
                "mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-chip transition-colors",
                isActive
                  ? "hover:bg-primary/10"
                  : "text-faint hover:bg-subtle hover:text-ink",
              )}
            >
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform",
                  subExpanded && "rotate-180",
                )}
              />
            </button>
          )}
        </div>

        {!collapsed && hasSub && (
          <NavSubmenu items={subItems} open={subExpanded} pathname={pathname} />
        )}
      </div>
    );
  };

  return (
    <div
      className={cn(
        "flex h-screen shrink-0 flex-col border-r border-line bg-surface transition-all duration-200",
        collapsed ? "w-16" : "w-[228px]",
      )}
    >
      {/* Emblème + nom de l'application */}
      <div className={cn("px-4 pt-5", collapsed && "px-2")}>
        <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
          {company?.logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={company.logo}
              alt={`Logo ${company.name}`}
              className="h-8 w-8 shrink-0 rounded-[9px] bg-surface object-contain"
            />
          ) : (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[9px] bg-primary text-[12px] font-bold text-white">
              {(company?.name ?? "GEA").slice(0, 2).toUpperCase()}
            </div>
          )}
          {!collapsed && (
            <span className="truncate text-[17px] font-bold tracking-tight text-ink">
              {company?.name ?? "ERP Matériaux"}
            </span>
          )}
        </div>

        {/* Carte « Organisation » — nom + établissement courant */}
        {!collapsed && (
          <div className="mt-4 flex items-center gap-3 rounded-card bg-subtle px-3 py-2.5">
            <Store className="h-[18px] w-[18px] shrink-0 text-muted" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[11px] font-semibold text-ink">
                {company?.name ?? "Mon entreprise"}
              </p>
              <p className="truncate text-[10px] text-muted">
                {company?.establishment ?? "Espace entreprise"}
              </p>
            </div>
          </div>
        )}
      </div>
      {/* Navigation groupée par sections */}
      <nav
        className={cn(
          "flex-1 space-y-4 overflow-y-auto py-4",
          collapsed ? "px-2" : "px-3",
        )}
      >
        {groups.map((group) => (
          <div key={group.key} className="space-y-0.5">
            {!collapsed && (
              <p className="px-3 pb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-faint">
                {group.label}
              </p>
            )}
            {group.modules.map(renderEntry)}
          </div>
        ))}

        {standalone.length > 0 && (
          <div className="space-y-0.5 border-t border-line pt-3">
            {standalone.map(renderEntry)}
          </div>
        )}
      </nav>

      {!collapsed && (
        <div className="border-t border-line px-4 py-3 text-[9px] text-faint">
          {company?.name ?? "ERP"} · Gestion multimodulaire
        </div>
      )}
    </div>
  );
}
