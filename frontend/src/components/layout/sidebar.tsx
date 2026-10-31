/**
 * Sidebar de navigation — liste les modules et leurs pages.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useCurrentCompany } from "@/hooks/useAuth";
import { useSettingsNav } from "@/components/settings/settings-nav";
import {
  BarChart3,
  BookOpen,
  ChevronDown,
  CreditCard,
  FileText,
  LayoutDashboard,
  Package,
  Receipt,
  Settings,
  ShoppingCart,
  Store,
  Tag,
  Truck,
  Users,
  Warehouse,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard },
  { label: "Point de vente", href: "/dashboard/sales/pos", icon: Store },
  { label: "Catalogue", href: "/dashboard/catalogue", icon: Package },
  { label: "Clients", href: "/dashboard/contacts", icon: Users },
  { label: "Ventes", href: "/dashboard/sales", icon: ShoppingCart },
  { label: "Stock", href: "/dashboard/stock", icon: Warehouse },
  { label: "Achats", href: "/dashboard/purchases", icon: Tag },
  { label: "Livraison", href: "/dashboard/delivery", icon: Truck },
  { label: "Facturation", href: "/dashboard/invoicing", icon: FileText },
  { label: "Paiements", href: "/dashboard/payments", icon: CreditCard },
  { label: "Dépenses", href: "/dashboard/expenses", icon: Receipt },
  { label: "Comptabilité", href: "/dashboard/accounting", icon: BookOpen },
  { label: "Reporting", href: "/dashboard/reporting", icon: BarChart3 },
  { label: "Paramètres", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname();
  const { data: company } = useCurrentCompany();
  // Sections accessibles du module Paramètres (sous-menu dépliable).
  const settingsNav = useSettingsNav();
  // Le sous-menu se déplie dès qu'on entre dans la section Paramètres, mais
  // reste repliable par l'utilisateur : la flèche est un contrôle indépendant
  // du lien (elle ne navigue pas).
  const inSettings = pathname?.startsWith("/dashboard/settings") ?? false;
  const [settingsOpen, setSettingsOpen] = useState(inSettings);

  useEffect(() => {
    if (inSettings) setSettingsOpen(true);
  }, [inSettings]);

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
        {navItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          // L'entrée « Paramètres » déplie ses sections en sous-menu.
          const subItems =
            item.href === "/dashboard/settings" ? settingsNav : undefined;
          const subExpanded = settingsOpen && Boolean(subItems);
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

                {!collapsed && subItems && (
                  <button
                    type="button"
                    onClick={() => setSettingsOpen((open) => !open)}
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

              {!collapsed && subItems && settingsOpen && (
                <div className="mt-1 space-y-0.5">
                  {subItems.map((child) => {
                    const childActive = pathname === child.href;
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={cn(
                          "flex items-center rounded-md py-1.5 pl-10 pr-3 text-xs transition-colors",
                          childActive
                            ? "bg-gray-800 font-medium text-white"
                            : "text-gray-400 hover:bg-gray-800 hover:text-white",
                        )}
                      >
                        <span className="truncate">{child.label}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
