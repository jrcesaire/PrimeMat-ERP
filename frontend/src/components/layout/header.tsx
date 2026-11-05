/**
 * Header du dashboard — bouton retour à l'écran précédent, utilisateur et menu.
 *
 * Le bouton retour est le premier élément en haut à gauche : il ramène à
 * l'écran précédent (`router.back()`). Quand il n'y a aucun écran précédent
 * dans l'application (accès direct par lien partagé ou nouvel onglet), il se
 * replie sur le lanceur d'applications.
 */
"use client";

import { useEffect, useMemo, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { User, LogOut, Settings, Bell, ArrowLeft, LayoutGrid, PanelLeftClose, PanelLeftOpen, Store } from "lucide-react";
import { NAV_ITEMS, isNavGroup } from "@/lib/nav-config";
import { GlobalSearch } from "@/components/layout/global-search";
import { ThemeSelector } from "@/components/dashboard/ThemeSelector";
import { ThemeToggle } from "@/components/dashboard/ThemeToggle";
import { useCurrentCompany } from "@/hooks/useAuth";

/** Écran de repli quand il n'y a aucun écran précédent dans l'application. */
const FALLBACK_ROUTE = "/";

export function Header({
  title = "Tableau de bord",
  showBackButton = false,
  showSidebarToggle = false,
  sidebarCollapsed = false,
  onToggleSidebar,
}: {
  title?: string;
  showBackButton?: boolean;
  showSidebarToggle?: boolean;
  sidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const { data: company } = useCurrentCompany();
  const logoutMutation = useLogout();

  // Fil d'Ariane : libellé du module (ou de la sous-page) correspondant à la
  // route courante, déduit de `nav-config` (source unique de vérité).
  const currentLabel = useMemo(() => {
    const route = (pathname ?? "").replace(/\/+$/, "") || "/";
    if (route === "/") return "Applications";
    const navItem = NAV_ITEMS.find(
      (item) => route === item.href || route.startsWith(`${item.href}/`),
    );
    if (!navItem) return title;
    const leaves = (navItem.children ?? []).flatMap((child) =>
      isNavGroup(child) ? child.items : [child],
    );
    return leaves.find((leaf) => leaf.href === route)?.label ?? navItem.label;
  }, [pathname, title]);

  /** Nom affiché dans le menu du compte. */
  const userName =
    user?.full_name ||
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
    user?.email ||
    "Utilisateur";

  // Navigations effectuées DANS l'application depuis l'affichage de ce header.
  // Distingue un vrai « écran précédent » d'un accès direct (lien partagé,
  // nouvel onglet) derrière lequel il n'y a rien à retrouver.
  const inAppDepth = useRef(0);
  const previousPathname = useRef<string | null>(null);

  useEffect(() => {
    if (
      previousPathname.current !== null &&
      previousPathname.current !== pathname
    ) {
      inAppDepth.current += 1;
    }
    previousPathname.current = pathname;
  }, [pathname]);

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
  };

  /** Retour à l'écran précédent — repli sur le lanceur si aucun historique. */
  const handleBack = () => {
    if (inAppDepth.current === 0) {
      router.push(FALLBACK_ROUTE);
      return;
    }
    router.back();
  };

  return (
    <header className="flex h-20 shrink-0 items-center gap-4 border-b border-line bg-surface px-6">
      {/* Gauche : bascules, identité de l'entreprise et fil d'Ariane */}
      <div className="flex min-w-0 items-center gap-3">
        {showSidebarToggle && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            title={sidebarCollapsed ? "Afficher le menu latéral" : "Réduire le menu latéral"}
            aria-label={sidebarCollapsed ? "Afficher le menu latéral" : "Réduire le menu latéral"}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </Button>
        )}
        {showBackButton && (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={handleBack}
              title="Retour à l'écran précédent"
              aria-label="Retour à l'écran précédent"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Retour</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push("/")}
              title="Toutes les applications"
              aria-label="Toutes les applications"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
          </>
        )}

        <div className="hidden min-w-0 md:block">
          <p className="truncate text-[13px] font-semibold leading-tight text-ink">
            {company?.name ?? "Entreprise"}
          </p>
          <p className="truncate text-[11px] leading-tight text-muted">
            {company?.establishment ?? "Espace entreprise"}
          </p>
        </div>

        <span className="hidden text-[13px] text-faint md:inline">/</span>
        <h2 className="truncate text-[13px] font-semibold text-ink">
          {currentLabel}
        </h2>
      </div>

      {/* Centre : recherche globale (⌘ K) */}
      <div className="mx-auto hidden w-full max-w-[312px] lg:block">
        <GlobalSearch />
      </div>

      {/* Droite : thème, notifications, compte et site actif */}
      <div className="flex shrink-0 items-center gap-2">
        <ThemeToggle />
        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
        </Button>

        <div className="mx-1 hidden h-8 w-px bg-line sm:block" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="h-auto flex-col items-start gap-0 px-2 py-1 text-left"
            >
              <span className="text-[13px] font-semibold leading-tight text-ink">
                {userName}
              </span>
              <span className="text-[11px] leading-tight text-muted">
                {user?.is_superuser ? "Superadministrateur" : "Utilisateur"}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Mon compte</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
              <User className="mr-2 h-4 w-4" />
              Profil
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
              <Settings className="mr-2 h-4 w-4" />
              Paramètres
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {/* La palette de couleurs est réglée depuis le menu du compte. */}
            <div className="px-2 py-1.5">
              <ThemeSelector />
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="hidden items-center gap-2 rounded-control bg-primary-soft px-3 py-1.5 lg:flex">
          <Store className="h-4 w-4 text-primary" />
          <span className="max-w-[140px] truncate text-[12px] font-medium text-primary">
            {company?.establishment ?? company?.name ?? "Site"}
          </span>
        </div>
      </div>
    </header>
  );
}
