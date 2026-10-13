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
    <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
        Mode de paiement
      </p>

      <div className="grid grid-cols-2 gap-2">
        {METHODS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onMethod(id)}
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-3 text-sm font-medium transition",
              method === id
                ? "border-primary bg-primary text-white shadow"
                : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </button>
        ))}
      </div>

      {/* Affichage montant reçu / monnaie — style terminal encaisseur */}
      <div className="rounded-md bg-gray-900 p-3 text-right">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">
          Montant reçu
        </p>
        <p className="text-2xl font-bold tabular-nums text-white">
          {formatCurrency(received)}
        </p>
        <p
          className={cn(
            "mt-1 text-sm font-medium",
            change > 0
              ? "text-green-400"
              : received > 0 && change < 0
                ? "text-amber-400"
                : "text-gray-500",
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
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <Button
        size="lg"
        onClick={onSubmit}
        disabled={disabled || submitting || (received > 0 && change < 0)}
        className="h-14 w-full bg-green-600 text-base font-bold text-white hover:bg-green-700"
      >
        {submitting
          ? "Encaissement…"
          : `Encaisser ${formatCurrency(total)}`}
      </Button>
    </div>
  );
}