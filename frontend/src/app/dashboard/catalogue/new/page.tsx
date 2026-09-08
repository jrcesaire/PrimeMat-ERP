/**
 * Création / édition d'un produit — mode de vente dérivé de la catégorie.
 */
"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useCreateProduct,
  useUpdateProduct,
  useProduct,
  useCategoryTree,
} from "@/hooks/useCatalogue";

interface FlatCategory {
  id: number;
  name: string;
  saleMode: string;
  depth: number;
}

function flattenTree(
  nodes: { id: number; name: string; resolved_sale_mode?: string; sale_mode?: string; children?: unknown[] }[],
  depth = 0,
  out: FlatCategory[] = []
): FlatCategory[] {
  for (const n of nodes ?? []) {
    out.push({
      id: n.id,
      name: n.name,
      saleMode: n.resolved_sale_mode ?? n.sale_mode ?? "unit",
      depth,
    });
    if (n.children?.length)
      flattenTree(n.children as typeof nodes, depth + 1, out);
  }
  return out;
}

const SALE_MODE_LABELS: Record<string, string> = {
  unit: "À l'unité",
  length: "Au mètre (BAC)",
  dual: "Unité + mètre",
};

export default function NewProductPage() {
  return (
    <Suspense fallback={null}>
      <NewProductPageInner />
    </Suspense>
  );
}

function NewProductPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = Number(searchParams.get("id")) || null;
  const isEdit = !!editId;
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct();
  const { data: existing } = useProduct(editId ?? 0);
  const { data: tree = [] } = useCategoryTree();

  const categories = useMemo(
    () =>
      flattenTree(
        tree as never as { id: number; name: string; children?: unknown[] }[]
      ),
    [tree]
  );

  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [sellingPrice, setSellingPrice] = useState(0);
  const [pricePerMeter, setPricePerMeter] = useState(0);
  const [unitLength, setUnitLength] = useState(2.5);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Pré-remplissage en mode édition (une seule fois)
  useEffect(() => {
    if (!existing || loaded) return;
    setLoaded(true);
    setName(existing.name);
    setCategoryId(existing.category_id);
    setSellingPrice(existing.selling_price ?? 0);
    setPricePerMeter(existing.price_per_meter ?? 0);
    setUnitLength(existing.unit_length ?? 2.5);
  }, [existing, loaded]);

  const selectedCat = categories.find((c) => c.id === categoryId) ?? null;
  const mode = selectedCat?.saleMode ?? "unit";

  const handleSave = async () => {
    setError(null);
    if (!name.trim()) return setError("Nom du produit requis.");
    if (!categoryId) return setError("Choisissez une catégorie.");
    const data = {
      name: name.trim(),
      category_id: categoryId,
      selling_price: mode === "length" ? undefined : Number(sellingPrice),
      price_per_meter: mode === "unit" ? undefined : Number(pricePerMeter),
      unit_length: mode === "dual" ? Number(unitLength) : undefined,
    };
    try {
      if (isEdit) {
        await updateProduct.mutateAsync({ id: editId, data });
      } else {
        await createProduct.mutateAsync(data);
      }
      router.push("/dashboard/catalogue");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : `Erreur lors de ${isEdit ? "la modification" : "la création"}`
      );
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? "Modifier le produit" : "Nouveau produit"}
        </h1>
        <p className="text-sm text-gray-600">
          Le mode de vente est défini par la catégorie
        </p>
      </div>

      <Card className="space-y-4 p-4">
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Nom *</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Tôle BAC Alu 0,30" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Catégorie *</label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">— Choisir —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {"\u00A0".repeat(c.depth * 4)}
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedCat && (
          <p className="text-xs text-gray-500">
            Mode de vente hérité :{" "}
            <strong>{SALE_MODE_LABELS[mode] ?? mode}</strong>
          </p>
        )}

        {mode === "unit" && (
          <div className="w-48">
            <label className="mb-1 block text-sm font-medium text-gray-700">Prix de vente (pièce)</label>
            <Input type="number" min={0} value={sellingPrice} onChange={(e) => setSellingPrice(Number(e.target.value))} />
          </div>
        )}
        {(mode === "length" || mode === "dual") && (
          <div className="w-48">
            <label className="mb-1 block text-sm font-medium text-gray-700">Prix au mètre linéaire</label>
            <Input type="number" min={0} value={pricePerMeter} onChange={(e) => setPricePerMeter(Number(e.target.value))} />
          </div>
        )}
        {mode === "dual" && (
          <div className="w-48">
            <label className="mb-1 block text-sm font-medium text-gray-700">Longueur standard pièce (m)</label>
            <Input type="number" step="0.01" min={0} value={unitLength} onChange={(e) => setUnitLength(Number(e.target.value))} />
          </div>
        )}

        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={createProduct.isPending || updateProduct.isPending}>
            {createProduct.isPending || updateProduct.isPending
              ? "Enregistrement…"
              : isEdit
                ? "Enregistrer les modifications"
                : "Créer"}
          </Button>
          <Button variant="outline" onClick={() => router.push("/dashboard/catalogue")}>
            Annuler
          </Button>
        </div>
      </Card>
    </div>
  );
}