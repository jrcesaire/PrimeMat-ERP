/**
 * Panneau d'encaissement type terminal (maquette caisse B) :
 * tuiles de méthode de paiement + affichage montant reçu / monnaie +
 * pavé numérique + bouton « Encaisser » géant.
 */
"use client";

import { Banknote, FileText, Landmark, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/lib/utils";
import { PosKeypad } from "./PosKeypad";

const METHODS = [
  { id: "cash", label: "Espèces", Icon: Banknote },
  { id: "mobile_money", label: "Mobile Money", Icon: Smartphone },
  { id: "bank", label: "Virement", Icon: Landmark },
  { id: "check", label: "Chèque", Icon: FileText },
] as const;

interface Props {
  method: string;
  onMethod: (method: string) => void;
  /** Montant reçu saisi au pavé (chaîne contrôlée par la page). */
  amount: string;
  onAmount: (value: string) => void;
  total: number;
  /** Panier vide : bloque l'encaissement. */
  disabled?: boolean;
  submitting?: boolean;
  error?: string | null;
  onSubmit: () => void;
}

export function PosPaymentPanel({
  method,
  onMethod,
  amount,
  onAmount,
  total,
  disabled,
  submitting,
  error,
  onSubmit,
}: Props) {
  const received = Number(amount || 0);
  const change = received - total;

  return (
    <div className="space-y-3 rounded-card border border-line bg-surface p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
        Mode de paiement
      </p>

      <div className="grid grid-cols-2 gap-2">
        {METHODS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onMethod(id)}
            className={cn(
              "flex items-center gap-2 rounded-control border px-3 py-2.5 text-[13px] font-medium transition-colors",
              method === id
                ? "border-primary bg-primary-soft text-primary"
                : "border-line bg-surface text-muted hover:bg-subtle hover:text-ink",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </button>
        ))}
      </div>

      {/* Affichage montant reçu / monnaie — style terminal encaisseur */}
      <div className="rounded-control bg-subtle p-3 text-right">
        <p className="text-[10px] uppercase tracking-[0.08em] text-muted">
          Montant reçu
        </p>
        <p className="text-[22px] font-semibold tabular-nums text-ink">
          {formatCurrency(received)}
        </p>
        <p
          className={cn(
            "mt-1 text-[12px] font-medium",
            change > 0
              ? "text-success"
              : received > 0 && change < 0
                ? "text-warning"
                : "text-faint",
          )}
        >
          {change > 0
            ? `Monnaie à rendre : ${formatCurrency(change)}`
            : received > 0 && change < 0
              ? `Reste à encaisser : ${formatCurrency(-change)}`
              : "\u00A0"}
        </p>
      </div>

      <PosKeypad
        value={amount}
        onChange={onAmount}
        onExact={() => onAmount(String(total))}
      />

      {error && (
        <div className="rounded-control bg-danger-soft p-3 text-[13px] text-danger">
          {error}
        </div>
      )}

      <Button
        size="lg"
        onClick={onSubmit}
        disabled={disabled || submitting || (received > 0 && change < 0)}
        className="h-12 w-full"
      >
        {submitting
          ? "Encaissement…"
          : `Encaisser ${formatCurrency(total)}`}
      </Button>
    </div>
  );
}