/**
 * Périodes de paie & lots de bulletins — création, génération, validation, paiement.
 */
"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import {
  useCreatePeriod,
  useGenerateRun,
  usePayRun,
  usePayrollPeriods,
  useValidateRun,
} from "@/hooks/usePayroll";
import { formatDate } from "@/lib/utils";
import type { PayrollRun } from "@/lib/types";

function apiDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const inputCls =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";

const RUN_STATE: Record<string, string> = {
  draft: "Brouillon",
  validated: "Validé",
  paid: "Payé",
  cancelled: "Annulé",
};

export default function RunsPage() {
  const { data: periods = [], isLoading } = usePayrollPeriods();
  const createPeriod = useCreatePeriod();
  const generateRun = useGenerateRun();
  const validateRun = useValidateRun();
  const payRun = usePayRun();

  const [form, setForm] = useState({
    name: "",
    date_start: "",
    date_end: "",
    payment_date: "",
  });
  const [runs, setRuns] = useState<Record<number, PayrollRun>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
    } catch (err) {
      setError(apiDetail(err, "Action impossible."));
    }
  };

  const submitPeriod = async () => {
    if (!form.name || !form.date_start || !form.date_end) {
      setError("Nom, début et fin de période sont obligatoires.");
      return;
    }
    await run(async () => {
      await createPeriod.mutateAsync({
        name: form.name,
        date_start: form.date_start,
        date_end: form.date_end,
        payment_date: form.payment_date || null,
      });
      setForm({ name: "", date_start: "", date_end: "", payment_date: "" });
    });
  };

  const generate = (periodId: number) =>
    run(async () => {
      const created = await generateRun.mutateAsync(periodId);
      setRuns((prev) => ({ ...prev, [periodId]: created }));
      setNotice(`Lot ${created.reference} généré pour la période.`);
    });

  const validate = (periodId: number, runId: number) =>
    run(async () => {
      const updated = await validateRun.mutateAsync(runId);
      setRuns((prev) => ({ ...prev, [periodId]: updated }));
    });

  const pay = (periodId: number, runId: number) =>
    run(async () => {
      const updated = await payRun.mutateAsync(runId);
      setRuns((prev) => ({ ...prev, [periodId]: updated }));
    });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Périodes & lots de paie"
        subtitle="Créez une période puis générez le lot : un bulletin par contrat actif."
      />
      {error && (
        <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
      )}
      {notice && (
        <div className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      <Card className="p-5">
        <h3 className="mb-4 text-base font-semibold">Nouvelle période</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <input className={inputCls} placeholder="Nom (ex. Paie Janvier 2026)"
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={inputCls} type="date" value={form.date_start}
            onChange={(e) => setForm({ ...form, date_start: e.target.value })} />
          <input className={inputCls} type="date" value={form.date_end}
            onChange={(e) => setForm({ ...form, date_end: e.target.value })} />
          <input className={inputCls} type="date" value={form.payment_date}
            onChange={(e) => setForm({ ...form, payment_date: e.target.value })} />
        </div>
        <div className="mt-4">
          <Button onClick={submitPeriod} disabled={createPeriod.isPending}>
            Créer la période
          </Button>
        </div>
      </Card>

      <Card className="p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Chargement…</div>
        ) : periods.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">Aucune période.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Période</th>
                <th className="px-4 py-2">Du</th>
                <th className="px-4 py-2">Au</th>
                <th className="px-4 py-2">Lot</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {periods.map((p) => {
                const lot = runs[p.id];
                return (
                  <tr key={p.id} className="border-t border-slate-100">
                    <td className="px-4 py-2">{p.name}</td>
                    <td className="px-4 py-2">{formatDate(p.date_start)}</td>
                    <td className="px-4 py-2">{formatDate(p.date_end)}</td>
                    <td className="px-4 py-2">
                      {lot
                        ? `${lot.reference} — ${RUN_STATE[lot.state] ?? lot.state}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => generate(p.id)}>
                          Générer le lot
                        </Button>
                        {lot && lot.state === "draft" && (
                          <Button onClick={() => validate(p.id, lot.id)}>Valider</Button>
                        )}
                        {lot && lot.state === "validated" && (
                          <Button onClick={() => pay(p.id, lot.id)}>Payer</Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

