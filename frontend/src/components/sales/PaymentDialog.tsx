/**
 * PaymentDialog — fenêtre d'encaissement d'une facture
 * (étape 4 du parcours de vente).
 *
 * Choix intégral / partiel (boutons radio), date, montant, méthode
 * (espèces, Mobile Money, virement, chèque, carte) et journal comptable
 * (caisse, banque…). Après enregistrement, le reçu PDF est proposé
 * (téléchargement nommé + aperçu) via printReceipt().
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { Banknote } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCreatePayment, useJournals } from "@/hooks/useOperations";
import { printReceipt } from "@/lib/api/pdf";

interface PaymentDialogProps {
  open: boolean;
  onClose: () => void;
  invoiceId: number;
  partnerId: number;
  remaining: number;
  currency: string;
}

const METHODS = [
  { value: "cash", label: "Espèces" },
  { value: "mobile_money", label: "Mobile Money" },
  { value: "bank_transfer", label: "Virement" },
  { value: "check", label: "Chèque" },
  { value: "card", label: "Carte" },
];

/** Journal suggéré par défaut selon la méthode de paiement. */
function suggestedJournalCode(
  journals: { code: string; name: string }[],
  method: string
): string {
  const codes = new Set(journals.map((j) => j.code));
  if (method === "cash" && codes.has("CAI")) return "CAI";
  if (method === "bank_transfer" || method === "check" || method === "card") {
    if (codes.has("BAN")) return "BAN";
  }
  if (method === "mobile_money") {
    const mobile = journals.find((j) =>
      /mobile|money|momo|mtn|moov|wave|orange/i.test(`${j.code} ${j.name}`)
    );
    if (mobile) return mobile.code;
    if (codes.has("BAN")) return "BAN";
  }
  return [...codes][0] ?? "";
}

export function PaymentDialog(props: PaymentDialogProps) {
  return <PaymentDialogBody {...props} />;
}
function PaymentDialogBody({
  open,
  onClose,
  invoiceId,
  partnerId,
  remaining,
  currency,
}: PaymentDialogProps) {
  const createPayment = useCreatePayment();
  const { data: journals = [] } = useJournals();
  const [mode, setMode] = useState<"full" | "partial">("full");
  const [amount, setAmount] = useState("");
  const [payDate, setPayDate] = useState("");
  const [method, setMethod] = useState("cash");
  const [journalCode, setJournalCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [justPaidId, setJustPaidId] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      setMode("full");
      setAmount(String(remaining));
      setPayDate(new Date().toISOString().slice(0, 10));
      setMethod("cash");
      setError(null);
      setJustPaidId(null);
    }
  }, [open, remaining]);

  useEffect(() => {
    if (open && journals.length > 0) {
      setJournalCode((current) => {
        const known = journals.some((j) => j.code === current);
        if (current && known) return current;
        return suggestedJournalCode(journals, method);
      });
    }
  }, [open, journals, method]);

  const parsedAmount = useMemo(
    () => parseFloat(amount.replace(",", ".")),
    [amount]
  );
  const handleModeChange = (next: "full" | "partial") => {
    setMode(next);
    setError(null);
    if (next === "full") setAmount(String(remaining));
  };

  const handleSubmit = async () => {
    setError(null);
    if (!parsedAmount || parsedAmount <= 0) {
      return setError("Saisissez un montant positif.");
    }
    if (parsedAmount > remaining + 0.005) {
      return setError("Le montant dépasse le reste dû.");
    }
    if (!payDate) {
      return setError("Choisissez la date du paiement.");
    }
    try {
      const payment = await createPayment.mutateAsync({
        partner_id: partnerId,
        invoice_id: invoiceId,
        method,
        amount: parsedAmount,
        payment_date: payDate,
        journal_code: journalCode || undefined,
        direction: "in",
      });
      setJustPaidId(payment.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Erreur lors de l'enregistrement du paiement"
      );
    }
  };

  return (
    <div
      className={!open ? "hidden" : ""}
      role="presentation"
      onClick={onClose}
    >
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <PayOverlay
          onClose={onClose}
          remaining={remaining}
          currency={currency}
          error={error}
          justPaidId={justPaidId}
          mode={mode}
          onModeChange={handleModeChange}
          payDate={payDate}
          onPayDateChange={setPayDate}
          amount={amount}
          onAmountChange={setAmount}
          method={method}
          onMethodChange={setMethod}
          journalCode={journalCode}
          onJournalChange={setJournalCode}
          journals={journals}
          pending={createPayment.isPending}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
}

interface PayOverlayProps {
  onClose: () => void;
  remaining: number;
  currency: string;
  error: string | null;
  justPaidId: number | null;
  mode: "full" | "partial";
  onModeChange: (next: "full" | "partial") => void;
  payDate: string;
  onPayDateChange: (v: string) => void;
  amount: string;
  onAmountChange: (v: string) => void;
  method: string;
  onMethodChange: (v: string) => void;
  journalCode: string;
  onJournalChange: (v: string) => void;
  journals: { code: string; name: string }[];
  pending: boolean;
  onSubmit: () => void;
}

function PayOverlay(p: PayOverlayProps) {
  return (
    <div
      className="w-full max-w-md space-y-4 rounded-lg bg-white p-6 shadow-xl"
      onClick={(e) => e.stopPropagation()}
      role="dialog"
      aria-label="Enregistrer un paiement"
    >
      <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
        <Banknote className="h-5 w-5 text-green-600" />
        Enregistrer un paiement
      </h2>
      <p className="text-sm text-gray-600">
        Reste dû :{" "}
        <span className="font-semibold text-gray-900">
          {p.remaining} {p.currency}
        </span>
      </p>

      {p.error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">
          {p.error}
        </div>
      )}

      {p.justPaidId ? (
        <div className="space-y-3 rounded-md bg-green-50 p-4 text-sm text-green-800">
          <p className="font-medium">Paiement enregistré avec succès.</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => printReceipt(p.justPaidId as number)}>
              Imprimer le reçu
            </Button>
            <Button size="sm" variant="outline" onClick={p.onClose}>
              Fermer
            </Button>
          </div>
        </div>
      ) : (
        <>
          <fieldset className="text-sm">
            <legend className="mb-1 text-xs font-medium text-gray-600">
              Type de paiement
            </legend>
            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="pay-mode"
                  checked={p.mode === "full"}
                  onChange={() => p.onModeChange("full")}
                />
                Intégral
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="pay-mode"
                  checked={p.mode === "partial"}
                  onChange={() => p.onModeChange("partial")}
                />
                Partiel
              </label>
            </div>
          </fieldset>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600">
                Date
              </label>
              <input
                type="date"
                value={p.payDate}
                onChange={(e) => p.onPayDateChange(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">
                Montant
              </label>
              <input
                type="number"
                min="0"
                step="any"
                value={p.amount}
                readOnly={p.mode === "full"}
                onChange={(e) => p.onAmountChange(e.target.value)}
                placeholder={String(p.remaining)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              Méthode
            </label>
            <select
              value={p.method}
              onChange={(e) => p.onMethodChange(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              Journal comptable
            </label>
            {p.journals.length > 0 ? (
              <>
                <select
                  value={p.journalCode}
                  onChange={(e) => p.onJournalChange(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  {p.journals.map((j) => (
                    <option key={j.code} value={j.code}>
                      {j.code} — {j.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Registre où le paiement sera comptabilisé (caisse, banque…).
                </p>
              </>
            ) : (
              <p className="mt-1 text-xs text-gray-500">
                Journal déduit automatiquement du mode de paiement
                (comptabilisation automatique).
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={p.onClose}>
              Annuler
            </Button>
            <Button
              onClick={p.onSubmit}
              disabled={p.pending}
              className="bg-green-600 hover:bg-green-700"
            >
              {p.pending ? "Enregistrement…" : "Encaisser"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}


