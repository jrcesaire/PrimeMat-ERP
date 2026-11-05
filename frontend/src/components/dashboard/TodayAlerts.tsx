/**
 * « À suivre aujourd'hui » — alertes opérationnelles du tableau de bord.
 *
 * Reprend la carte de la maquette : une liste de points d'attention avec
 * pastille colorée, détail chiffré et lien d'action. Alimentée par
 * `useReportingKpis()` et `useInvoiceStatus()` — aucune donnée fictive.
 */
"use client";

import Link from "next/link";
import { AlertTriangle, ClipboardList, Truck } from "lucide-react";
import type { ElementType } from "react";
import { Card } from "@/components/ui/card";
import { useInvoiceStatus, useReportingKpis } from "@/hooks/useReporting";
import { cn, formatCurrency, formatNumber, TONE_CLASSES, type Tone } from "@/lib/utils";

interface Alert {
  icon: ElementType;
  tone: Tone;
  title: string;
  detail: string;
  href: string;
  action: string;
}

function AlertRow({ alert }: { alert: Alert }) {
  const Icon = alert.icon;
  return (
    <div className="flex items-start gap-3 border-b border-line pb-4 last:border-0 last:pb-0">
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-control",
          TONE_CLASSES[alert.tone],
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-semibold text-ink">{alert.title}</p>
        <p className="mt-0.5 text-[12px] text-muted">{alert.detail}</p>
        <Link
          href={alert.href}
          className="mt-1 inline-block text-[12px] font-medium text-primary hover:underline"
        >
          {alert.action} →
        </Link>
      </div>
    </div>
  );
}

export function TodayAlerts() {
  const { data: kpis } = useReportingKpis();
  const { data: invoiceStatus = [] } = useInvoiceStatus();

  const openInvoices = invoiceStatus
    .filter((item) => item.status !== "paid" && item.status !== "cancelled")
    .reduce(
      (acc, item) => ({
        count: acc.count + item.count,
        amount: acc.amount + item.amount,
      }),
      { count: 0, amount: 0 },
    );

  const alerts: Alert[] = [];

  if (openInvoices.count > 0) {
    alerts.push({
      icon: AlertTriangle,
      tone: "warning",
      title: "Factures à recouvrer",
      detail: `${formatNumber(openInvoices.count)} facture(s) · ${formatCurrency(openInvoices.amount)} à relancer`,
      href: "/dashboard/invoicing",
      action: "Relancer les clients",
    });
  }

  if ((kpis?.orders_draft ?? 0) > 0) {
    alerts.push({
      icon: ClipboardList,
      tone: "info",
      title: "Commandes à préparer",
      detail: `${formatNumber(kpis?.orders_draft ?? 0)} commande(s) en brouillon attendent une action`,
      href: "/dashboard/sales/orders",
      action: "Ouvrir les commandes",
    });
  }

  if ((kpis?.pending_delivery_qty ?? 0) > 0) {
    alerts.push({
      icon: Truck,
      tone: "info",
      title: "Quantités à livrer",
      detail: `${formatNumber(kpis?.pending_delivery_qty ?? 0)} unité(s) restent à expédier`,
      href: "/dashboard/delivery",
      action: "Vérifier les livraisons",
    });
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[17px] font-semibold text-ink">
          À suivre aujourd&apos;hui
        </h2>
        {alerts.length > 0 && (
          <span className="rounded-chip bg-warning-soft px-2 py-0.5 text-[11px] font-medium text-warning">
            {alerts.length}
          </span>
        )}
      </div>

      {alerts.length === 0 ? (
        <p className="py-6 text-center text-[13px] text-muted">
          Rien à signaler — tout est à jour.
        </p>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <AlertRow key={alert.title} alert={alert} />
          ))}
        </div>
      )}
    </Card>
  );
}