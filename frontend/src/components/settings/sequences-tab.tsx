/**
 * Onglet Paramètres → Séquences.
 *
 * Nomenclature des références par type : matricules employés, contrats,
 * bulletins, lots de paie, devis, commandes, factures, bons de livraison,
 * reçus, dépenses et écritures comptables. Chaque type définit un **préfixe**,
 * la **longueur de la série**, la **réinitialisation** (jamais / mensuelle /
 * trimestrielle / semestrielle / annuelle) et un **suffixe** (aucun / MMAA /
 * AAAA / personnalisé), avec aperçu de la prochaine référence.
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
import {
  DEFAULT_NOMENCLATURE,
  DOC_MODELS,
  useNomenclature,
  useSaveNomenclature,
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
  const save = useSaveNomenclature();
  const [draft, setDraft] = useState<Record<string, DocNomenclature>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) setDraft({ ...config });
  }, [config]);

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

  return (
    <Card className="p-6">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold">
        <Hash className="h-5 w-5 text-blue-600" />
        Nomenclature des séquences
      </h2>
      <p className="mb-5 text-sm text-muted">
        Format : <span className="font-mono">PRÉFIXE-SERIE-SUFFIXE</span> — ex.{" "}
        <span className="font-mono">MAT-0001</span> (matricule d&apos;un salarié) ou{" "}
        <span className="font-mono">FAC-000123-2609</span>. La série peut être
        réinitialisée périodiquement. Les matricules employés suivent l&apos;ordre
        d&apos;entrée.
      </p>
      {isLoading ? (
        <p className="flex items-center gap-2 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
        </p>
      ) : (
        <div className="space-y-4">
          {DOC_MODELS.map(({ key, label }) => {
            const cfg = { ...DEFAULT_NOMENCLATURE, ...draft[key] };
            return (
              <div key={key} className="rounded-lg border border-line p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-medium text-ink">{label}</h3>
                  <span className="rounded-md bg-blue-50 px-3 py-1 font-mono text-sm text-blue-700">
                    {previewReference(cfg)}
                  </span>
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
        <Button onClick={handleSave} disabled={save.isPending || isLoading}>
          {save.isPending ? "Enregistrement…" : "Enregistrer les séquences"}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">
            Séquences enregistrées ✓ — appliquées aux prochains documents.
          </span>
        )}
      </div>
    </Card>
  );
}

