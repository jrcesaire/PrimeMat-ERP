import { useRouter } from "next/navigation";
import { ArrowLeft, Printer } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useInvoice } from "@/hooks/useOperations";
import { useClients } from "@/hooks/useCRM";
import { printInvoice } from "@/lib/api/pdf";
import { formatCurrency, formatDate, StatusBadge } from "@/lib/utils";
import type { InvoiceLine } from "@/hooks/useOperations";

function LineDetail({ line, currency }: { line: InvoiceLine; currency: string }) {
  const fmt = (n: number) => formatCurrency(n, currency);
  if (line.sell_by_length && line.cuts && line.cuts.length > 0) {
    return (
      <div className="border-b border-gray-100 py-3">
        <div className="font-medium text-gray-900">{line.description ?? `Ligne #${line.id}`}</div>
        <div className="mt-1 space-y-0.5 text-xs text-gray-500">
          {line.cuts.map((c, i) => (
            <div key={i} className="flex justify-between">
              <span>{c.quantity} pièces × {c.length.toFixed(2)} m</span>
              <span>= {(c.quantity * c.length).toFixed(2)} m</span>
            </div>
          ))}
          <div className="flex justify-between border-t border-gray-200 pt-1 font-medium text-gray-700">
            <span>Total: {line.cuts.reduce((s, c) => s + c.quantity * c.length, 0).toFixed(2)} m × {fmt(line.unit_price)}</span>
            <span>{fmt(line.subtotal)}</span>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-between border-b border-gray-100 py-3">
      <div>
        <div className="font-medium text-gray-900">{line.description ?? `Ligne #${line.id}`}</div>
        <div className="text-xs text-gray-500">Quantité: {line.quantity}</div>
      </div>
      <div className="text-right">
        <div className="font-medium">{fmt(line.unit_price)}</div>
        <div className="text-sm font-semibold text-gray-900">{fmt(line.subtotal)}</div>
      </div>
    </div>
  );
}

export default async function InvoiceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const router = useRouter();
  const invoiceId = Number(id);
  const { data: invoice, isLoading, error } = useInvoice(invoiceId);
  const { data: clients = [] } = useClients();

  if (isLoading) return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (error || !invoice) return <p className="p-6 text-sm text-red-500">Facture introuvable.</p>;

  const client = clients.find((c) => c.id === invoice.partner_id);
  const remaining = Math.max(invoice.amount_total - invoice.paid_amount, 0);
  const currency = invoice.currency_code || "XOF";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="rounded-md p-2 hover:bg-gray-100">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{invoice.reference}</h1>
            <p className="text-sm text-gray-600">
              Facture — {client?.name ?? `Client #${invoice.partner_id}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={invoice.status} />
          <Button variant="outline" size="sm" onClick={() => printInvoice(invoice.id)}>
            <Printer className="mr-2 h-4 w-4" /> Imprimer
          </Button>
        </div>
      </div>

      <Card className="grid grid-cols-2 gap-4 p-4 text-sm md:grid-cols-3">
        <div>
          <p className="text-xs text-gray-500">Client</p>
          <p className="font-medium text-gray-900">{client?.name ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Statut</p>
          <StatusBadge status={invoice.status} />
        </div>
        <div>
          <p className="text-xs text-gray-500">Date</p>
          <p className="font-medium text-gray-900">{formatDate(invoice.invoice_date)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Échéance</p>
          <p className="font-medium text-gray-900">{invoice.due_date ? formatDate(invoice.due_date) : "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Total</p>
          <p className="font-medium text-gray-900">{formatCurrency(invoice.amount_total, currency)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Payé</p>
          <p className="font-medium text-green-600">{formatCurrency(invoice.paid_amount, currency)}</p>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
              <th className="px-4 py-3">Produit</th>
              <th className="px-4 py-3 text-right">Qté</th>
              <th className="px-4 py-3 text-right">P.U.</th>
              <th className="px-4 py-3 text-right">Montant</th>
            </tr>
          </thead>
          <tbody>
            {invoice.lines?.map((l) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {l.description ?? `Produit #${l.product_id}`}
                  {l.cuts && l.cuts.length > 0 && (
                    <p className="mt-0.5 text-xs italic text-gray-500">
                      {l.cuts.map((c) => `${c.quantity} × ${c.length} m`).join(", ")}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-right">{l.quantity}</td>
                <td className="px-4 py-3 text-right">{formatCurrency(l.unit_price, currency)}</td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(l.subtotal, currency)}</td>
              </tr>
            ))}
            {(!invoice.lines || invoice.lines.length === 0) && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                  Aucune ligne.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card className="space-y-2 p-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Montant hors taxes</span>
          <span className="font-medium text-gray-900">{formatCurrency(invoice.amount_untaxed, currency)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">TVA</span>
          <span className="font-medium text-gray-900">{formatCurrency(invoice.tax_amount, currency)}</span>
        </div>
        <div className="flex justify-between text-base font-bold">
          <span className="text-gray-700">Total</span>
          <span>{formatCurrency(invoice.amount_total, currency)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Payé</span>
          <span className="font-medium text-green-600">{formatCurrency(invoice.paid_amount, currency)}</span>
        </div>
        <div className="flex justify-between text-sm font-semibold">
          <span className="text-gray-500">Reste dû</span>
          <span className={remaining > 0 ? "text-red-600" : "text-gray-600"}>
            {formatCurrency(remaining, currency)}
          </span>
        </div>
      </Card>
    </div>
  );
}
