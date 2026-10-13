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
import { BarcodeScanner } from "@/components/catalogue/barcode-scanner";

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
  const [isStock, setIsStock] = useState(true);       // Quincaillerie (en stock)
  const [isProduction, setIsProduction] = useState(false); // Production (a produire)
  const [barcode, setBarcode] = useState("");
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
    setBarcode(existing.barcode ?? "");
    const st = existing.storage_type ?? "stockable";
    setIsStock(st === "stockable" || st === "hybrid");
    setIsProduction(st === "on_demand" || st === "hybrid");
  }, [existing, loaded]);

  const selectedCat = categories.find((c) => c.id === categoryId) ?? null;
  const mode = selectedCat?.saleMode ?? "unit";

  const handleSave = async () => {
    setError(null);
    if (!name.trim()) return setError("Nom du produit requis.");
    if (!categoryId) return setError("Choisissez une catégorie.");
    if (!isStock && !isProduction)
      return setError("Cochez au moins un type : Quincaillerie et/ou Production.");
    const storage_type = isStock && isProduction ? "hybrid" : isProduction ? "on_demand" : "stockable";
    const data = {
      name: name.trim(),
      category_id: categoryId,
      storage_type,
      barcode: barcode.trim() || undefined,
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

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Type de produit *</label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-gray-300 p-3 hover:border-primary">
              <input
                type="checkbox"
                checked={isStock}
                onChange={(e) => setIsStock(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900">Quincaillerie</span>
                <span className="block text-xs text-gray-500">En stock — vendu depuis le stock</span>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-gray-300 p-3 hover:border-primary">
              <input
                type="checkbox"
                checked={isProduction}
                onChange={(e) => setIsProduction(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900">Production</span>
                <span className="block text-xs text-gray-500">Pas en stock — nécessite production</span>
              </span>
            </label>
          </div>
          {(isStock || isProduction) && (
            <p className="mt-1 text-xs text-gray-500">
              Type enregistré :{" "}
              <strong>
                {isStock && isProduction ? "Stock + Production (hybride)" : isProduction ? "Production (sur commande)" : "Quincaillerie (en stock)"}
              </strong>
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">Code-barres / QR (optionnel)</label>
            <Input
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="Scanner le code du fabricant ou saisir manuellement"
            />
          </div>
          <div className="flex items-end">
            <BarcodeScanner
              label="Scanner"
              className="w-full"
              onScan={(code) => setBarcode(code)}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500">
          Sans code-barres, une référence système (PRD-XXXXXX) est générée automatiquement.
        </p>

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