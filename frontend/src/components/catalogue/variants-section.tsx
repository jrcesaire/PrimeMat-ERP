/**
 * Section Variantes d'un produit :
 * 1. Gestion des propriétés (Couleur, Finition...) et de leurs valeurs
 * 2. Génération des variantes (produit cartésien des valeurs cochées)
 * 3. Tableau des variantes — prix inline, défaut exclusif, activation
 */
"use client";

import { useState } from "react";
import { Plus, Trash2, X, Check, Loader2, Layers } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/lib/utils";
import { useConfirm, confirmDeleteOptions } from "@/components/ui/confirm";
import {
  useProperties,
  useVariants,
  useCreateProperty,
  useDeleteProperty,
  useAddPropertyValue,
  useDeletePropertyValue,
  useGenerateVariants,
  useUpdateVariant,
  useDeleteVariant,
} from "@/hooks/useCatalogue";
import type { ProductVariant } from "@/lib/types";

interface VariantsSectionProps {
  productId: number;
  productPrice: number | null;
}

export function VariantsSection({ productId, productPrice }: VariantsSectionProps) {
  const { data: properties = [], isLoading } = useProperties();
  const { data: variants = [] } = useVariants(productId);
  const confirm = useConfirm();

  const createProperty = useCreateProperty();
  const deleteProperty = useDeleteProperty();
  const addValue = useAddPropertyValue();
  const deleteValue = useDeletePropertyValue();
  const generate = useGenerateVariants();
  const updateVariant = useUpdateVariant();
  const deleteVariant = useDeleteVariant();

  const [newPropName, setNewPropName] = useState("");
  const [valueInputs, setValueInputs] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<Record<number, number[]>>({});

  const chosenCount = Object.entries(selected).filter(([, ids]) => ids.length > 0);
  const totalCombos = chosenCount.length
    ? chosenCount.reduce((acc, [, ids]) => acc * ids.length, 1)
    : 0;

  const toggleValue = (propId: number, valueId: number) => {
    setSelected((prev) => {
      const current = prev[propId] ?? [];
      return {
        ...prev,
        [propId]: current.includes(valueId)
          ? current.filter((id) => id !== valueId)
          : [...current, valueId],
      };
    });
  };

  const handleCreateProperty = async () => {
    const name = newPropName.trim();
    if (!name) return;
    try {
      await createProperty.mutateAsync({ name, values: [] });
      setNewPropName("");
    } catch {
      /* doublon : le libellé reste saisissable */
    }
  };

  const handleGenerate = async () => {
    if (!totalCombos) return;
    try {
      await generate.mutateAsync({ productId, values: selected });
      setSelected({});
    } catch {
      /* valeur invalide : sélection conservée */
    }
  };

  return (
    <div className="space-y-4">
      {/* ---------------- Propriétés & valeurs ---------------- */}
      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Layers className="h-4 w-4" /> Propriétés du produit
            </h3>
            <p className="text-xs text-gray-500">
              Ex. « Couleur » avec les valeurs Rouge, Vert, Gris foncé…
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              value={newPropName}
              onChange={(e) => setNewPropName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreateProperty()}
              placeholder="Nouvelle propriété (ex. Couleur)"
              className="h-9 w-56"
            />
            <Button
              size="sm"
              className="h-9"
              disabled={!newPropName.trim() || createProperty.isPending}
              onClick={handleCreateProperty}
            >
              <Plus className="h-4 w-4" /> Ajouter
            </Button>
          </div>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Chargement…</p>
        ) : properties.length === 0 ? (
          <p className="text-sm text-gray-500">
            Aucune propriété — créez-en une pour définir les variantes.
          </p>
        ) : (
          <div className="space-y-3">
            {properties.map((prop) => (
              <div key={prop.id} className="rounded-lg border border-gray-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{prop.name}</span>
                  <button
                    className="text-xs text-gray-400 hover:text-red-600"
                    onClick={async () => {
                      const { confirmed } = await confirm({
                        title: `Supprimer la propriété « ${prop.name} » ?`,
                        description:
                          "Les variantes concernées perdront cette caractéristique. Réaffectez-les si nécessaire.",
                        confirmLabel: "Supprimer",
                        cancelLabel: "Annuler",
                        tone: "danger",
                      });
                      if (confirmed) deleteProperty.mutate(prop.id);
                    }}
                  >
                    Supprimer
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {prop.values.map((v) => (
                    <span
                      key={v.id}
                      className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700"
                    >
                      {v.value}
                      <button
                        className="text-gray-400 hover:text-red-600"
                        onClick={() => deleteValue.mutate({ propertyId: prop.id, valueId: v.id })}
                        aria-label={`Supprimer ${v.value}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                  <Input
                    value={valueInputs[prop.id] ?? ""}
                    onChange={(e) => setValueInputs((p) => ({ ...p, [prop.id]: e.target.value }))}
                    onKeyDown={async (e) => {
                      if (e.key === "Enter") {
                        const val = (valueInputs[prop.id] ?? "").trim();
                        if (val) {
                          await addValue.mutateAsync({ propertyId: prop.id, value: val });
                          setValueInputs((p) => ({ ...p, [prop.id]: "" }));
                        }
                      }
                    }}
                    placeholder="Ajouter une valeur + Entrée"
                    className="h-7 w-44 text-xs"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ---------------- Génération ---------------- */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-gray-900">Générer les variantes</h3>
        <p className="text-xs text-gray-500">
          Cochez les valeurs à combiner — chaque combinaison crée une variante.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {properties.map((prop) => (
            <div key={prop.id} className="rounded-lg border border-gray-200 p-3">
              <p className="text-xs font-semibold uppercase text-gray-500">{prop.name}</p>
              <div className="mt-2 space-y-1.5">
                {prop.values.map((v) => (
                  <label key={v.id} className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={(selected[prop.id] ?? []).includes(v.id)}
                      onChange={() => toggleValue(prop.id, v.id)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    {v.value}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Button
            size="sm"
            disabled={!totalCombos || generate.isPending}
            onClick={handleGenerate}
          >
            {generate.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Générer {totalCombos > 0 ? `${totalCombos} variante${totalCombos > 1 ? "s" : ""}` : ""}
          </Button>
          <span className="text-xs text-gray-500">
            Les combinaisons existantes sont ignorées (aucun doublon).
          </span>
        </div>
      </Card>

      {/* ---------------- Tableau des variantes ---------------- */}
      <Card className="overflow-hidden p-0">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Variantes ({variants.length})
          </h3>
        </div>
        {variants.length === 0 ? (
          <p className="p-6 text-center text-sm text-gray-500">
            Aucune variante — générez-en depuis les propriétés ci-dessus.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-2">Réf.</th>
                <th className="px-4 py-2">Combinaison</th>
                <th className="px-4 py-2">Caractéristiques</th>
                <th className="px-4 py-2 text-right">Prix de vente</th>
                <th className="px-4 py-2 text-center">Défaut</th>
                <th className="px-4 py-2 text-center">Active</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {variants.map((v: ProductVariant) => (
                <tr key={v.id} className="border-b border-gray-100">
                  <td className="px-4 py-2 text-xs text-gray-500">{v.reference ?? "—"}</td>
                  <td className="px-4 py-2 font-medium text-gray-900">{v.name_suffix}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">
                    {v.properties.map((pp) => `${pp.property_name}: ${pp.value}`).join(" · ")}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <PriceCell
                      value={v.selling_price}
                      fallback={productPrice}
                      onSave={(price) => updateVariant.mutate({ id: v.id, data: { selling_price: price } })}
                    />
                  </td>
                  <td className="px-4 py-2 text-center">
                    <input
                      type="radio"
                      name={`variant-default-${productId}`}
                      checked={v.is_default}
                      onChange={() => updateVariant.mutate({ id: v.id, data: { is_default: true } })}
                      className="h-4 w-4"
                      aria-label={`Définir ${v.name_suffix} comme variante par défaut`}
                    />
                  </td>
                  <td className="px-4 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={v.is_active}
                      onChange={(e) => updateVariant.mutate({ id: v.id, data: { is_active: e.target.checked } })}
                      className="h-4 w-4 rounded border-gray-300"
                      aria-label={`Activer ${v.name_suffix}`}
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      className="text-gray-400 hover:text-red-600"
                      onClick={async () => {
                      const { confirmed } = await confirm(
                        confirmDeleteOptions(`la variante ${v.name_suffix}`),
                      );
                      if (confirmed) deleteVariant.mutate(v.id);
                    }}
                      aria-label={`Supprimer ${v.name_suffix}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

/** Cellule prix éditable — vide = prix du produit de base. */
function PriceCell({
  value,
  fallback,
  onSave,
}: {
  value: number | null;
  fallback: number | null;
  onSave: (price: number | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  if (editing) {
    return (
      <span className="inline-flex items-center gap-1">
        <Input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              const n = parseFloat(draft.replace(",", "."));
              onSave(isNaN(n) ? null : n);
              setEditing(false);
            } else if (e.key === "Escape") {
              setEditing(false);
            }
          }}
          className="h-8 w-24 text-right text-sm"
        />
        <button
          onClick={() => {
            const n = parseFloat(draft.replace(",", "."));
            onSave(isNaN(n) ? null : n);
            setEditing(false);
          }}
          className="text-green-600 hover:text-green-700"
          aria-label="Enregistrer"
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          onClick={() => setEditing(false)}
          className="text-gray-400 hover:text-gray-600"
          aria-label="Annuler"
        >
          <X className="h-4 w-4" />
        </button>
      </span>
    );
  }

  return (
    <button
      className="text-sm text-gray-900 hover:text-primary hover:underline"
      onClick={() => {
        setDraft(value != null ? String(value) : "");
        setEditing(true);
      }}
      title="Cliquer pour modifier le prix"
    >
      {value != null ? (
        formatCurrency(value)
      ) : fallback != null ? (
        <span className="text-gray-400">{formatCurrency(fallback)} (base)</span>
      ) : (
        "—"
      )}
    </button>
  );
}
