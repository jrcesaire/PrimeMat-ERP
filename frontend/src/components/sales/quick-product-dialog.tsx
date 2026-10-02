/**
 * Dialog « Ajout rapide de produit ».
 *
 * Utilisé lorsque l'utilisateur cherche un produit introuvable (POS ou
 * lignes de devis/commande) : création minimale (nom + prix de vente),
 * la référence étant générée automatiquement par le backend.
 */
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCreateProduct } from "@/hooks/useCatalogue";
import type { Product } from "@/lib/types";

interface Props {
  initialName: string;
  onClose: () => void;
  onCreated: (p: Product) => void;
}

export function QuickProductDialog({ initialName, onClose, onCreated }: Props) {
  const createProduct = useCreateProduct();
  const [name, setName] = useState(initialName);
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!name.trim()) return setError("Le nom est obligatoire.");
    if (!(Number(price) > 0)) return setError("Saisissez un prix de vente valide.");
    setBusy(true);
    setError(null);
    try {
      const product = await createProduct.mutateAsync({
        name: name.trim(),
        selling_price: Number(price),
        status: "active",
      } as Partial<Product>);
      onCreated(product);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Erreur lors de la création du produit.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl">
        <h3 className="mb-1 text-lg font-semibold text-gray-900">Ajout rapide de produit</h3>
        <p className="mb-4 text-xs text-gray-500">
          La référence est générée automatiquement. Complétez la fiche plus tard dans le Catalogue.
        </p>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Nom *</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Prix de vente *</label>
            <Input
              type="number"
              min={0}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Annuler
          </Button>
          <Button onClick={save} disabled={busy}>
            {busy ? "Création…" : "Créer et ajouter"}
          </Button>
        </div>
      </div>
    </div>
  );
}
