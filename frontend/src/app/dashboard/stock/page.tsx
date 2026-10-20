/**
 * Page Stock — entrepôts, niveaux (réel / réservé / disponible), mouvements.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useWarehouses,
  useStockLevels,
  useStockMovements,
  useCreateWarehouse,
  useCreateMovement,
  STOCK_KEYS,
} from "@/hooks/useStock";
import { useProducts } from "@/hooks/useCatalogue";

export default function StockPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: warehouses = [] } = useWarehouses();
  const { data: levels = [], isLoading: loadingLevels } = useStockLevels();
  const { data: movements = [] } = useStockMovements(0, 30);
  const { data: products = [] } = useProducts();
  const createWarehouse = useCreateWarehouse();
  const createMovement = useCreateMovement();

  const [whName, setWhName] = useState("");
  const [mvProduct, setMvProduct] = useState<number | null>(null);
  const [mvWarehouse, setMvWarehouse] = useState<number | null>(null);
  const [mvQty, setMvQty] = useState(0);
  const [mvType, setMvType] = useState("in");
  const [error, setError] = useState<string | null>(null);

  const productName = (id: number) =>
    products.find((p) => p.id === id)?.name ?? `Produit #${id}`;

  const handleAddWarehouse = async () => {
    if (!whName.trim()) return;
    try {
      await createWarehouse.mutateAsync({ name: whName.trim() });
      setWhName("");
    } catch {
      alert("Erreur lors de la création de l'entrepôt");
    }
  };

  const handleAddMovement = async () => {
    setError(null);
    if (!mvProduct || !mvWarehouse || mvQty <= 0)
      return setError("Produit, entrepôt et quantité > 0 requis.");
    try {
      await createMovement.mutateAsync({
        movement_type: mvType === "in" ? "purchase_receipt" : "manual_out",
        warehouse_id: mvWarehouse,
        product_id: mvProduct,
        quantity: mvType === "in" ? mvQty : -mvQty,
      });
      setMvQty(0);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur mouvement de stock");
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stock</h1>
        <p className="text-sm text-gray-600">Entrepôts, niveaux et mouvements</p>
      </div>

      {/* Entrepôts */}
      <Card className="p-4">
        <h2 className="mb-3 font-semibold text-gray-800">Entrepôts</h2>
        <div className="flex flex-wrap items-center gap-2">
          {warehouses.map((w) => (
            <span key={w.id} className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700">
              {w.name}
            </span>
          ))}
          <Input value={whName} onChange={(e) => setWhName(e.target.value)} placeholder="Nouvel entrepôt…" className="w-48" />
          <Button size="sm" variant="outline" onClick={handleAddWarehouse} disabled={createWarehouse.isPending}>
            Ajouter
          </Button>
        </div>
      </Card>

      {/* Mouvement rapide */}
      <Card className="space-y-3 p-4">
        <h2 className="font-semibold text-gray-800">Mouvement rapide</h2>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
          <select className="rounded-md border border-gray-300 px-3 py-2 text-sm" value={mvType} onChange={(e) => setMvType(e.target.value)}>
            <option value="in">Entrée</option>
            <option value="out">Sortie</option>
          </select>
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm sm:col-span-2"
            value={mvProduct ?? ""}
            onChange={(e) => setMvProduct(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Produit —</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={mvWarehouse ?? ""}
            onChange={(e) => setMvWarehouse(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">— Entrepôt —</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          <Input type="number" min={0} value={mvQty || ""} onChange={(e) => setMvQty(Number(e.target.value))} placeholder="Qté" />
        </div>
        <Button onClick={handleAddMovement} disabled={createMovement.isPending}>
          {createMovement.isPending ? "Enregistrement…" : "Enregistrer le mouvement"}
        </Button>
      </Card>

      {/* Niveaux */}
      <Card className="overflow-hidden p-0">
        <h2 className="px-4 pt-4 font-semibold text-gray-800">Niveaux de stock</h2>
        {loadingLevels ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : levels.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucun niveau de stock.</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Produit</th>
                <th className="px-4 py-3">Entrepôt</th>
                <th className="px-4 py-3 text-right">Réel</th>
                <th className="px-4 py-3 text-right">Réservé</th>
                <th className="px-4 py-3 text-right">Disponible</th>
              </tr>
            </thead>
            <tbody>
              {levels.map((l) => {
                const wh = warehouses.find((w) => w.id === l.warehouse_id);
                return (
                  <tr
                    key={l.id}
                    onClick={() => router.push(`/dashboard/catalogue/${l.product_id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">{productName(l.product_id)}</td>
                    <td className="px-4 py-3 text-gray-600">{wh?.name ?? `#${l.warehouse_id}`}</td>
                    <td className="px-4 py-3 text-right">{l.quantity_on_hand}</td>
                    <td className="px-4 py-3 text-right text-orange-600">{l.quantity_reserved}</td>
                    <td className="px-4 py-3 text-right font-semibold text-green-700">{l.available}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* Derniers mouvements */}
      <Card className="overflow-hidden p-0">
        <h2 className="px-4 pt-4 font-semibold text-gray-800">Derniers mouvements</h2>
        {movements.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucun mouvement.</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Produit</th>
                <th className="px-4 py-3 text-right">Quantité</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((m) => (
                <tr
                  key={m.id}
                  onClick={() => router.push(`/dashboard/catalogue/${m.product_id}`)}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 text-gray-600">{new Date(m.created_at).toLocaleString("fr-FR")}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                      {m.movement_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">{productName(m.product_id)}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${m.quantity >= 0 ? "text-green-700" : "text-red-600"}`}>
                    {m.quantity > 0 ? "+" : ""}{m.quantity}
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
