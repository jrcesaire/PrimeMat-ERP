/**
 * Section Modules principaux — accès aux modules clés du ERP.
 *
 * Modules : Ventes, Point de vente, Facturation, Contacts
 */
"use client";

import Link from "next/link";
import { ShoppingCart, Euro, FileText, Users } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useMemo } from "react";
import { useQuotes, useOrders } from "@/hooks/useSales";
import { useInvoices } from "@/hooks/useOperations";
import { usePartners } from "@/hooks/useCRM";
import { formatNumber } from "@/lib/utils";

type MainModule = {
  key: string;
  label: string;
  description: string;
  icon: typeof ShoppingCart;
  href: string;
  color: string;
  iconColor: string;
  staticStats?: string;
};

const mainModules: MainModule[] = [
  {
    key: "sales",
    label: "Ventes",
    description: "Devis, commandes, factures",
    icon: ShoppingCart,
    href: "/dashboard/sales",
    color: "bg-blue-50",
    iconColor: "text-blue-600",
  },
  {
    key: "pos",
    label: "Point de vente",
    description: "Vente comptoir et caisse",
    icon: Euro,
    href: "/dashboard/sales/pos",
    color: "bg-green-50",
    iconColor: "text-green-600",
    staticStats: "Ouvert",
  },
  {
    key: "invoicing",
    label: "Facturation",
    description: "Factures et paiements",
    icon: FileText,
    href: "/dashboard/invoicing",
    color: "bg-indigo-50",
    iconColor: "text-indigo-600",
  },
  {
    key: "contacts",
    label: "Contacts",
    description: "Clients, fournisseurs, chantiers",
    icon: Users,
    href: "/dashboard/contacts",
    color: "bg-purple-50",
    iconColor: "text-purple-600",
  },
];

export function MainModulesSection() {
  const { data: quotes = [] } = useQuotes();
  const { data: orders = [] } = useOrders();
  const { data: invoices = [] } = useInvoices();
  const { data: partners = [] } = usePartners();

  const statsByKey = useMemo<Record<string, string>>(() => {
    const draftQuotes = quotes.filter((q) => q.status === "draft").length;
    const unpaid = invoices.filter(
      (i) => i.status !== "paid" && i.status !== "cancelled"
    ).length;
    const actives = partners.filter((p) => (p as { is_active?: boolean }).is_active !== false).length;
    return {
      sales:
        quotes.length === 0 && orders.length === 0
          ? "Aucun devis pour le moment"
          : `${formatNumber(draftQuotes)} devis en brouillon`,
      pos: "Ouvert",
      invoicing:
        invoices.length === 0
          ? "Aucune facture pour le moment"
          : unpaid === 0
            ? "Toutes les factures sont soldées"
            : `${formatNumber(unpaid)} facture${unpaid > 1 ? "s" : ""} à recouvrer`,
      contacts:
        partners.length === 0
          ? "Aucun contact pour le moment"
          : `${formatNumber(actives)} contact${actives > 1 ? "s" : ""} enregistré${actives > 1 ? "s" : ""}`,
    };
  }, [quotes, orders, invoices, partners]);

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Modules principaux</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {mainModules.map((module) => (
          <Link key={module.key} href={module.href}>
            <Card className="group cursor-pointer p-6 transition-all duration-200 hover:shadow-lg">
              <div className="flex items-start gap-3">
                <div className={`rounded-xl p-3 ${module.color}`}>
                  <module.icon className={`h-6 w-6 ${module.iconColor}`} />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 group-hover:text-primary">{module.label}</h3>
                  <p className="text-sm text-gray-600">{module.description}</p>
                  <p className="mt-2 text-xs text-gray-500">
                    {module.staticStats ?? statsByKey[module.key]}
                  </p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
