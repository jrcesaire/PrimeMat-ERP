/**
 * Header du dashboard — bouton retour à l'écran précédent, utilisateur et menu.
 *
 * Le bouton retour est le premier élément en haut à gauche : il ramène à
 * l'écran précédent (`router.back()`). Quand il n'y a aucun écran précédent
 * dans l'application (accès direct par lien partagé ou nouvel onglet), il se
 * replie sur le lanceur d'applications.
 */
"use client";

import { useEffect, useRef, useState } from "react";
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
import { User, LogOut, Settings, Bell, Paintbrush, ArrowLeft, LayoutGrid, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
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
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-3">
        {showSidebarToggle && (
          <Button
            variant="ghost"
            size="sm"
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
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Retour</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/")}
              title="Toutes les applications"
              aria-label="Toutes les applications"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
          </>
        )}
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span>{company?.name ?? "Entreprise"}</span>
          {company?.establishment && (
            <>
              <span>•</span>
              <span className="text-gray-500">{company.establishment}</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <ThemeToggle />
        <ThemeSelector />
        <Button variant="ghost" size="sm">
          <Bell className="h-4 w-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span>
                {user?.full_name ||
                  [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                  user?.email ||
                  "Utilisateur"}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
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
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
