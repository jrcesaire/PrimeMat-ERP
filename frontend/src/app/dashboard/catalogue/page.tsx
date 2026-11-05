/**
 * Page Catalogue - liste des produits et accès à la création/édition.
 *
 * Le mode de vente (unité / mètre linéaire / dual) est dérivé de la
 * catégorie choisie - jamais saisissable manuellement.
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, Package, Plus, Upload } from "lucide-react";
import { BarcodeScanner } from "@/components/catalogue/barcode-scanner";
import { apiClient } from "@/lib/api/client";
import { attachHidScanner } from "@/lib/hid-scanner";
import type { Product } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ImportDialog } from "@/components/shared/import-dialog";
import { ExportButton } from "@/components/shared/export-button";
import { CATALOGUE_KEYS, useProducts } from "@/hooks/useCatalogue";
import { useStockLevels } from "@/hooks/useStock";
import { cn, formatCurrency, formatNumber, lastRouteSegment } from "@/lib/utils";

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
  const pathname = usePathname();
  // Sous-route « Scanner un produit » : la caméra s'ouvre dès l'arrivée.
  const autoScan = lastRouteSegment(pathname) === "scan";
  const { data: products = [], isLoading } = useProducts();

  // Quantités en stock de TOUS les articles en une seule requête : permet
  // d'afficher une disponibilité réelle (et non estimée) sur chaque tuile.
  const { data: stockLevels = [] } = useStockLevels();
  const stockByProduct = useMemo(() => {
    const map = new Map<number, number>();
    for (const level of stockLevels) {
      map.set(
        level.product_id,
        (map.get(level.product_id) ?? 0) + Number(level.available ?? 0),
      );
    }
    return map;
  }, [stockLevels]);
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
        setScanMsg(`Aucun produit pour le code « ${code} » - créez-le avec ce code-barres.`);
        setTimeout(() => setScanMsg(null), 6000);
      }
    } catch {
      setScanMsg("Erreur lors de la recherche du code.");
    }
  };

  // Scan AIDC (douchette USB / terminal) - marche sans focus sur un champ.
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
            autoOpen={autoScan}
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

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-[228px] animate-pulse rounded-card bg-subtle" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <EmptyState
          icon={Package}
          title="Aucun produit"
          description="Créez votre premier article ou importez votre catalogue existant."
          className="rounded-card border border-line bg-surface"
          action={
            <Link href="/dashboard/catalogue/new">
              <Button size="sm">Créer le premier produit</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {products.map((p) => {
            const sm = SALE_MODE_LABELS[p.sale_mode ?? "unit"];
            const storage = STORAGE_TYPE_BADGES[p.storage_type];
            const qty = stockByProduct.get(p.id);
            const tracked = qty !== undefined;
            const out = tracked && qty <= 0;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => router.push(`/dashboard/catalogue/${p.id}`)}
                className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4 text-left transition-colors hover:border-primary/40"
              >
                {/* Miniature + etat de disponibilite (stock reel) */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-control bg-subtle">
                    <Package className="h-6 w-6 text-muted" />
                  </div>
                  <span
                    className={cn(
                      "inline-flex shrink-0 items-center gap-1 rounded-chip px-2 py-0.5 text-[10px] font-medium",
                      !tracked
                        ? "bg-subtle text-muted"
                        : out
                          ? "bg-danger-soft text-danger"
                          : "bg-success-soft text-success",
                    )}
                  >
                    {!tracked ? (
                      "Stock non suivi"
                    ) : out ? (
                      <>
                        <AlertTriangle className="h-3 w-3" />
                        Rupture
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-3 w-3" />
                        Disponible
                      </>
                    )}
                  </span>
                </div>

                {/* Identification : reference, designation, badges */}
                <div className="min-w-0">
                  <p className="truncate text-[10px] uppercase tracking-wide text-faint">
                    {p.reference}
                  </p>
                  <p className="mt-0.5 line-clamp-2 text-[14px] font-semibold leading-snug text-ink">
                    {p.name}
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <span
                      className={cn(
                        "rounded-chip px-2 py-0.5 text-[10px] font-medium",
                        sm?.cls ?? "bg-subtle text-muted",
                      )}
                    >
                      {sm?.label ?? p.sale_mode}
                    </span>
                    {storage && (
                      <span
                        className={cn(
                          "rounded-chip px-2 py-0.5 text-[10px] font-medium",
                          storage.cls,
                        )}
                      >
                        {storage.label}
                      </span>
                    )}
                    {p.variants_count ? (
                      <span className="rounded-chip bg-primary-soft px-2 py-0.5 text-[10px] font-medium text-primary">
                        {p.variants_count} variante
                        {p.variants_count > 1 ? "s" : ""}
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Prix + quantite en stock */}
                <div className="mt-auto flex items-end justify-between gap-3 border-t border-line pt-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.08em] text-muted">
                      Prix
                    </p>
                    <p className="text-[15px] font-semibold tabular-nums text-ink">
                      {p.sell_by_length
                        ? `${formatCurrency(p.price_per_meter ?? 0)}/ml`
                        : formatCurrency(p.selling_price ?? 0)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase tracking-[0.08em] text-muted">
                      En stock
                    </p>
                    <p
                      className={cn(
                        "text-[15px] font-semibold tabular-nums",
                        out ? "text-danger" : "text-ink",
                      )}
                    >
                      {tracked ? formatNumber(qty) : "-"}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
