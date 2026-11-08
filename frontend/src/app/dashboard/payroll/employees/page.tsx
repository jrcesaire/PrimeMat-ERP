/**
 * Employés — registre du personnel.
 *
 * Le formulaire de création s'ouvre dans une **fenêtre modale** (bouton
 * « Nouveau salarié ») et comporte un libellé pour chaque champ, y compris les
 * paramètres de paie (salaire de base, structure) et la situation familiale
 * (qui détermine les parts fiscales / la RICF).
 */
"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/ui/page-header";
import {
  useApplyPayrollSettings,
  useCreateEmployee,
  useEmployees,
  usePayrollStructures,
} from "@/hooks/usePayroll";
import type { PayrollEmployeeCreate } from "@/lib/types";

function apiDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const MARITAL = [
  { value: "single", label: "Célibataire" },
  { value: "married", label: "Marié(e)" },
  { value: "divorced", label: "Divorcé(e)" },
  { value: "widowed", label: "Veuf(ve)" },
];

const inputCls =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";
const labelCls = "mb-1 block text-xs font-medium text-slate-600";

const EMPTY_FORM = {
  reference: "",
  first_name: "",
  last_name: "",
  job_title: "",
  marital_status: "single",
  dependents: "",
  cnps_number: "",
  structure_id: "",
  wage: "",
};

/** Parts fiscales estimées (barème ivoirien) — miroir de `derive_tax_parts`. */
function estimateParts(marital: string, dependents: string): number {
  const children = Math.max(0, Number(dependents) || 0);
  let base = 1;
  if (marital === "married" || marital === "widowed") base = 2;
  else if (children > 0) base = 1.5;
  return Math.min(base + 0.5 * children, 5);
}

export default function EmployeesPage() {
  const { data: employees = [], isLoading } = useEmployees();
  const { data: structures = [] } = usePayrollStructures();
  const createEmployee = useCreateEmployee();
  const applySettings = useApplyPayrollSettings();

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const set = (key: string, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async () => {
    setError(null);
    if (!form.first_name || !form.last_name) {
      setError("Prénom et nom sont obligatoires.");
      return;
    }
    if (!form.structure_id) {
      setError("Choisissez la structure de paie (jeu de règles applicable).");
      return;
    }
    const payload: PayrollEmployeeCreate = {
      // Matricule laissé vide → généré automatiquement (ordre d'entrée,
      // séquence « employee » de Paramètres → Séquences).
      reference: form.reference.trim() || undefined,
      first_name: form.first_name,
      last_name: form.last_name,
      job_title: form.job_title || undefined,
      marital_status: form.marital_status,
      dependents: Number(form.dependents) || 0,
      cnps_number: form.cnps_number || undefined,
      contract: {
        structure_id: Number(form.structure_id),
        wage: Number(form.wage) || 0,
      },
    };
    try {
      await createEmployee.mutateAsync(payload);
      setOpen(false);
      setForm({ ...EMPTY_FORM });
      setNotice(
        `Salarié « ${form.first_name} ${form.last_name} » créé avec son contrat.`,
      );
    } catch (err) {
      setError(apiDetail(err, "Erreur lors de la création du salarié."));
    }
  };

  const initStructure = async () => {
    setError(null);
    try {
      await applySettings.mutateAsync();
      setNotice("Structure de paie « Paie Côte d'Ivoire » créée.");
    } catch (err) {
      setError(apiDetail(err, "Impossible d'initialiser la structure de paie."));
    }
  };

  const parts = estimateParts(form.marital_status, form.dependents);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Employés"
        subtitle="Registre du personnel. Les paramètres de paie sont définis à la création."
        actions={
          <Button onClick={() => { setError(null); setOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Nouveau salarié
          </Button>
        }
      />

      {notice && (
        <div className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          {notice}
        </div>
      )}
      {error && !open && (
        <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
      )}

      {structures.length === 0 && (
        <Card className="border-amber-300 bg-amber-50 p-5">
          <h3 className="text-sm font-semibold text-amber-900">
            Aucune structure de paie
          </h3>
          <p className="mt-1 text-sm text-amber-800">
            Créez la structure par défaut (« Paie Côte d&apos;Ivoire » : barème ITS
            2026, CNPS plafonnée) pour pouvoir enregistrer des salariés.
          </p>
          <Button
            className="mt-3"
            onClick={initStructure}
            disabled={applySettings.isPending}
          >
            {applySettings.isPending ? "Initialisation…" : "Initialiser la structure de paie"}
          </Button>
        </Card>
      )}

      <Card className="p-0">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Chargement…</div>
        ) : employees.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            Aucun salarié enregistré. Cliquez sur « Nouveau salarié ».
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Matricule</th>
                <th className="px-4 py-2">Nom</th>
                <th className="px-4 py-2">Emploi</th>
                <th className="px-4 py-2">N° CNPS</th>
                <th className="px-4 py-2 text-right">Parts fiscales</th>
                <th className="px-4 py-2">Statut</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((emp) => (
                <tr key={emp.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-mono text-xs">{emp.reference}</td>
                  <td className="px-4 py-2">
                    {emp.full_name || `${emp.first_name} ${emp.last_name}`}
                  </td>
                  <td className="px-4 py-2">{emp.job_title || "—"}</td>
                  <td className="px-4 py-2">{emp.cnps_number || "—"}</td>
                  <td className="px-4 py-2 text-right">{emp.tax_parts ?? "—"}</td>
                  <td className="px-4 py-2">{emp.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nouveau salarié</DialogTitle>
            <DialogDescription>
              Identité, situation familiale et paramètres de paie (salaire de base
              et structure de règles).
            </DialogDescription>
          </DialogHeader>

          <div className="grid max-h-[60vh] gap-4 overflow-y-auto pr-1 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Matricule</label>
              <input className={inputCls} placeholder="généré automatiquement"
                value={form.reference}
                onChange={(e) => set("reference", e.target.value)} />
              <p className="mt-1 text-[11px] text-slate-400">
                Laisser vide pour une numérotation automatique (MAT-0001,
                MAT-0002…) — réglable dans Paramètres → Séquences.
              </p>
            </div>
            <div>
              <label className={labelCls}>Emploi</label>
              <input className={inputCls} placeholder="ex. Chef d'équipe"
                value={form.job_title}
                onChange={(e) => set("job_title", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Prénom *</label>
              <input className={inputCls} placeholder="ex. Koffi"
                value={form.first_name}
                onChange={(e) => set("first_name", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Nom *</label>
              <input className={inputCls} placeholder="ex. KOUASSI"
                value={form.last_name}
                onChange={(e) => set("last_name", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Situation familiale</label>
              <select className={inputCls} value={form.marital_status}
                onChange={(e) => set("marital_status", e.target.value)}>
                {MARITAL.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>
                Personnes à charge (nombre d&apos;enfants)
              </label>
              <input className={inputCls} type="number" min={0} placeholder="ex. 2"
                value={form.dependents}
                onChange={(e) => set("dependents", e.target.value)} />
              <p className="mt-1 text-[11px] text-slate-400">
                +0,5 part fiscale par personne à charge (réduit l&apos;ITS).
              </p>
            </div>

            <div>
              <label className={labelCls}>N° CNPS</label>
              <input className={inputCls} placeholder="ex. 170002000001"
                value={form.cnps_number}
                onChange={(e) => set("cnps_number", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Structure de paie *</label>
              <select className={inputCls} value={form.structure_id}
                onChange={(e) => set("structure_id", e.target.value)}>
                <option value="">— Choisir —</option>
                {structures.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <p className="mt-1 text-[11px] text-slate-400">
                Jeu de règles de calcul (barème ITS, CNPS) appliqué au salarié.
              </p>
            </div>
            <div>
              <label className={labelCls}>
                Salaire de base mensuel (brut, FCFA)
              </label>
              <input className={inputCls} type="number" min={0} placeholder="ex. 150000"
                value={form.wage}
                onChange={(e) => set("wage", e.target.value)} />
              <p className="mt-1 text-[11px] text-slate-400">
                Montant de base imposable, avant primes et retenues.
              </p>
            </div>
            <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600 sm:col-span-2">
              Parts fiscales estimées : <b>{parts}</b> — RICF correspondante&nbsp;:{" "}
              <b>{((parts - 1) * 11000).toLocaleString("fr-FR")} FCFA</b>
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Annuler</Button>
            </DialogClose>
            <Button onClick={submit} disabled={createEmployee.isPending}>
              {createEmployee.isPending ? "Création…" : "Créer le salarié"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

