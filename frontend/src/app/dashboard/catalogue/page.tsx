/**
 * Page Catalogue — liste des produits et accès à la création/édition.
 *
 * Le mode de vente (unité / mètre linéaire / dual) est dérivé de la
 * catégorie choisie — jamais saisissable manuellement.
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Plus, Package, Upload } from "lucide-react";
import { BarcodeScanner } from "@/components/catalogue/barcode-scanner";
import { apiClient } from "@/lib/api/client";
import { attachHidScanner } from "@/lib/hid-scanner";
import type { Product } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ImportDialog } from "@/components/shared/import-dialog";
import { ExportButton } from "@/components/shared/export-button";
import { CATALOGUE_KEYS, useProducts } from "@/hooks/useCatalogue";
import { formatCurrency } from "@/lib/utils";

const SALE_MODE_LABELS: Record<string, { label: string; cls: string }> = {
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

export default function CataloguePage() {
  const router = useRouter();
  const { data: products = [], isLoading } = useProducts();
  const [importOpen, setImportOpen] = useState(false);
  const [scanMsg, setScanMsg] = useState<string | null>(null);

  const handleScanLookup = async (code: string) => {
    try {
      const res = await apiClient.get(
        `/catalogue/products/lookup?code=${encodeURIComponent(code)}`
      );
      if (res.data?.found && res.data.product) {
        router.push(`/dashboard/catalogue/${res.data.product.id}`);
      } else {
        setScanMsg(`Aucun produit pour le code « ${code} » — créez-le avec ce code-barres.`);
        setTimeout(() => setScanMsg(null), 6000);
      }
    } catch {
      setScanMsg("Erreur lors de la recherche du code.");
    }
  };

  // Scan AIDC (douchette USB / terminal) — marche sans focus sur un champ.
  useEffect(() => {
    return attachHidScanner(handleScanLookup);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Catalogue</h1>
          <p className="text-sm text-gray-600">
            Le mode de vente est défini par la catégorie
          </p>
        </div>
        <div className="flex items-center gap-2">
          <BarcodeScanner
            label="Scanner un produit"
            onScan={handleScanLookup}
          />
          <ExportButton endpoint="/catalogue/products/export" fallbackName="produits" />
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={() => setImportOpen(true)}
          >
            <Upload className="h-4 w-4" />
            Importer
          </Button>
          <Link href="/dashboard/catalogue/new">
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nouveau produit
            </Button>
          </Link>
        </div>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        endpoint="/catalogue/products/import"
        title="Importer des produits"
        columnsHint="reference, nom, categorie, prix_achat, prix_vente, prix_ml, unite, vente_au_metre (oui/non), marque, code_barre"
        invalidateKeys={[CATALOGUE_KEYS.products]}
      />

      {scanMsg && (
        <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">{scanMsg}</div>
      )}

      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : products.length === 0 ? (
          <div className="p-10 text-center">
            <Package className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="text-sm text-gray-500">Aucun produit.</p>
            <Link href="/dashboard/catalogue/new" className="mt-3 inline-block">
              <Button size="sm">Créer le premier produit</Button>
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Produit</th>
                <th className="px-4 py-3">Réf.</th>
                <th className="px-4 py-3">Mode de vente</th>
                <th className="px-4 py-3 text-center">Variantes</th>
                <th className="px-4 py-3 text-right">Prix unité</th>
                <th className="px-4 py-3 text-right">Prix / ml</th>
                <th className="px-4 py-3 text-right">Pièce std</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => {
                const sm = SALE_MODE_LABELS[p.sale_mode ?? "unit"];
                return (
                  <tr
                    key={p.id}
                    onClick={() => router.push(`/dashboard/catalogue/${p.id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">
                      {p.name}{" "}
                      {(() => {
                        const b = STORAGE_TYPE_BADGES[p.storage_type];
                        return b ? (
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${b.cls}`}>{b.label}</span>
                        ) : null;
                      })()}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{p.reference}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${sm?.cls ?? "bg-gray-100"}`}>
                        {sm?.label ?? p.sale_mode}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600">
                      {p.variants_count ? (
                        <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                          {p.variants_count}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {p.selling_price ? formatCurrency(p.selling_price) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {p.price_per_meter ? formatCurrency(p.price_per_meter) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {p.unit_length ? `${p.unit_length} m` : "—"}
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
