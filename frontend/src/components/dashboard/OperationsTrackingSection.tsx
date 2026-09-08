/**
 * Section Suivi opérations — livraisons prévues et commandes en production.
 */
"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";

const plannedDeliveries = [
  { id: 1, order: "CMD-0045", client: "BTP Côte Sud", date: "2025-01-15", status: "confirmed", items: 12, amount: "850,000 FCFA" },
  { id: 2, order: "CMD-0046", client: "Matériaux Plus", date: "2025-01-16", status: "preparing", items: 8, amount: "1,200,000 FCFA" },
  { id: 3, order: "CMD-0047", client: "Construction SA", date: "2025-01-17", status: "confirmed", items: 5, amount: "450,000 FCFA" },
];

const ordersInProduction = [
  { id: 1, order: "CMD-0042", client: "BTP Côte Sud", status: "in_production", items: 3, progress: 65 },
  { id: 2, order: "CMD-0043", client: "Matériaux Plus", status: "preparation", items: 7, progress: 30 },
];

const statusConfigs: Record<string, { label: string; className: string }> = {
  confirmed: { label: "Confirmé", className: "bg-blue-100 text-blue-800" },
  preparing: { label: "En préparation", className: "bg-yellow-100 text-yellow-800" },
  in_production: { label: "En production", className: "bg-purple-100 text-purple-800" },
  preparation: { label: "Préparation", className: "bg-orange-100 text-orange-800" },
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
                  <span>{delivery.date} • {delivery.items} articles</span>
                  <span className="font-medium text-gray-900">{delivery.amount}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Orders in Production */}
        <Card className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Commandes en production</h3>
            <Link href="/dashboard/sales" className="text-sm text-primary hover:underline">
              Voir tout
            </Link>
          </div>
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
                    <span>{order.items} articles</span>
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
        </Card>
      </div>
    </section>
  );
}
