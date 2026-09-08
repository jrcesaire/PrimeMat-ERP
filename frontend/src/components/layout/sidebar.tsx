/**
 * Sidebar de navigation — liste les modules et leurs pages.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useCurrentCompany } from "@/hooks/useAuth";
import {
  LayoutDashboard,
  Package,
  Users,
  ShoppingCart,
  Warehouse,
  Truck,
  FileText,
  CreditCard,
  BarChart3,
  Settings,
  Tag,
  Store,
  Receipt,
  BookOpen,
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

export function Sidebar() {
  const pathname = usePathname();
  const { data: company } = useCurrentCompany();

  return (
    <div className="flex h-screen w-64 flex-col overflow-y-auto bg-gray-900 text-gray-100">
      <div className="border-b border-gray-800 p-4">
        <div className="flex items-center gap-3">
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
          <div className="min-w-0">
            <h1 className="truncate text-sm font-bold leading-tight text-white">
              {company?.name ?? "ERP Matériaux"}
            </h1>
            {company?.code && (
              <span className="text-xs text-gray-400">{company.code}</span>
            )}
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white",
              )}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
