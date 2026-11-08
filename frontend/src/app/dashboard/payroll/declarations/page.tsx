/**
 * Déclarations CNPS & ITS par période de paie.
 */
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import {
  useCnpsDeclaration,
  useItsDeclaration,
  usePayrollPeriods,
} from "@/hooks/usePayroll";
import { printCnpsReturn, printItsReturn } from "@/lib/api/pdf";
import { formatCurrency } from "@/lib/utils";

const inputCls =
  "rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";

export default function DeclarationsPage() {
  const { data: periods = [] } = usePayrollPeriods();
  const [periodId, setPeriodId] = useState<number | null>(null);
  const { data: cnps } = useCnpsDeclaration(periodId);
  const { data: its } = useItsDeclaration(periodId);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Déclarations CNPS & ITS"
        subtitle="Bordereau des cotisations sociales et état de l'impôt sur salaires, par période."
      />

      <Card className="flex flex-wrap items-end gap-3 p-5">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Période de paie</label>
          <select
            className={inputCls}
            value={periodId ?? ""}
            onChange={(e) => setPeriodId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Sélectionner —</option>
            {periods.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <Button
          variant="outline"
          disabled={!periodId}
          onClick={() => periodId && printCnpsReturn(periodId)}
        >
          Bordereau CNPS (PDF)
        </Button>
        <Button
          variant="outline"
          disabled={!periodId}
          onClick={() => periodId && printItsReturn(periodId)}
        >
          État ITS (PDF)
        </Button>
      </Card>

      {cnps && (
        <Card className="p-0">
          <div className="border-b border-slate-100 px-5 py-3">
            <h3 className="font-semibold">Bordereau CNPS</h3>
            <p className="text-xs text-slate-500">
              Base cotisable : {formatCurrency(cnps.base)} — effectif :{" "}
              {cnps.employee_count} salarié(s).
            </p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Organisme</th>
                <th className="px-4 py-2 text-right">Part salariale</th>
                <th className="px-4 py-2 text-right">Part patronale</th>
                <th className="px-4 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {cnps.registers.map((reg) => (
                <tr key={reg.code} className="border-t border-slate-100">
                  <td className="px-4 py-2">{reg.name} <span className="text-slate-400">({reg.code})</span></td>
                  <td className="px-4 py-2 text-right">{formatCurrency(reg.employee)}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(reg.employer)}</td>
                  <td className="px-4 py-2 text-right font-semibold">{formatCurrency(reg.total)}</td>
                </tr>
              ))}
              <tr className="border-t border-slate-200 bg-slate-900 text-white">
                <td className="px-4 py-2 font-semibold">TOTAL À VERSER</td>
                <td className="px-4 py-2 text-right">{formatCurrency(cnps.employee_total)}</td>
                <td className="px-4 py-2 text-right">{formatCurrency(cnps.employer_total)}</td>
                <td className="px-4 py-2 text-right font-bold">{formatCurrency(cnps.grand_total)}</td>
              </tr>
            </tbody>
          </table>
        </Card>
      )}

      {its && (
        <Card className="p-0">
          <div className="border-b border-slate-100 px-5 py-3">
            <h3 className="font-semibold">État ITS</h3>
            <p className="text-xs text-slate-500">
              Total retenu : {formatCurrency(its.total_its)} sur {its.employee_count} salarié(s).
            </p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Salarié</th>
                <th className="px-4 py-2 text-right">Parts</th>
                <th className="px-4 py-2 text-right">Brut imposable</th>
                <th className="px-4 py-2 text-right">ITS net</th>
              </tr>
            </thead>
            <tbody>
              {its.lines.map((line) => (
                <tr key={line.employee_id} className="border-t border-slate-100">
                  <td className="px-4 py-2">{line.employee}</td>
                  <td className="px-4 py-2 text-right">{line.parts}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(line.gross)}</td>
                  <td className="px-4 py-2 text-right font-semibold">{formatCurrency(line.its)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {!periodId && (
        <p className="text-sm text-slate-400">
          Sélectionnez une période pour afficher les déclarations.
        </p>
      )}
    </div>
  );
}
