/**
 * Dernières commandes — tableau compact du tableau de bord.
 *
 * Reprend la carte « Dernières commandes » de la maquette (référence, client,
 * date, montant, statut). Les données viennent de `useOrders()` ; base vide →
 * état vide.
 */
"use client";

import Link from "next/link";
import { ShoppingCart } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  TableFootBar,
  TableHeadRow,
  TableRow,
  TableShell,
  Td,
  Th,
} from "@/components/ui/data-table";
import { useOrders } from "@/hooks/useSales";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";

/** Nombre de commandes affichées sur le tableau de bord. */
const LIMIT = 5;

export function RecentOrders() {
  const { data: orders = [], isLoading } = useOrders();
  const recent = orders.slice(0, LIMIT);

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[17px] font-semibold text-ink">Dernières commandes</h2>
        <Link
          href="/dashboard/sales/orders"
          className="text-[13px] font-medium text-primary hover:underline"
        >
          Voir toutes →
        </Link>
      </div>

      {isLoading ? (
        <div className="h-48 animate-pulse rounded-control bg-subtle" />
      ) : recent.length === 0 ? (
        <EmptyState
          icon={ShoppingCart}
          title="Aucune commande"
          description="Les commandes clients apparaîtront ici dès leur création."
        />
      ) : (
        <TableShell>
          <table className="w-full">
            <thead>
              <TableHeadRow>
                <Th>Commande</Th>
                <Th>Date</Th>
                <Th className="text-right">Montant</Th>
                <Th>Statut</Th>
              </TableHeadRow>
            </thead>
            <tbody>
              {recent.map((order) => (
                <TableRow key={order.id}>
                  <Td className="font-semibold">{order.reference}</Td>
                  <Td className="text-muted">{formatDate(order.order_date)}</Td>
                  <Td className="text-right font-semibold tabular-nums">
                    {formatCurrency(order.amount_total)}
                  </Td>
                  <Td>
                    <StatusBadge status={order.status} />
                  </Td>
                </TableRow>
              ))}
            </tbody>
          </table>
          <TableFootBar shown={recent.length} total={orders.length} />
        </TableShell>
      )}
    </Card>
  );
}