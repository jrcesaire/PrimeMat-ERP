/**
 * Section Statistiques BI — indicateurs clés et graphiques (données réelles).
 *
 * Zéro valeur fictive : base vide → états « en attente de données »
 * (cartes à 0, graphiques vides, top listes masquées).
 */
"use client";

import { Euro, ShoppingCart, Package, BarChart3, Activity, TrendingUp, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useMemo } from "react";
import {
  useExpensesByCategory,
  useInvoiceStatus,
  usePaymentsByMethod,
  useReportingKpis,
  useSalesTrend,
  useTopPartners,
  useTopProducts,
} from "@/hooks/useReporting";
import { useInvoices } from "@/hooks/useOperations";
import { formatCurrency, formatNumber } from "@/lib/utils";

export function BIStatsSection() {
  const { data: kpis, isLoading: kpisLoading } = useReportingKpis();
  const { data: trend = [] } = useSalesTrend(12);
  const { data: topProducts = [] } = useTopProducts(6);
  const { data: topPartners = [] } = useTopPartners(5);
  const { data: invoiceStatus = [] } = useInvoiceStatus();
  const { data: paymentMethods = [] } = usePaymentsByMethod();
  const { data: expensesByCategory = [] } = useExpensesByCategory();
  const { data: invoices = [] } = useInvoices();

  const hasDocuments =
    (kpis?.invoice_count ?? 0) > 0 ||
    (kpis?.orders_total ?? 0) > 0 ||
    invoices.length > 0;

  const cards = useMemo(
    () => [
      {
        label: "CA mensuel",
        value: formatCurrency(kpis?.total_invoiced ?? 0),
        icon: Euro,
        color: "text-green-600",
      },
      {
        label: "Encaissements",
        value: formatCurrency(kpis?.total_collected ?? 0),
        icon: Euro,
        color: "text-blue-600",
      },
      {
        label: "Factures",
        value: formatNumber(kpis?.invoice_count ?? 0),
        icon: ShoppingCart,
        color: "text-purple-600",
      },
      {
        label: "Restes à recouvrer",
        value: formatCurrency(kpis?.outstanding ?? 0),
        icon: Package,
        color: "text-orange-600",
      },
    ],
    [kpis]
  );

  const categoryChart = useMemo(() => {
    const byCat = expensesByCategory.slice(0, 6);
    const max = Math.max(1, ...byCat.map((c) => c.amount));
    return byCat.map((c) => ({
      label: c.category,
      heightPct: Math.max(4, Math.round((c.amount / max) * 100)),
      title: `${c.category} : ${formatCurrency(c.amount)}`,
    }));
  }, [expensesByCategory]);

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Statistiques (BI)</h2>
      {kpisLoading ? (
        <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Chargement des indicateurs…
        </div>
      ) : (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((stat) => (
          <Card key={stat.label} className="p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-gray-50 p-2">
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-2xl font-bold tabular-nums text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-600">{stat.label}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
      )}

      {/* Chart cards */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* CA par catégorie — dépenses réelles par catégorie */}
        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Dépenses par catégorie</h3>
            <BarChart3 className="h-4 w-4 text-gray-400" />
          </div>
          {categoryChart.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
              Aucune dépense enregistrée pour le moment.
            </p>
          ) : (
          <div className="h-48 w-full">
            <div className="flex h-full items-end justify-around gap-1">
              {categoryChart.map((bar) => (
                <div
                  key={bar.label}
                  className="w-full max-w-[40px] rounded-t bg-primary opacity-80 transition-opacity hover:opacity-100"
                  style={{ height: `${bar.heightPct}%` }}
                  title={bar.title}
                />
              ))}
            </div>
            <div className="mt-2 flex justify-around gap-1 text-xs text-gray-500">
              {categoryChart.map((bar) => (
                <span key={bar.label} className="max-w-[60px] truncate" title={bar.label}>
                  {bar.label}
                </span>
              ))}
            </div>
          </div>
          )}
        </Card>

        {/* Flux de trésorerie — encaissements vs dépenses (12 derniers mois) */}
        <Card className="flex flex-col p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Flux de trésorerie</h3>
            <Activity className="h-4 w-4 text-gray-400" />
          </div>
          {trend.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
              Aucun mouvement enregistré pour le moment.
            </p>
          ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            <svg
              className="min-h-[120px] w-full flex-1"
              viewBox={`0 0 ${Math.max(trend.length - 1, 1) * 12} 40`}
              preserveAspectRatio="none"
            >
              <polyline
                points={trend
                  .map((p, i) => {
                    const max = Math.max(1, ...trend.map((t) => t.collected));
                    const x = i * 12;
                    const y = 38 - Math.min(36, (p.collected / max) * 36);
                    return `${x},${y.toFixed(1)}`;
                  })
                  .join(" ")}
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
                className="text-primary"
              />
            </svg>
            <div className="mt-2 shrink-0 space-y-1">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="shrink-0 text-gray-500">Entrées</span>
                <span className="whitespace-nowrap font-medium tabular-nums text-green-600">
                  {formatCurrency(kpis?.total_collected ?? 0)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="shrink-0 text-gray-500">Sorties</span>
                <span className="whitespace-nowrap font-medium tabular-nums text-red-600">
                  {formatCurrency(kpis?.total_expenses ?? 0)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="shrink-0 text-gray-500">Solde net</span>
                <span className="whitespace-nowrap font-medium tabular-nums text-blue-600">
                  {formatCurrency(kpis?.cash_flow ?? 0)}
                </span>
              </div>
            </div>
          </div>
          )}
        </Card>

        {/* Top produits — issu des factures comptabilisées */}
        <Card className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Top produits</h3>
            <TrendingUp className="h-4 w-4 text-gray-400" />
          </div>
          {topProducts.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
              {hasDocuments
                ? "Aucune vente comptabilisée pour le moment."
                : "Les meilleures ventes apparaîtront après les premières factures."}
            </p>
          ) : (
          <div className="h-48 w-full space-y-3 overflow-y-auto">
            {topProducts.map((product) => (
              <div key={product.product} className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900" title={product.product}>
                    {product.product}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatNumber(product.quantity)} vendu{product.quantity > 1 ? "s" : ""}
                    {product.category ? ` • ${product.category}` : ""}
                  </p>
                </div>
                <span className="shrink-0 whitespace-nowrap text-xs font-medium tabular-nums text-gray-900">
                  {formatCurrency(product.revenue)}
                </span>
              </div>
            ))}
          </div>
          )}
          {topPartners.length > 0 && (
            <div className="mt-4 border-t border-gray-100 pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Meilleurs clients
              </p>
              <div className="space-y-2">
                {topPartners.slice(0, 3).map((partner) => (
                  <div key={partner.partner} className="flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-gray-700" title={partner.partner}>
                      {partner.partner}
                    </span>
                    <span className="shrink-0 font-medium tabular-nums text-gray-900">
                      {formatCurrency(partner.revenue)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
      <p className="mt-3 text-xs text-gray-400">
        {hasDocuments
          ? `${formatNumber(kpis?.invoice_count ?? 0)} facture(s) comptabilisée(s) · ` +
            `${formatNumber(kpis?.orders_confirmed ?? 0)} commande(s) confirmée(s) · ` +
            `${formatNumber(kpis?.orders_draft ?? 0)} brouillon(s)`
          : "En attente des premières données — créez un devis pour alimenter le tableau de bord."}
      </p>
      {paymentMethods.length > 0 && invoiceStatus.length > 0 && (
        <p className="mt-1 text-xs text-gray-400">
          {invoiceStatus.length} statut(s) de facturation · {paymentMethods.length} mode(s) de paiement utilisé(s).
        </p>
      )}
    </section>
  );
}
