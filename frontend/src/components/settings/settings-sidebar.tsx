/**
 * Rail de navigation des Paramètres.
 *
 * Même design que la sidebar du tableau de bord (`components/layout/sidebar.tsx`,
 * styles partagés dans `lib/nav-styles.ts`) : emblème, entrées `rounded-control`,
 * groupes en capitales discrètes.
 *
 * Contenu : le groupe « Application » (réglages transverses) puis **un groupe
 * par application du lanceur** qui possède réellement des réglages. Les
 * entrées sont filtrées par permission et par module actif ; un module sans
 * réglage n'est **pas listé** (il apparaîtra dès que ses paramètres existeront).
 *
 * Sous `lg`, le rail se replie en une rangée de chips horizontale.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCurrentCompany, useCurrentUser } from "@/hooks/useAuth";
import { useModuleStates } from "@/hooks/useModules";
import {
  isSettingsLinkAllowed,
  SETTINGS_APP_GROUP,
  SETTINGS_MODULE_GROUPS,
  type SettingsGroup,
  type SettingsLink,
} from "@/lib/settings-config";
import {
  NAV_ENTRY_ACTIVE,
  NAV_ENTRY_ICON,
  NAV_ENTRY_IDLE,
  NAV_ENTRY_LINK,
  NAV_ENTRY_ROW,
  NAV_GROUP_LABEL,
} from "@/lib/nav-styles";

/** Route courante, sans slash final. */
function normalize(pathname: string | null): string {
  return (pathname ?? "").replace(/\/+$/, "") || "/";
}

/** Vrai si `href` est la route courante ou l'une de ses sous-pages. */
function isLinkActive(route: string, href: string): boolean {
  return route === href || route.startsWith(`${href}/`);
}

export function SettingsSidebar() {
  const pathname = usePathname();
  const route = normalize(pathname);
  const { data: company } = useCurrentCompany();
  const { data: currentUser } = useCurrentUser();
  const { data: moduleStates } = useModuleStates();

  // Profil pas encore chargé (premier rendu / SSR) : aucun filtrage, pour
  // éviter un clignotement du rail.
  const filterReady = Boolean(currentUser);
  const allowed = (link: SettingsLink) =>
    !filterReady ||
    isSettingsLinkAllowed(link, {
      isSuperuser: currentUser?.is_superuser === true,
      permissions: currentUser?.permissions ?? [],
    });

  // Modules actifs — `null` tant que la liste n'est pas chargée : on montre
  // alors tous les groupes plutôt que de vider le rail.
  const activeModules = moduleStates
    ? new Set(
        moduleStates
          .filter((m) => m.is_active && m.status === "active")
          .map((m) => m.name),
      )
    : null;

  const groups: SettingsGroup[] = [
    SETTINGS_APP_GROUP,
    ...SETTINGS_MODULE_GROUPS,
  ]
    .filter(
      (group) => !group.module || !activeModules || activeModules.has(group.module),
    )
    .map((group) => ({ ...group, links: group.links.filter(allowed) }))
    // Un module sans aucun réglage accessible n'apparaît pas : la liste ne
    // montre que ce qui existe réellement.
    .filter((group) => group.links.length > 0);

  const flatLinks = groups.flatMap((group) => group.links);

  return (
    <div className="shrink-0">
      {/* Écran étroit : le rail vertical n'a pas la place, on le déplie en ligne. */}
      <nav className="flex flex-wrap gap-1 border-b border-line pb-3 lg:hidden">
        {flatLinks.map((link) => {
          const active = isLinkActive(route, link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              title={link.description}
              className={cn(
                "rounded-chip px-3 py-1.5 text-[12px] transition-colors",
                active
                  ? "bg-primary-soft font-medium text-primary"
                  : "text-muted hover:bg-subtle hover:text-ink",
              )}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Écran large : rail calqué sur la sidebar du tableau de bord. */}
      <aside className="hidden w-[228px] shrink-0 lg:block">
        <div className="sticky top-0 flex max-h-[calc(100vh-9rem)] flex-col overflow-y-auto border-r border-line pr-3">
          {/* Emblème + entreprise, comme la sidebar du tableau de bord. */}
          <div className="flex items-center gap-3 pb-4">
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
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-ink">
                Paramètres
              </p>
              <p className="truncate text-[10px] text-muted">
                {company?.name ?? "Mon entreprise"}
              </p>
            </div>
          </div>

          {/* Retour à l'accueil : les Paramètres ne sont pas un module isolé. */}
          <div className={cn(NAV_ENTRY_ROW, NAV_ENTRY_IDLE)}>
            <Link href="/dashboard" className={NAV_ENTRY_LINK}>
              <ArrowLeft className={NAV_ENTRY_ICON} />
              <span className="truncate">Tableau de bord</span>
            </Link>
          </div>

          <div className="mt-4 space-y-4">
            {groups.map((group) => (
              <div key={group.key} className="space-y-0.5">
                <p className={NAV_GROUP_LABEL}>{group.label}</p>

                {group.links.map((link) => {
                  const active = isLinkActive(route, link.href);
                  return (
                    <div
                      key={link.href}
                      className={cn(
                        NAV_ENTRY_ROW,
                        active ? NAV_ENTRY_ACTIVE : NAV_ENTRY_IDLE,
                      )}
                    >
                      <Link
                        href={link.href}
                        title={link.description}
                        aria-label={link.label}
                        className={NAV_ENTRY_LINK}
                      >
                        <link.icon className={NAV_ENTRY_ICON} />
                        <span className="truncate">{link.label}</span>
                      </Link>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
