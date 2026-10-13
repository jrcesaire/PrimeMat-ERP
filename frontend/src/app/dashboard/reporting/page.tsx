/**
 * Page Reporting — tableau de bord BI avec graphiques (recharts).
 *
 * Sources : /reporting/* (agrégats calculés backend, filtrage tenant).
 */
"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import {
  useExpensesByCategory,
  useInvoiceStatus,
  usePaymentsByMethod,
  useReportingKpis,
  useSalesTrend,
  useTopPartners,
  useTopProducts,
} from "@/hooks/useReporting";
import { formatCurrency } from "@/lib/utils";

const COLORS = [
  "#0d3a8f",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
  "#64748b",
];

const STATUS_LABELS: Record<string, string> = {
  posted: "Émise",
  paid: "Payée",
  partially_paid: "Partiellement payée",
  draft: "Brouillon",
  proforma: "Pro forma",
  cancelled: "Annulée",
  credit: "Avoir",
};

const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  bank_transfer: "Virement",
  check: "Chèque",
  card: "Carte",
  mobile_money: "Mobile Money",
  other: "Autre",
};

function KpiCard({
  label,
  value,
  cls = "text-gray-900",
}: {
  label: string;
  value: number;
  cls?: string;
}) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-1 break-words text-2xl font-bold leading-tight ${cls}`}>
        {formatCurrency(value)}
      </p>
    </Card>
  );
}

export default function ReportingPage() {
  const { data: kpis } = useReportingKpis();
  const { data: trend = [] } = useSalesTrend(12);
  const { data: topProducts = [] } = useTopProducts(8);
  const { data: topPartners = [] } = useTopPartners(8);
  const { data: invoiceStatus = [] } = useInvoiceStatus();
  const { data: paymentMethods = [] } = usePaymentsByMethod();
  const { data: expensesByCategory = [] } = useExpensesByCategory();

  const hasData = trend.some((t) => t.invoiced > 0 || t.collected > 0);
  const statusPie = invoiceStatus.map((s) => ({
    name: STATUS_LABELS[s.status] ?? s.status,
    value: s.amount,
    count: s.count,
  }));
  const methodPie = paymentMethods.map((m) => ({
    name: METHOD_LABELS[m.method] ?? m.method,
    value: m.amount,
    count: m.count,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reporting</h1>
        <p className="text-sm text-gray-600">
          Tableau de bord BI — 12 derniers mois
        </p>
      </div>

      {/* ---------- Cartes KPI ---------- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard label="Chiffre d'affaires facturé" value={kpis?.total_invoiced ?? 0} />
        <KpiCard label="Encaissements" value={kpis?.total_collected ?? 0} cls="text-green-700" />
        <KpiCard label="Dépenses" value={kpis?.total_expenses ?? 0} cls="text-red-600" />
        <KpiCard
          label="Trésorerie nette"
          value={kpis?.cash_flow ?? 0}
          cls={(kpis?.cash_flow ?? 0) >= 0 ? "text-green-700" : "text-red-600"}
        />
        <KpiCard label="Restes à recouvrer" value={kpis?.outstanding ?? 0} cls="text-orange-600" />
        <KpiCard label="Marge brute (CA − dépenses)" value={kpis?.gross_margin ?? 0} />
      </div>

      {!hasData && (
        <Card className="p-6 text-center text-sm text-gray-500">
          Aucune donnée sur la période — les graphiques se rempliront dès les
          premières factures.
        </Card>
      )}

      {/* ---------- Tendance mensuelle ---------- */}
      <Card className="p-4">
        <h2 className="mb-4 text-sm font-semibold text-gray-800">
          CA facturé vs encaissements vs dépenses
        </h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
              />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="invoiced" name="CA facturé" stroke="#0d3a8f" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="collected" name="Encaissé" stroke="#10b981" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="expenses" name="Dépenses" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* ---------- Top produits ---------- */}
        <Card className="p-4">
          <h2 className="mb-4 text-sm font-semibold text-gray-800">
            Top produits (par CA)
          </h2>
          {topProducts.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">Aucune vente.</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topProducts}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
                  />
                  <YAxis
                    type="category"
                    dataKey="product"
                    width={140}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: string) => (v.length > 18 ? `${v.slice(0, 17)}…` : v)}
                  />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="revenue" name="CA" fill="#0d3a8f" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* ---------- Top clients ---------- */}
        <Card className="p-4">
          <h2 className="mb-4 text-sm font-semibold text-gray-800">
            Top clients (par CA)
          </h2>
          {topPartners.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">Aucune vente.</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topPartners}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
                  />
                  <YAxis
                    type="category"
                    dataKey="partner"
                    width={140}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: string) => (v.length > 18 ? `${v.slice(0, 17)}…` : v)}
                  />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="revenue" name="CA" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ---------- Statuts de factures ---------- */}
        <Card className="p-4">
          <h2 className="mb-4 text-sm font-semibold text-gray-800">
            Factures par statut (montants)
          </h2>
          {statusPie.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">Aucune facture.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusPie}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {statusPie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* ---------- Modes de paiement ---------- */}
        <Card className="p-4">
          <h2 className="mb-4 text-sm font-semibold text-gray-800">
            Encaissements par mode de paiement
          </h2>
          {methodPie.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">Aucun paiement.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={methodPie}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {methodPie.map((_, i) => (
                      <Cell key={i} fill={COLORS[(i + 1) % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* ---------- Dépenses par catégorie ---------- */}
        <Card className="p-4">
          <h2 className="mb-4 text-sm font-semibold text-gray-800">
            Dépenses par catégorie
          </h2>
          {expensesByCategory.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">Aucune dépense.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={expensesByCategory} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="category"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v: string) => (v.length > 10 ? `${v.slice(0, 9)}…` : v)}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
                  />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="amount" name="Dépenses" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <p className="text-xs text-gray-400">
        {kpis
          ? `${kpis.invoice_count} facture(s) comptabilisée(s) · ${kpis.orders_confirmed} commande(s) confirmée(s) · ${kpis.orders_draft} brouillon(s)`
          : "Chargement des indicateurs…"}
      </p>
    </div>
  );
}
