/**
 * Layout du dashboard — sidebar + header + contenu.
 *
 * Client component : gère l'état réduit/étendu de la sidebar
 * (persisté en localStorage).
 */
"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { subscribePosFocus } from "@/lib/pos-focus";

const SIDEBAR_KEY = "erp-sidebar-collapsed";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  // Mode focus caisse : la page POS masque sidebar + header pendant la vente.
  const [posFocus, setPosFocus] = useState(false);

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
    <div className="flex h-screen bg-gray-50">
      {!posFocus && <Sidebar collapsed={collapsed} />}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!posFocus && (
          <Header
            showBackButton
            showSidebarToggle
            sidebarCollapsed={collapsed}
            onToggleSidebar={toggleSidebar}
          />
        )}
        <main
          className={
            posFocus
              ? "min-h-0 flex-1 overflow-hidden p-4"
              : "flex-1 overflow-y-auto p-6"
          }
        >
          {children}
        </main>
      </div>
    </div>
  );
}
