/**
 * Rapport de clôture de session de caisse (Point de Vente).
 * Affiche le récapitulatif financier d'une session et permet l'impression.
 * Conforme au PRD §4.1.2 §4 — Rapport de clôture.
 */
"use client";
import { RowsSkeleton } from "@/components/ui/skeleton";

import { useState } from "react";
import { ArrowLeft, Printer, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { usePosSessionCloseReport } from "@/hooks/usePosSessions";
import { PosSessionCloseReport } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

interface Props {
  sessionId: number | null;
  onBack: () => void;
}

function statusVariant(status: string) {
  switch (status) {
    case "open":
      return "default";
    case "closing":
      return "outline";
    case "closed":
      return "secondary";
    default:
      return "secondary";
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "open":
      return "Ouverte";
    case "closing":
      return "Clôture en cours";
    case "closed":
      return "Clôturée";
    default:
      return status;
  }
}

export function PosCloseReport({ sessionId, onBack }: Props) {
  const { data: report, isLoading } = usePosSessionCloseReport(sessionId);
  const [printing, setPrinting] = useState(false);

  if (!report) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" /> Retour
          </Button>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Rapport de clôture</h1>
        </div>
        {isLoading ? (
          <RowsSkeleton className="mx-auto max-w-lg" />
        ) : (
          <p className="p-10 text-center text-sm text-muted">
            Rapport de clôture introuvable pour cette session.
          </p>
        )}
      </div>
    );
  }

  const varianceClass =
    report.variance === null
      ? "text-muted"
      : report.variance < 0
        ? "text-red-600 font-medium"
        : report.variance > 0
          ? "text-green-600 font-medium"
          : "text-muted font-medium";

  const handlePrint = async () => {
    setPrinting(true);
    try {
      const win = window.open("", "_blank", "width=800,height=900");
      if (!win) return;
      win.document.write(`
        <!DOCTYPE html>
        <html lang="fr">
        <head>
          <meta charset="utf-8" />
          <title>Rapport de clôture — ${report.reference}</title>
          <style>
            @page { size: A4; margin: 18mm; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 11pt; color: #111827; }
            .header { border-bottom: 2px solid #111827; padding-bottom: 8px; margin-bottom: 16px; }
            .title { font-size: 16pt; font-weight: 800; margin: 0; }
            .subtitle { color: #6b7280; font-size: 9pt; margin: 2px 0 0 0; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin-bottom: 16px; }
            .kv > div { margin-bottom: 4px; }
            .kv .k { color: #6b7280; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.04em; }
            .kv .v { font-weight: 600; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 9pt; }
            th { text-align: left; border-bottom: 1px solid #d1d5db; color: #6b7280; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.04em; padding: 6px 4px; }
            td { border-bottom: 1px solid #e5e7eb; padding: 5px 4px; vertical-align: top; }
            td.right, th.right { text-align: right; }
            .total-row { font-weight: 700; border-top: 2px solid #111827; }
            .footer { margin-top: 20px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 8pt; color: #6b7280; }
          </style>
        </head>
        <body>
          <div class="header">
            <p class="title">Rapport de clôture de caisse</p>
            <p class="subtitle">Point de Vente — ${report.reference}</p>
          </div>
          <div class="grid">
            <div class="kv">
              <div><span class="k">Session</span><span class="v">${report.reference}</span></div>
              <div><span class="k">Statut</span><span class="v">${statusLabel(report.status)}</span></div>
              <div><span class="k">Ouverte le</span><span class="v">${formatDate(report.opened_at)}</span></div>
              <div><span class="k">Clôturée le</span><span class="v">${report.closed_at ? formatDate(report.closed_at) : "—"}</span></div>
            </div>
            <div class="kv">
              <div><span class="k">Solde initial</span><span class="v">${formatCurrency(report.initial_balance)}</span></div>
              <div><span class="k">Total des ventes</span><span class="v">${formatCurrency(report.sales_total)}</span></div>
              <div><span class="k">Nombre de ventes</span><span class="v">${report.sales_count}</span></div>
              <div><span class="k">Solde théorique</span><span class="v">${formatCurrency(report.theoretical_balance)}</span></div>
            </div>
          </div>
          <div class="kv" style="margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px; background: #f9fafb;">
            <div><span class="k">Solde constaté</span><span class="v">${formatCurrency(report.closing_balance ?? 0)}</span></div>
            <div>
              <span class="k">Écart de caisse</span>
              <span class="v">
                ${report.variance === null ? "—" : (report.variance >= 0 ? "+" : "")}${formatCurrency(report.variance ?? 0)}
              </span>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th style="width: 22%">Référence</th>
                <th style="width: 18%">Date</th>
                <th style="width: 30%">Client</th>
                <th class="right" style="width: 15%">Montant</th>
                <th class="right" style="width: 15%">Total</th>
              </tr>
            </thead>
            <tbody>
              ${report.sales
                .map(
                  (s) => `
                <tr>
                  <td>${s.order_reference}</td>
                  <td>${formatDate(s.created_at)}</td>
                  <td>${s.partner_name ?? "—"}</td>
                  <td class="right">${formatCurrency(s.amount_total)}</td>
                  <td class="right">${formatCurrency(s.amount_total)}</td>
                </tr>
              `,
                )
                .join("")}
              <tr class="total-row">
                <td colspan="3">Total des ventes</td>
                <td class="right">${formatCurrency(report.sales_total)}</td>
                <td class="right">${formatCurrency(report.sales_total)}</td>
              </tr>
            </tbody>
          </table>
          <div class="footer">
            Généré le ${new Date().toLocaleString("fr-FR")} — ERP Point de Vente.
          </div>
        </body>
        </html>
      `);
      win.document.close();
      win.focus();
      win.print();
      win.onafterprint = () => win.close();
    } finally {
      setPrinting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" /> Retour
          </Button>
          <Button
            size="sm"
            onClick={handlePrint}
            disabled={printing}
            title="Imprimer le rapport de clôture"
          >
            {printing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Printer className="h-4 w-4" />
            )}
            Imprimer le rapport
          </Button>
        </div>
        <h1 className="text-[28px] font-semibold leading-tight text-ink">Rapport de clôture</h1>
        <Badge variant={statusVariant(report.status)}>{statusLabel(report.status)}</Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Récapitulatif financier</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs uppercase text-muted">Solde initial</div>
            <div className="text-lg font-medium">{formatCurrency(report.initial_balance)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-muted">Total des ventes</div>
            <div className="text-lg font-medium">{formatCurrency(report.sales_total)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-muted">Mouvements de fonds</div>
            <div className="text-lg font-medium">
              {formatCurrency(report.fund_movements_total)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-muted">Nombre de ventes</div>
            <div className="text-lg font-medium">{report.sales_count}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs uppercase text-muted">Solde théorique</div>
            <div className="text-lg font-medium">{formatCurrency(report.theoretical_balance)}</div>
          </div>
          <div className="space-y-1 col-span-2 md:col-span-1">
            <div className="text-xs uppercase text-muted">Solde constaté</div>
            <div className="text-lg font-medium">{formatCurrency(report.closing_balance ?? 0)}</div>
          </div>
          <div className="space-y-1 col-span-2 md:col-span-1">
            <div className="text-xs uppercase text-muted">Écart de caisse</div>
            <div className={`text-lg font-medium ${varianceClass}`}>
              {report.variance === null ? "—" : report.variance >= 0 ? `+${formatCurrency(report.variance)}` : formatCurrency(report.variance)}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ventes de la session</CardTitle>
          <CardDescription>
            {report.sales_count} vente{report.sales_count > 1 ? "s" : ""} enregistrée{report.sales_count > 1 ? "s" : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {report.sales.length === 0 ? (
            <p className="p-4 text-center text-sm text-muted">
              Aucune vente rattachée à cette session.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs uppercase text-muted">
                    <th className="px-4 py-3">Référence</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Client</th>
                    <th className="px-4 py-3 text-right">Montant</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sales.map((s) => (
                    <tr key={s.order_reference} className="border-b border-line">
                      <td className="px-4 py-3 font-semibold text-ink">
                        {s.order_reference}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {formatDate(s.created_at)}
                      </td>
                      <td className="px-4 py-3 text-ink">
                        {s.partner_name ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        {formatCurrency(s.amount_total)}
                      </td>
                    </tr>
                  ))}
                  <tr className="border-t border-line font-bold bg-subtle">
                    <td className="px-4 py-3" colSpan={3}>
                      Total des ventes
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatCurrency(report.sales_total)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="text-xs text-muted text-center">
        Généré le {new Date().toLocaleString("fr-FR")} — ERP Point de Vente.
        {report.variance !== null && report.variance < 0 && (
          <span className="text-red-600 font-medium ml-2">
            ⚠️ Écart négatif détecté — solde constaté inférieur au solde théorique.
          </span>
        )}
      </div>
    </div>
  );
}