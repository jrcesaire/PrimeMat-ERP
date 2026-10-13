/**
 * Page du dashboard — Interface d'accueil moderne et ergonomique.
 *
 * Première zone visible : modules principaux (Ventes, PdV, Dépenses, Contacts)
 * Zone suivante : actions rapides (nouveau devis, vente comptoir, dépense)
 * Zone suivante : livraisons prévues et commandes en production
 * Dernière zone : statistiques BI
 */
"use client";

import { useRouter } from "next/navigation";
import { QuickActionsSection } from "@/components/dashboard/QuickActionsSection";
import { MainModulesSection } from "@/components/dashboard/MainModulesSection";
import { OperationsTrackingSection } from "@/components/dashboard/OperationsTrackingSection";
import { BIStatsSection } from "@/components/dashboard/BIStatsSection";
import { LayoutGrid, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const router = useRouter();

  return (
    <div className="space-y-8 pb-12">
      {/* Hero header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tableau de bord</h1>
          <p className="mt-1 text-sm text-gray-600">
            Bienvenue dans votre ERP — ERP Matériaux de Construction
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/")}
            title="Retour à toutes les applications"
            className="flex items-center gap-2"
          >
            <LayoutGrid className="h-4 w-4" />
            Toutes les applications
          </Button>
          <Button variant="outline" size="sm" className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Actualiser
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <QuickActionsSection />

      {/* Main Modules */}
      <MainModulesSection />

      {/* Operations Tracking */}
      <OperationsTrackingSection />

      {/* BI Stats */}
      <BIStatsSection />
    </div>
  );
}
