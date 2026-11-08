/**
 * Onglet Paramètres → Séquences.
 *
 * N'affiche que les séquences **en vigueur** : les types réellement définis par
 * la nomenclature (`doc_nomenclature`) et rattachés à un module **actif** —
 * aucune liste statique. Pour chacune : la règle appliquée (préfixe, longueur
 * de série, réinitialisation, suffixe), le **dernier numéro émis** et la
 * **prochaine référence**.
 *
 * Le filigrane et les CGV restent dans l'onglet « Documents ».
 */
"use client";
import { NumberInput } from "@/components/ui/number-input";

import { useEffect, useState } from "react";
import { Hash, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useModuleStates } from "@/hooks/useModules";
import {
  DEFAULT_NOMENCLATURE,
  DOC_MODEL_LABELS,
  MODEL_MODULE,
  useNomenclature,
  useSaveNomenclature,
  useSequences,
  previewReference,
  type DocNomenclature,
} from "@/hooks/useNomenclature";

const RESET_OPTIONS: { value: DocNomenclature["reset"]; label: string }[] = [
  { value: "never", label: "Jamais" },
  { value: "month", label: "Mensuel" },
  { value: "quarter", label: "Trimestriel" },
  { value: "semester", label: "Semestriel" },
  { value: "year", label: "Annuel" },
];

const SUFFIX_OPTIONS: { value: DocNomenclature["suffix_type"]; label: string }[] = [
  { value: "none", label: "Aucun" },
  { value: "mmaa", label: "MMAA (ex. 2609)" },
  { value: "aaaa", label: "AAAA (ex. 2026)" },
  { value: "custom", label: "Personnalisé" },
];

export function SequencesTab() {
  const { data: config, isLoading } = useNomenclature();
  const { data: sequences = [], isLoading: loadingSequences } = useSequences();
  const { data: moduleStates } = useModuleStates();
  const save = useSaveNomenclature();
  const [draft, setDraft] = useState<Record<string, DocNomenclature>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) setDraft({ ...config });
  }, [config]);

  // Modules actifs — `null` tant que la liste n'est pas chargée : on n'applique
  // alors aucun filtre, pour ne pas masquer les séquences au premier rendu.
  const activeModules = moduleStates
    ? new Set(
        moduleStates
          .filter((m) => m.is_active && m.status === "active")
          .map((m) => m.name),
      )
    : null;

  /** Séquences en vigueur : définies, et rattachées à un module actif. */
  const visible = sequences.filter((entry) => {
    const module = MODEL_MODULE[entry.model];
    return !module || !activeModules || activeModules.has(module);
  });

  const update = (model: string, patch: Partial<DocNomenclature>) =>
    setDraft((d) => ({
      ...d,
      [model]: { ...DEFAULT_NOMENCLATURE, ...d[model], ...patch },
    }));

  const handleSave = async () => {
    setSaved(false);
    await save.mutateAsync(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const loading = isLoading || loadingSequences;

  return (
    <Card className="p-6">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
        <Hash className="h-5 w-5 text-blue-600" />
        Séquences en vigueur
      </h2>
      <p className="mb-5 text-sm text-muted">
        Format : <span className="font-mono">PRÉFIXE-SERIE-SUFFIXE</span> — ex.{" "}
        <span className="font-mono">MAT-0001</span> (matricule d&apos;un salarié) ou{" "}
        <span className="font-mono">FAC-000123-2609</span>. Seules les séquences
        réellement utilisées par les modules <strong>activés</strong> sont listées.
      </p>
      {loading ? (
        <p className="flex items-center gap-2 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
        </p>
      ) : visible.length === 0 ? (
        <p className="text-sm text-muted">
          Aucune séquence en vigueur : activez les modules concernés ou définissez
          une nomenclature.
        </p>
      ) : (
        <div className="space-y-4">
          {visible.map((entry) => {
            const key = entry.model;
            const cfg = { ...DEFAULT_NOMENCLATURE, ...draft[key] };
            const label = DOC_MODEL_LABELS[key] ?? key;
            return (
              <div key={key} className="rounded-lg border border-line p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-ink">{label}</h3>
                  <div className="flex flex-wrap items-center gap-2">
                    {entry.in_use ? (
                      <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                        Dernier n° émis : {entry.last_number}
                      </span>
                    ) : (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        Prête — aucun numéro émis
                      </span>
                    )}
                    <span className="rounded-md bg-blue-50 px-3 py-1 font-mono text-sm text-blue-700">
                      Prochaine : {entry.next_reference || previewReference(cfg)}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted">
                      Préfixe
                    </label>
                    <Input
                      value={cfg.prefix}
                      onChange={(e) =>
                        update(key, { prefix: e.target.value.toUpperCase() })
                      }
                      placeholder="DEV"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted">
                      Longueur de la série
                    </label>
                    <NumberInput
                      min={3}
                      max={8}
                      value={cfg.padding}
                      onChange={(v) => update(key, { padding: v || 6 })}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted">
                      Réinitialisation
                    </label>
                    <select
                      className="w-full rounded-md border border-line px-3 py-2 text-sm"
                      value={cfg.reset}
                      onChange={(e) =>
                        update(key, {
                          reset: e.target.value as DocNomenclature["reset"],
                        })
                      }
                    >
                      {RESET_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-muted">
                      Suffixe
                    </label>
                    <select
                      className="w-full rounded-md border border-line px-3 py-2 text-sm"
                      value={cfg.suffix_type}
                      onChange={(e) =>
                        update(key, {
                          suffix_type: e.target
                            .value as DocNomenclature["suffix_type"],
                        })
                      }
                    >
                      {SUFFIX_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {cfg.suffix_type === "custom" && (
                  <div className="mt-3 max-w-xs">
                    <label className="mb-1 block text-xs font-medium text-muted">
                      Suffixe personnalisé
                    </label>
                    <Input
                      value={cfg.suffix_custom}
                      onChange={(e) => update(key, { suffix_custom: e.target.value })}
                      placeholder="GEA"
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-5 flex items-center gap-3">
        <Button onClick={handleSave} disabled={save.isPending || loading}>
          {save.isPending ? "Enregistrement…" : "Enregistrer les séquences"}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">
            Séquences enregistrées ✓ — appliquées aux prochains numéros.
          </span>
        )}
      </div>
    </Card>
  );
}

