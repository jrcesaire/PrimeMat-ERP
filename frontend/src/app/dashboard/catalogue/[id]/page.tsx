/**
 * Détail d'un produit — lecture + lien d'édition.
 */
"use client";

import Link from "next/link";
import { use } from "react";
import { ArrowLeft, Pencil } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useProduct, useCategoryTree } from "@/hooks/useCatalogue";
import { VariantsSection } from "@/components/catalogue/variants-section";
import { formatCurrency } from "@/lib/utils";

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
      flattenTree(
        n.children as typeof nodes,
        depth + 1,
        out
      );
  }
  return out;
}

const MODE_LABELS: Record<string, { label: string; cls: string }> = {
  unit: { label: "À l'unité", cls: "bg-gray-100 text-gray-700" },
  length: { label: "Au mètre (BAC)", cls: "bg-blue-100 text-blue-700" },
  dual: { label: "Unité + mètre", cls: "bg-purple-100 text-purple-700" },
};

const STORAGE_TYPE_BADGES: Record<string, { label: string; cls: string }> = {
  stockable: { label: "En stock", cls: "bg-emerald-100 text-emerald-700" },
  on_demand: { label: "Production", cls: "bg-orange-100 text-orange-700" },
  hybrid: { label: "Stock + Production", cls: "bg-violet-100 text-violet-700" },
  service: { label: "Service", cls: "bg-gray-100 text-gray-600" },
};

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: idParam } = use(params);
  const id = Number(idParam) || 0;
  const { data: product, isLoading } = useProduct(id);
  const { data: tree = [] } = useCategoryTree();

  if (isLoading)
    return <p className="p-6 text-sm text-gray-500">Chargement…</p>;
  if (!product)
    return (
      <p className="p-6 text-sm text-gray-500">
        Produit introuvable (ou accès refusé).
      </p>
    );

  const cats = flattenTree(tree as never as { id: number; name: string; children?: unknown[] }[]);
  const category = cats.find((c) => c.id === product.category_id);
  const mode = MODE_LABELS[product.sale_mode] ?? MODE_LABELS.unit;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/dashboard/catalogue" className="text-sm text-gray-500 hover:text-primary">
            <ArrowLeft className="mr-1 inline h-4 w-4" /> Retour au catalogue
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{product.name}</h1>
          <p className="text-sm text-gray-600">
            {product.reference}
            {category ? ` · ${category.name}` : ""}
          </p>
        </div>
        <Link href={`/dashboard/catalogue/new?id=${product.id}`}>
          <Button variant="outline" className="flex items-center gap-2">
            <Pencil className="h-4 w-4" /> Modifier
          </Button>
        </Link>
      </div>

      <Card className="grid grid-cols-2 gap-6 p-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-gray-500">Mode de vente</p>
          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${mode.cls}`}>
            {mode.label}
          </span>
        </div>
        <div>
          <p className="text-xs text-gray-500">Type</p>
          {(() => {
            const b = STORAGE_TYPE_BADGES[product.storage_type] ?? STORAGE_TYPE_BADGES.stockable;
            return (
              <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${b.cls}`}>
                {b.label}
              </span>
            );
          })()}
        </div>
        <div>
          <p className="text-xs text-gray-500">Statut</p>
          <p className="text-sm font-medium text-gray-900">
            {product.status === "active" ? "Actif" : product.status}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Code-barres</p>
          <p className="text-sm font-medium text-gray-900">
            {product.barcode ?? "—"}
          </p>
        </div>
      </Card>

      <Card className="grid grid-cols-1 gap-6 p-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-gray-500">Prix de vente unitaire</p>
          <p className="text-lg font-bold text-gray-900">
            {product.selling_price != null && product.selling_price > 0
              ? formatCurrency(product.selling_price)
              : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Prix au mètre linéaire</p>
          <p className="text-lg font-bold text-gray-900">
            {product.price_per_meter != null && product.price_per_meter > 0
              ? formatCurrency(product.price_per_meter)
              : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">
            {product.sale_mode === "dual" ? "Longueur standard pièce" : "Longueur standard"}
          </p>
          <p className="text-lg font-bold text-gray-900">
            {product.unit_length != null ? `${product.unit_length} m` : "—"}
          </p>
        </div>
      </Card>

      <VariantsSection
        productId={product.id}
        productPrice={product.selling_price ?? null}
      />

      {product.description && (
        <Card className="p-4">
          <p className="text-xs text-gray-500">Description</p>
          <p className="mt-1 text-sm text-gray-700">{product.description}</p>
        </Card>
      )}
    </div>
  );
}