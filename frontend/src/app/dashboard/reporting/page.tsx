/**
 * Page Reporting — agrégats simples (CA, encaissements, dépenses, marge).
 */
"use client";

import { useMemo } from "react";
import { Card } from "@/components/ui/card";
import { useInvoices, usePayments, useExpenses } from "@/hooks/useOperations";
import { useOrders } from "@/hooks/useSales";
import { formatCurrency } from "@/lib/utils";

export default function ReportingPage() {
  const { data: invoices = [] } = useInvoices();
  const { data: payments = [] } = usePayments();
  const { data: expenses = [] } = useExpenses();
  const { data: orders = [] } = useOrders();

  const stats = useMemo(() => {
    const totalInvoiced = invoices.reduce((s, i) => s + (i.amount_total || 0), 0);
    const totalPaid = payments
      .filter((p) => p.direction === "in")
      .reduce((s, p) => s + (p.amount || 0), 0);
    const totalExpenses = expenses.reduce((s, e) => s + (e.amount || 0), 0);
    const confirmedOrders = orders.filter((o) => o.status === "confirmed").length;
    return {
      totalInvoiced,
      totalPaid,
      totalExpenses,
      cashFlow: totalPaid - totalExpenses,
      outstanding: totalInvoiced - totalPaid,
      invoiceCount: invoices.length,
      confirmedOrders,
    };
  }, [invoices, payments, expenses, orders]);

  const cards = [
    { label: "Chiffre d'affaires facturé", value: stats.totalInvoiced, cls: "text-gray-900" },
    { label: "Encaissements", value: stats.totalPaid, cls: "text-green-700" },
    { label: "Dépenses", value: stats.totalExpenses, cls: "text-red-600" },
    { label: "Trésorerie nette", value: stats.cashFlow, cls: stats.cashFlow >= 0 ? "text-green-700" : "text-red-600" },
    { label: "Restes à recouvrer", value: stats.outstanding, cls: "text-orange-600" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reporting</h1>
        <p className="text-sm text-gray-600">Indicateurs consolidés</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Card key={c.label} className="min-w-0 p-4">
            <p className="text-sm text-gray-500">{c.label}</p>
            <p className={`mt-1 break-words text-2xl font-bold leading-tight ${c.cls}`}>
              {formatCurrency(c.value)}
            </p>
          </Card>
        ))}
        <Card className="min-w-0 p-4">
          <p className="text-sm text-gray-500">Activité</p>
          <p className="mt-1 text-sm font-medium text-gray-800">
            {stats.invoiceCount} facture(s) · {stats.confirmedOrders} commande(s) confirmée(s)
          </p>
        </Card>
      </div>

      <p className="text-xs text-gray-400">
        Graphiques BI détaillés (CA par catégorie, marges) : prochaine itération.
      </p>
    </div>
  );
}
