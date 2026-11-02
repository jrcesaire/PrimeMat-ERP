/**
 * Sidebar de navigation — liste les modules et leurs pages.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useCurrentCompany, useCurrentUser, usePermission } from "@/hooks/useAuth";
import { useSettingsNav } from "@/components/settings/settings-nav";
import { ChevronDown } from "lucide-react";
import {
  NAV_ITEMS,
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

  return (
    <div
      className={cn(
        "flex h-screen flex-col overflow-y-auto bg-gray-900 text-gray-100 transition-all duration-200",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className={cn("border-b border-gray-800 p-4", collapsed && "flex justify-center px-2")}>
        <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
          {company?.logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={company.logo}
              alt={`Logo ${company.name}`}
              className="h-10 w-10 shrink-0 rounded-md bg-white object-contain p-0.5"
            />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-bold text-white">
              {(company?.name ?? "GEA").slice(0, 2).toUpperCase()}
            </div>
          )}
          <div className={cn("min-w-0", collapsed && "hidden")}>
            <h1 className="truncate text-sm font-bold leading-tight text-white">
              {company?.name ?? "ERP Matériaux"}
            </h1>
            {company?.code && (
              <span className="text-xs text-gray-400">{company.code}</span>
            )}
          </div>
        </div>
      </div>
      <nav className={cn("flex-1 space-y-1 py-4", collapsed ? "px-2" : "px-2")}>
        {modules.map(({ item, children: subItems }) => {
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
                  "flex items-center rounded-md transition-colors",
                  isActive
                    ? "bg-primary text-white"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white",
                )}
              >
                <Link
                  href={item.href}
                  title={item.label}
                  aria-label={item.label}
                  className={cn(
                    "flex flex-1 items-center gap-3 px-3 py-2 text-sm",
                    collapsed && "justify-center px-0",
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
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
                      "mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
                      isActive
                        ? "hover:bg-black/10"
                        : "text-gray-400 hover:bg-gray-700 hover:text-white",
                    )}
                  >
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 transition-transform",
                        subExpanded && "rotate-180",
                      )}
                    />
                  </button>
                )}
              </div>

              {!collapsed && hasSub && (
                <NavSubmenu
                  items={subItems}
                  open={subExpanded}
                  pathname={pathname}
                />
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
