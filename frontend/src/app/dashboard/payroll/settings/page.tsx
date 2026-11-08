/**
 * Paramètres de paie — taux et barèmes par défaut (configurables).
 *
 * Ces valeurs alimentent le moteur de calcul (SMIG, taux CNPS, plafond, RICF,
 * exonération transport) et le barème ITS appliqué à la structure de paie.
 */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import {
  useApplyPayrollSettings,
  usePayrollSettings,
  useUpdatePayrollSettings,
} from "@/hooks/usePayroll";
import type { PayrollSettings } from "@/lib/types";

const inputCls =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";

const FIELDS: { key: keyof PayrollSettings; label: string; step?: string }[] = [
  { key: "smig", label: "SMIG mensuel (FCFA)" },
  { key: "cnps_salary_rate", label: "Taux CNPS salarié (%)", step: "0.01" },
  { key: "cnps_employer_rate", label: "Taux CNPS patronal (%)", step: "0.01" },
  { key: "cnps_ceiling_multiple", label: "Plafond CNPS (× SMIG)" },
  { key: "ricf_per_half_part", label: "RICF par demi-part (FCFA)" },
  { key: "transport_exempt", label: "Exonération transport (FCFA)" },
];

export default function PayrollSettingsPage() {
  const { data: settings, isLoading } = usePayrollSettings();
  const update = useUpdatePayrollSettings();
  const apply = useApplyPayrollSettings();

  const [form, setForm] = useState<Record<string, number>>({});
  const [brackets, setBrackets] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!settings) return;
    setForm({
      smig: settings.smig,
      cnps_salary_rate: settings.cnps_salary_rate,
      cnps_employer_rate: settings.cnps_employer_rate,
      cnps_ceiling_multiple: settings.cnps_ceiling_multiple,
      ricf_per_half_part: settings.ricf_per_half_part,
      transport_exempt: settings.transport_exempt,
    });
    setBrackets(JSON.stringify(settings.its_brackets, null, 2));
  }, [settings]);

  const save = async () => {
    setError(null);
    setNotice(null);
    let its_brackets;
    try {
      its_brackets = JSON.parse(brackets);
    } catch {
      setError("Le barème ITS doit être un JSON valide.");
      return;
    }
    try {
      await update.mutateAsync({ ...form, its_brackets } as Partial<PayrollSettings>);
      setNotice("Paramètres enregistrés. Cliquez sur « Appliquer » pour mettre à jour la structure.");
    } catch (err) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Échec de l'enregistrement.",
      );
    }
  };

  const applyNow = async () => {
    setError(null);
    setNotice(null);
    try {
      await apply.mutateAsync();
      setNotice("Structure de paie mise à jour avec les paramètres courants.");
    } catch (err) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Échec de l'application.",
      );
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Paramètres de paie"
        subtitle="Taux, plafonds et barème ITS par défaut. Modifiables sans code."
      />
      {error && (
        <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
      )}
      {notice && (
        <div className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      {isLoading ? (
        <div className="text-sm text-slate-500">Chargement…</div>
      ) : (
        <>
          <Card className="p-5">
            <h3 className="mb-4 text-base font-semibold">Taux et plafonds</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {FIELDS.map((field) => (
                <div key={String(field.key)}>
                  <label className="mb-1 block text-xs text-slate-500">
                    {field.label}
                  </label>
                  <input
                    className={inputCls}
                    type="number"
                    step={field.step}
                    value={form[String(field.key)] ?? 0}
                    onChange={(e) =>
                      setForm({ ...form, [String(field.key)]: Number(e.target.value) })
                    }
                  />
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="mb-2 text-base font-semibold">Barème ITS (JSON)</h3>
            <p className="mb-2 text-xs text-slate-500">
              Tranches mensuelles : liste d'objets {"{ \"up_to\": montant, \"rate\": %} ;"}
              {" "}le dernier palier utilise <code>up_to: null</code>.
            </p>
            <textarea
              className={`${inputCls} font-mono`}
              rows={10}
              value={brackets}
              onChange={(e) => setBrackets(e.target.value)}
            />
          </Card>

          <div className="flex gap-3">
            <Button onClick={save} disabled={update.isPending}>
              Enregistrer
            </Button>
            <Button variant="outline" onClick={applyNow} disabled={apply.isPending}>
              Appliquer à la structure
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
