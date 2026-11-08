/**
 * Bulletins de paie — calcul, validation, impression (PDF).
 */
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import {
  useAddPayslipInput,
  useComputePayslip,
  usePayslips,
  useValidatePayslip,
} from "@/hooks/usePayroll";
import { printPayslip } from "@/lib/api/pdf";
import { formatCurrency, formatDate } from "@/lib/utils";

function apiDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const STATE_LABEL: Record<string, string> = {
  draft: "Brouillon",
  verify: "À valider",
  done: "Validé",
  paid: "Payé",
  cancelled: "Annulé",
};

export default function PayslipsPage() {
  const { data: payslips = [], isLoading } = usePayslips();
  const compute = useComputePayslip();
  const validate = useValidatePayslip();
  const addInput = useAddPayslipInput();
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(apiDetail(err, "Action impossible."));
    }
  };

  const addPrime = async (id: number) => {
    const code = window.prompt("Code de l'élément variable (ex. PRIME_TRANSPORT)");
    if (!code) return;
    const label = window.prompt("Libellé") || code;
    const amount = Number(window.prompt("Montant (FCFA)") || "0");
    await run(() => addInput.mutateAsync({ id, input_code: code, name: label, amount }));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bulletins de paie"
        subtitle="Calculez, validez et imprimez les bulletins. Un bulletin validé est comptabilisé."
      />
      {error && (
        <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
      )}

      <Card className="p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Chargement…</div>
        ) : payslips.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            Aucun bulletin. Générez un lot depuis « Périodes &amp; lots ».
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">N°</th>
                <th className="px-4 py-2">Période</th>
                <th className="px-4 py-2 text-right">Brut</th>
                <th className="px-4 py-2 text-right">Retenues</th>
                <th className="px-4 py-2 text-right">Net</th>
                <th className="px-4 py-2">État</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {payslips.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-mono text-xs">{p.number}</td>
                  <td className="px-4 py-2">
                    {formatDate(p.date_from)} → {formatDate(p.date_to)}
                  </td>
                  <td className="px-4 py-2 text-right">{formatCurrency(p.gross)}</td>
                  <td className="px-4 py-2 text-right">
                    {formatCurrency(p.total_deductions)}
                  </td>
                  <td className="px-4 py-2 text-right font-semibold">
                    {formatCurrency(p.net_wage)}
                  </td>
                  <td className="px-4 py-2">{STATE_LABEL[p.state] ?? p.state}</td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        onClick={() => run(() => compute.mutateAsync(p.id))}
                        disabled={p.state === "done" || p.state === "paid"}
                      >
                        Calculer
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => addPrime(p.id)}
                        disabled={p.state === "done" || p.state === "paid"}
                      >
                        + Prime
                      </Button>
                      <Button
                        onClick={() => run(() => validate.mutateAsync(p.id))}
                        disabled={p.state === "done" || p.state === "paid"}
                      >
                        Valider
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => run(() => printPayslip(p.id))}
                        disabled={p.state === "draft"}
                      >
                        Bulletin
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <p className="text-xs text-slate-400">
        Le bulletin est généré au format PDF (A4). Ajoutez les primes/indemnités
        imposables via « + Prime » avant validation.
      </p>
    </div>
  );
}
