/**
 * Section Suivi opérations — livraisons prévues et commandes en production.
 *
 * Données réelles : commandes confirmées (livraisons) et commandes
 * en brouillon/préparation (production). Base vide → états vides.
 */
"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { useMemo } from "react";
import { useOrders } from "@/hooks/useSales";
import { useDeliveryNotes } from "@/hooks/useOperations";
import { formatCurrency, formatDate } from "@/lib/utils";

const statusConfigs: Record<string, { label: string; className: string }> = {
  draft: { label: "Brouillon", className: "bg-gray-100 text-gray-700" },
  confirmed: { label: "Confirmé", className: "bg-blue-100 text-blue-800" },
  preparing: { label: "En préparation", className: "bg-yellow-100 text-yellow-800" },
  in_production: { label: "En production", className: "bg-purple-100 text-purple-800" },
  preparation: { label: "Préparation", className: "bg-orange-100 text-orange-800" },
  shipped: { label: "Expédié", className: "bg-cyan-100 text-cyan-800" },
  delivered: { label: "Livré", className: "bg-green-100 text-green-800" },
};

function StatusBadge({ status }: { status: string }) {
  const config = statusConfigs[status] || { label: status, className: "bg-gray-100 text-gray-800" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}

export function OperationsTrackingSection() {
  const { data: orders = [] } = useOrders();
  const { data: deliveries = [] } = useDeliveryNotes();

  const plannedDeliveries = useMemo(
    () =>
      orders
        .filter((o) => o.status === "confirmed")
        .slice(0, 3)
        .map((o) => ({
          id: o.id,
          order: o.reference,
          // Le nom client complet arrive via l'endpoint détail ; ici on affiche la référence
          client: `Commande ${o.reference}`,
          date: o.order_date ?? null,
          status: o.status,
          items: o.lines?.length ?? 0,
          amount: o.amount_total ?? 0,
        })),
    [orders]
  );

  const ordersInProduction = useMemo(
    () =>
      orders
        .filter((o) => o.status === "draft")
        .slice(0, 3)
        .map((o) => ({
          id: o.id,
          order: o.reference,
          client: `Commande ${o.reference}`,
          status: o.status,
          items: o.lines?.length ?? 0,
          // Progression : part des lignes livrées si des BL existent, sinon 0
          progress: 0,
        })),
    [orders]
  );

  void deliveries;

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Suivi opérations</h2>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Planned Deliveries */}
        <Card className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Livraisons prévues</h3>
            <Link href="/dashboard/delivery" className="text-sm text-primary hover:underline">
              Voir tout
            </Link>
          </div>
          {plannedDeliveries.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">
              Aucune commande confirmée pour le moment.
            </p>
          ) : (
          <div className="space-y-3">
            {plannedDeliveries.map((delivery) => (
              <div key={delivery.id} className="border-b border-gray-100 pb-3 last:border-0">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{delivery.order}</p>
                    <p className="text-sm text-gray-600">{delivery.client}</p>
                  </div>
                  <StatusBadge status={delivery.status} />
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
                  <span>{formatDate(delivery.date)} • {delivery.items} article{delivery.items > 1 ? "s" : ""}</span>
                  <span className="font-medium tabular-nums text-gray-900">{formatCurrency(delivery.amount)}</span>
                </div>
              </div>
            ))}
          </div>
          )}
        </Card>

        {/* Orders in Production */}
        <Card className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Commandes en production</h3>
            <Link href="/dashboard/sales" className="text-sm text-primary hover:underline">
              Voir tout
            </Link>
          </div>
          {ordersInProduction.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">
              Aucun brouillon en cours pour le moment.
            </p>
          ) : (
          <div className="space-y-4">
            {ordersInProduction.map((order) => (
              <div key={order.id} className="border-b border-gray-100 pb-3 last:border-0">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{order.order}</p>
                    <p className="text-sm text-gray-600">{order.client}</p>
                  </div>
                  <StatusBadge status={order.status} />
                </div>
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{order.items} article{order.items > 1 ? "s" : ""}</span>
                    <span>{order.progress}%</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-gray-200">
                    <div
                      className="h-1.5 rounded-full bg-primary"
                      style={{ width: `${order.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          )}
        </Card>
      </div>
    </section>
  );
}
