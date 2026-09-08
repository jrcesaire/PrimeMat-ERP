/**
 * Section Statistiques BI — indicateurs clés et graphiques.
 */
"use client";

import { Euro, ShoppingCart, Package, BarChart3, Activity, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";

const biStats = [
  { label: "CA mensuel", value: "12,450,000 FCFA", change: "+15%", icon: Euro, color: "text-green-600", positive: true },
  { label: "Taux de marge", value: "32%", change: "-2%", icon: Euro, color: "text-blue-600", positive: false },
  { label: "Tickets/POS", value: "142", change: "+23%", icon: ShoppingCart, color: "text-purple-600", positive: true },
  { label: "Stock total", value: "892 000 FCFA", change: "-5%", icon: Package, color: "text-orange-600", positive: false },
];

const categorySales = [65, 40, 75, 50, 30, 55];
const categoryLabels = ["Brique", "Ciment", "Tôle", "Peinture", "Électricité", "Salle de bain"];

const topProducts = [
  { name: "Ciment 35kg", qty: "245 sacs", revenue: "1,470,000 FCFA" },
  { name: "Tôle BAC 0,45mm", qty: "180 l.", revenue: "1,080,000 FCFA" },
  { name: "Peinture Blanche 10L", qty: "89 pots", revenue: "890,000 FCFA" },
];

export function BIStatsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Statistiques (BI)</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {biStats.map((stat) => (
          <Card key={stat.label} className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-gray-50 p-2">
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-600">{stat.label}</p>
              </div>
              <div className={`ml-auto text-xs font-medium ${stat.positive ? "text-green-600" : "text-red-600"}`}>
                {stat.change}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Chart cards */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* CA par catégorie */}
        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">CA par catégorie</h3>
            <BarChart3 className="h-4 w-4 text-gray-400" />
          </div>
          <div className="h-48 w-full">
            <div className="flex h-full items-end justify-around gap-1">
              {categorySales.map((h, i) => (
                <div
                  key={i}
                  className="w-full max-w-[40px] rounded-t bg-primary opacity-80 transition-opacity hover:opacity-100"
                  style={{ height: `${h}%` }}
                  title={`Catégorie ${i + 1}: ${h}%`}
                />
              ))}
            </div>
            <div className="mt-2 flex justify-around text-xs text-gray-500">
              {categoryLabels.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>
          </div>
        </Card>

        {/* Flux de trésorerie */}
        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Flux de trésorerie</h3>
            <Activity className="h-4 w-4 text-gray-400" />
          </div>
          <div className="h-48 w-full">
            <svg className="h-full w-full" viewBox="0 0 100 40">
              <polyline
                points="0,30 15,25 30,28 45,20 60,22 75,15 90,18 100,10"
                fill="none"
                stroke="currentColor"
                strokeWidth="0.5"
                className="text-primary"
              />
            </svg>
            <div className="mt-2 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Entrées</span>
                <span className="text-green-600 font-medium">850,000 FCFA</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Sorties</span>
                <span className="text-red-600 font-medium">425,000 FCFA</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Solde net</span>
                <span className="text-blue-600 font-medium">+425,000 FCFA</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Top produits */}
        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Top produits</h3>
            <TrendingUp className="h-4 w-4 text-gray-400" />
          </div>
          <div className="h-48 w-full space-y-3">
            {topProducts.map((product, i) => (
              <div key={i} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{product.name}</p>
                  <p className="text-xs text-gray-500">{product.qty} vendus</p>
                </div>
                <span className="text-xs font-medium text-gray-900">{product.revenue}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
}
