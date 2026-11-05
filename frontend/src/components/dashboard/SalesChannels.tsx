/**
 * Répartition des encaissements par mode de règlement.
 *
 * Reprend la carte « Vos canaux de vente » de la maquette, alimentée par
 * `GET /reporting/payments-by-method`.
 */
"use client";

import { Wallet } from "lucide-react";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ProgressBar } from "@/components/ui/progress-bar";
import { usePaymentsByMethod } from "@/hooks/useReporting";
import { formatCurrency } from "@/lib/utils";

/** Libellés lisibles des modes de règlement renvoyés par l'API. */
const METHOD_LABELS: Record<string, string> = {
  cash: "Espèces",
  card: "Carte bancaire",
  mobile_money: "Mobile money",
  bank_transfer: "Virement",
  check: "Chèque",
  credit: "Crédit",
};

const TONES = ["primary", "success", "warning", "muted"] as const;

export function SalesChannels() {
  const { data: methods = [], isLoading } = usePaymentsByMethod();

  const total = methods.reduce((sum, method) => sum + method.amount, 0);
  const top = [...methods].sort((a, b) => b.amount - a.amount).slice(0, 4);

  return (
    <Card>
      <h2 className="text-[17px] font-semibold text-ink">
        Encaissements par mode
      </h2>
      <p className="mt-0.5 text-[13px] text-muted">
        {formatCurrency(total)} encaissés au total
      </p>

      {isLoading ? (
        <div className="mt-5 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 animate-pulse rounded-control bg-subtle" />
          ))}
        </div>
      ) : top.length === 0 ? (
        <EmptyState
          icon={Wallet}
          title="Aucun encaissement"
          description="La répartition s'affichera dès le premier règlement enregistré."
        />
      ) : (
        <div className="mt-5 space-y-4">
          {top.map((method, index) => (
            <ProgressBar
              key={method.method}
              label={METHOD_LABELS[method.method] ?? method.method}
              value={formatCurrency(method.amount)}
              percent={total > 0 ? (method.amount / total) * 100 : 0}
              tone={TONES[index % TONES.length]}
            />
          ))}
        </div>
      )}
    </Card>
  );
}