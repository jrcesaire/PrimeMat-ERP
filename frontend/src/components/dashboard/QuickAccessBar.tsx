/**
 * Barre d'accès rapide du tableau de bord.
 *
 * Reprend la rangée « ACCÈS RAPIDE » de la maquette : trois raccourcis en
 * contour et l'action principale (ouvrir la caisse) en aplat de la couleur
 * primaire.
 */
"use client";

import Link from "next/link";
import { ArrowRight, FileText, PackagePlus, ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";

const SHORTCUTS = [
  {
    label: "Créer un devis",
    icon: FileText,
    href: "/dashboard/sales/quotes/new",
  },
  {
    label: "Enregistrer un achat",
    icon: ShoppingBag,
    href: "/dashboard/purchases",
  },
  {
    label: "Ajouter un produit",
    icon: PackagePlus,
    href: "/dashboard/catalogue/new",
  },
];

export function QuickAccessBar() {
  return (
    <section className="space-y-3">
      <h2 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
        Accès rapide
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {SHORTCUTS.map((shortcut) => (
          <Link key={shortcut.label} href={shortcut.href}>
            <Button variant="outline" className="w-full justify-start">
              <shortcut.icon className="h-4 w-4" />
              {shortcut.label}
            </Button>
          </Link>
        ))}
        <Link href="/dashboard/sales/pos">
          <Button className="w-full justify-between">
            Ouvrir la caisse
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </section>
  );
}