"use client";

import { useState } from "react";
import { useConfirm, confirmDeleteOptions } from "@/components/ui/confirm";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCurrentUser } from "@/hooks/useAuth";
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/hooks/useCatalogue";
import type { ProductCategory } from "@/lib/types";

export default function CategoriesTab() {
  const { data: currentUser } = useCurrentUser();
  const permissions = currentUser?.permissions ?? [];
  const canCreateCategory =
    currentUser?.is_superuser === true ||
    permissions.includes("category:create");
  const canEditCategory =
    currentUser?.is_superuser === true || permissions.includes("category:edit");
  const canDeleteCategory =
    currentUser?.is_superuser === true || permissions.includes("category:delete");

  const { data: categories = [], isLoading: loadingCategories } =
    useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();
  const confirm = useConfirm();

  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [parentId, setParentId] = useState<number | null>(null);
  const [saleMode, setSaleMode] = useState("unit");

  const resetForm = () => {
    setEditId(null);
    setName("");
    setCode("");
    setDescription("");
    setParentId(null);
    setSaleMode("unit");
  };

  const openEdit = (c: ProductCategory) => {
    setEditId(c.id);
    setName(c.name);
    setCode(c.code ?? "");
    setDescription(c.description ?? "");
    setParentId(c.parent_id ?? null);
    setSaleMode(c.sale_mode ?? "unit");
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Le nom est obligatoire.");
      return;
    }
    try {
      if (editId) {
        await updateCategory.mutateAsync({
          id: editId,
          data: {
            name: name.trim(),
            code: code.trim() || null,
            description: description.trim() || null,
            parent_id: parentId,
            sale_mode: saleMode,
          },
        });
      } else {
        await createCategory.mutateAsync({
          name: name.trim(),
          code: code.trim() || null,
          description: description.trim() || null,
          parent_id: parentId,
          sale_mode: saleMode,
        });
      }
      resetForm();
      setShowForm(false);
      setError(null);
    } catch (e: any) {
      setError(
        e?.response?.data?.detail || e?.message || "Erreur d'enregistrement.",
      );
    }
  };

  const handleDelete = async (categoryName: string, categoryId: number) => {
    const { confirmed } = await confirm(
      confirmDeleteOptions(`${categoryName} — Supprimer cette catégorie ?`),
    );
    if (!confirmed) return;
    try {
      await deleteCategory.mutateAsync(categoryId);
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Suppression impossible.");
    }
  };

  const parentOptions = categories.filter(
    (c) => c.is_active && c.id !== editId,
  );



  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">{categories.length} catégorie(s)</p>
        {canCreateCategory && (
          <Button
            variant="outline"
            onClick={() => {
              resetForm();
              setShowForm((v) => !v);
            }}
          >
            {showForm ? "Fermer" : "+ Nouvelle catégorie"}
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {showForm && (
        <Card className="space-y-3 p-4">
          <h2 className="font-semibold text-gray-800">
            {editId ? "Modifier la catégorie" : "Nouvelle catégorie"}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="col-span-1 sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">Nom *</label>
              <Input placeholder="Ex. Ciments, Ferraillage" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Code</label>
              <Input placeholder="Ex. CIM" value={code} onChange={(e) => setCode(e.target.value)} />
            </div>
            <div className="col-span-1 sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <Input placeholder="Optionnel" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Catégorie parente</label>
              <select value={parentId ?? ""} onChange={(e) => setParentId(e.target.value ? Number(e.target.value) : null)} className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm">
                <option value="">— Aucune (racine) —</option>
                {parentOptions.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Mode de vente</label>
              <select value={saleMode} onChange={(e) => setSaleMode(e.target.value)} className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm">
                <option value="unit">À l'unité</option>
                <option value="length">Au mètre linéaire</option>
                <option value="dual">Au ml ou à la pièce</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowForm(false)}>Annuler</Button>
            <Button onClick={handleSave} disabled={createCategory.isPending || updateCategory.isPending}>
              {editId ? "Mettre à jour" : "Créer la catégorie"}
            </Button>
          </div>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        {loadingCategories ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : categories.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-500">Aucune catégorie.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Nom</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Code</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Parente</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Mode de vente</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Actif</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {categories.map((c) => (
                <tr key={c.id} className="align-top hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-medium text-gray-900">{c.name}</td>
                  <td className="px-4 py-2.5">{c.code ?? "—"}</td>
                  <td className="px-4 py-2.5">{c.parent_id != null ? categories.find((p) => p.id === c.parent_id)?.name ?? "—" : "—"}</td>
                  <td className="px-4 py-2.5">{c.sale_mode === "length" ? "Au ml" : c.sale_mode === "dual" ? "Dual" : "Unité"}</td>
                  <td className="px-4 py-2.5">{c.is_active ? "Oui" : "Non"}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      {canEditCategory && (
                        <Button size="sm" variant="outline" onClick={() => openEdit(c)}>Modifier</Button>
                      )}
                      {canDeleteCategory && (
                        <Button size="sm" variant="outline" onClick={() => handleDelete(c.name, c.id)}>Supprimer</Button>
                      )}
                    </div>
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
