/**
 * Section Modules principaux — accès aux modules clés du ERP.
 *
 * Modules : Ventes, Point de vente, Facturation, Contacts
 */
"use client";

import Link from "next/link";
import { ShoppingCart, Euro, FileText, Users } from "lucide-react";
import { Card } from "@/components/ui/card";

const mainModules = [
  {
    label: "Ventes",
    description: "Devis, commandes, factures",
    icon: ShoppingCart,
    href: "/dashboard/sales",
    color: "bg-blue-50",
    iconColor: "text-blue-600",
    stats: "12 devis aujourd'hui",
  },
  {
    label: "Point de vente",
    description: "Vente comptoir et caisse",
    icon: Euro,
    href: "/dashboard/pos",
    color: "bg-green-50",
    iconColor: "text-green-600",
    stats: "Ouvert",
  },
  {
    label: "Facturation",
    description: "Factures et paiements",
    icon: FileText,
    href: "/dashboard/invoicing",
    color: "bg-indigo-50",
    iconColor: "text-indigo-600",
    stats: "3 factures impayées",
  },
  {
    label: "Contacts",
    description: "Clients, fournisseurs, chantiers",
    icon: Users,
    href: "/dashboard/contacts",
    color: "bg-purple-50",
    iconColor: "text-purple-600",
    stats: "42 clients actifs",
  },
];

export function MainModulesSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Modules principaux</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {mainModules.map((module) => (
          <Link key={module.label} href={module.href}>
            <Card className="group cursor-pointer p-6 transition-all duration-200 hover:shadow-lg">
              <div className="flex items-start gap-3">
                <div className={`rounded-xl p-3 ${module.color}`}>
                  <module.icon className={`h-6 w-6 ${module.iconColor}`} />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900 group-hover:text-primary">{module.label}</h3>
                  <p className="text-sm text-gray-600">{module.description}</p>
                  <p className="mt-2 text-xs text-gray-500">{module.stats}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
