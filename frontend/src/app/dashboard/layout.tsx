/**
 * Layout du dashboard — sidebar + header + contenu.
 *
 * Client component : gère l'état réduit/étendu de la sidebar
 * (persisté en localStorage).
 *
 * La sidebar n'est montée que sur le tableau de bord : dès qu'on entre dans un
 * module (toute autre page `/dashboard/...`), elle est totalement retirée du
 * DOM et le module occupe toute la largeur. La navigation entre modules passe
 * alors par le bouton « Retour » (écran précédent) et le raccourci lanceur
 * « Toutes les applications » du header.
 */
"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { subscribePosFocus } from "@/lib/pos-focus";

const SIDEBAR_KEY = "erp-sidebar-collapsed";
/** Page d'accueil du dashboard — seule page où la sidebar reste affichée. */
const DASHBOARD_HOME = "/dashboard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  // Mode focus caisse : la page POS masque sidebar + header pendant la vente.
  const [posFocus, setPosFocus] = useState(false);

  // Hors tableau de bord, on est dans un module : la sidebar est retirée
  // (le slash final éventuel est ignoré).
  const route = (pathname ?? "").replace(/\/+$/, "") || "/";
  const showSidebar = !posFocus && route === DASHBOARD_HOME;

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
    } catch {
      // localStorage indisponible — garde la sidebar étendue
    }
  }, []);

  useEffect(() => subscribePosFocus(setPosFocus), []);

  const toggleSidebar = () => {
    setCollapsed((prev) => {
      try {
        localStorage.setItem(SIDEBAR_KEY, prev ? "0" : "1");
      } catch {
        // ignore
      }
      return !prev;
    });
  };

  return (
    <div className="flex h-screen bg-subtle">
      {showSidebar && <Sidebar collapsed={collapsed} />}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!posFocus && (
          <Header
            showBackButton
            showSidebarToggle={showSidebar}
            sidebarCollapsed={collapsed}
            onToggleSidebar={toggleSidebar}
          />
        )}
        <main
          className={
            posFocus
              ? "min-h-0 flex-1 overflow-hidden"
              : "flex-1 overflow-y-auto bg-canvas px-6 py-8 lg:px-8"
          }
        >
          {posFocus ? (
            children
          ) : (
            // Conteneur centré de la maquette (1212 px), qui remplace l'ancien
            // rembourrage fixe `px-[150px]` — illisible sur petit écran.
            <div className="mx-auto w-full max-w-[1212px]">{children}</div>
          )}
        </main>
      </div>
    </div>
  );
}
