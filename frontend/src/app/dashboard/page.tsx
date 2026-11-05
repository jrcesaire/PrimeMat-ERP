/**
 * Page du tableau de bord — vue d'ensemble de l'activité.
 *
 * Disposition de la maquette « GEA ERP » :
 * 1. en-tête (salutation + actions) ;
 * 2. **rangée de 4 indicateurs clés, visible dès l'ouverture** ;
 * 3. graphique d'évolution du chiffre d'affaires + encaissements par mode ;
 * 4. dernières commandes + points à suivre ;
 * 5. barre d'accès rapide.
 */
"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { LayoutGrid, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { DashboardKpis } from "@/components/dashboard/DashboardKpis";
import { RevenueChart } from "@/components/dashboard/RevenueChart";
import { SalesChannels } from "@/components/dashboard/SalesChannels";
import { RecentOrders } from "@/components/dashboard/RecentOrders";
import { TodayAlerts } from "@/components/dashboard/TodayAlerts";
import { QuickAccessBar } from "@/components/dashboard/QuickAccessBar";
import { useCurrentUser } from "@/hooks/useAuth";

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  // Salutation personnalisée quand le profil est chargé.
  const firstName =
    user?.first_name?.trim() || user?.full_name?.trim().split(" ")[0] || "";

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        eyebrow="Tableau de bord"
        title={firstName ? `Bonjour, ${firstName}` : "Bonjour,"}
        subtitle="Voici ce qui se passe dans votre entreprise aujourd'hui."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/")}
              title="Retour à toutes les applications"
            >
              <LayoutGrid className="h-4 w-4" />
              Toutes les applications
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => queryClient.invalidateQueries()}
              title="Recharger les indicateurs"
            >
              <RefreshCw className="h-4 w-4" />
              Actualiser
            </Button>
          </>
        }
      />

      {/* Indicateurs clés — visibles dès l'ouverture du tableau de bord. */}
      <DashboardKpis />

      {/* Activité commerciale */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RevenueChart />
        </div>
        <SalesChannels />
      </div>

      {/* Opérations et points d'attention */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecentOrders />
        </div>
        <TodayAlerts />
      </div>

      <QuickAccessBar />
    </div>
  );
}
