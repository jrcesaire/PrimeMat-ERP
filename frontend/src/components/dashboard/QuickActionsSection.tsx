/**
 * Section Actions rapides — accès direct aux fonctions courantes.
 *
 * De prime abord : devis, vente comptoir, dépense, contact.
 */
"use client";

import Link from "next/link";
import { FileText, ShoppingCart, Receipt, Users } from "lucide-react";
import { Card } from "@/components/ui/card";

const quickActions = [
  {
    label: "Nouveau devis",
    description: "Créer un devis client",
    icon: FileText,
    href: "/dashboard/sales/quotes/new",
    color: "bg-blue-50 text-blue-600",
    iconColor: "text-blue-600",
  },
  {
    label: "Vente comptoir",
    description: "Vente rapide comptoir",
    icon: ShoppingCart,
    href: "/dashboard/sales/pos",
    color: "bg-green-50 text-green-600",
    iconColor: "text-green-600",
  },
  {
    label: "Enregistrer une dépense",
    description: "Ajouter une dépense",
    icon: Receipt,
    href: "/dashboard/expenses",
    color: "bg-orange-50 text-orange-600",
    iconColor: "text-orange-600",
  },
  {
    label: "Nouveau contact",
    description: "Ajouter un client/fournisseur",
    icon: Users,
    href: "/dashboard/contacts/new",
    color: "bg-purple-50 text-purple-600",
    iconColor: "text-purple-600",
  },
];

export function QuickActionsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Actions rapides</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {quickActions.map((action) => (
          <Link key={action.label} href={action.href}>
            <Card className="group cursor-pointer p-4 transition-all duration-200 hover:shadow-md">
              <div className="flex items-center gap-3">
                <div className={`rounded-lg p-2 ${action.color}`}>
                  <action.icon className={`h-5 w-5 ${action.iconColor}`} />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{action.label}</p>
                  <p className="text-sm text-gray-600">{action.description}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
