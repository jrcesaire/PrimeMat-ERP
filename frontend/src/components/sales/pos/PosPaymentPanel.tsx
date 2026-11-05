/**
 * Panneau d'encaissement du ticket de caisse.
 *
 * Disposition de la maquette « GEA ERP » : modes de paiement en tuiles, montant
 * reçu, puis bouton d'encaissement pleine largeur avec flèche.
 *
 * Le **pavé numérique est replié par défaut** : le ticket tient ainsi à l'écran
 * sans défilement (carte, mobile money et virement ne demandent pas de montant
 * reçu). Le caissier le déplie d'un geste pour rendre la monnaie en espèces —
 * la liste d'articles se réduit alors d'autant, sans jamais pousser le bouton
 * d'encaissement hors de l'écran.
 */
"use client";

import { useState } from "react";
import {
  ArrowRight,
  Banknote,
  Calculator,
  ChevronDown,
  FileText,
  Landmark,
  Smartphone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/lib/utils";
import { PosKeypad } from "./PosKeypad";

const METHODS = [
  { id: "cash", label: "Espèces", Icon: Banknote },
  { id: "mobile_money", label: "Mobile", Icon: Smartphone },
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
  const [keypadOpen, setKeypadOpen] = useState(false);

  return (
    <div className="space-y-3">
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
              "flex items-center justify-center gap-2 rounded-control border px-2 py-2 text-[12px] font-medium transition-colors",
              method === id
                ? "border-primary bg-primary-soft text-primary"
                : "border-line bg-surface text-muted hover:bg-subtle hover:text-ink",
            )}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>

      {/* Montant reçu — pavé replié par défaut */}
      <div className="rounded-control bg-subtle p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[10px] uppercase tracking-[0.08em] text-muted">
            Montant reçu
          </p>
          <button
            type="button"
            onClick={() => setKeypadOpen((open) => !open)}
            aria-expanded={keypadOpen}
            className="flex items-center gap-1 rounded-chip px-2 py-0.5 text-[11px] font-medium text-primary hover:bg-primary/10"
          >
            <Calculator className="h-3.5 w-3.5" />
            {keypadOpen ? "Masquer" : "Saisir"}
            <ChevronDown
              className={cn(
                "h-3 w-3 transition-transform",
                keypadOpen && "rotate-180",
              )}
            />
          </button>
        </div>
        <p className="mt-1 text-right text-[20px] font-semibold tabular-nums text-ink">
          {formatCurrency(received)}
        </p>
        {received > 0 && (
          <p
            className={cn(
              "text-right text-[11px] font-medium",
              change > 0
                ? "text-success"
                : change < 0
                  ? "text-warning"
                  : "text-faint",
            )}
          >
            {change > 0
              ? `Monnaie à rendre : ${formatCurrency(change)}`
              : change < 0
                ? `Reste à encaisser : ${formatCurrency(-change)}`
                : "Compte juste"}
          </p>
        )}
      </div>

      {keypadOpen && (
        <PosKeypad
          value={amount}
          onChange={onAmount}
          onExact={() => onAmount(String(total))}
        />
      )}

      {error && (
        <div className="rounded-control bg-danger-soft p-2.5 text-[12px] text-danger">
          {error}
        </div>
      )}

      <Button
        size="lg"
        onClick={onSubmit}
        disabled={disabled || submitting || (received > 0 && change < 0)}
        className="h-12 w-full justify-between"
      >
        {submitting ? "Encaissement…" : `Encaisser ${formatCurrency(total)}`}
        <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}