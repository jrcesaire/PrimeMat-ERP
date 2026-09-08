/**
 * Création / édition d'un contact (client ou fournisseur).
 * - Sans `?id=`  → création
 * - Avec `?id=`  → édition (pré-remplie)
 */
"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useCreatePartner,
  usePartner,
  useUpdatePartner,
} from "@/hooks/useCRM";

export default function NewContactPage() {
  return (
    <Suspense fallback={null}>
      <NewContactPageInner />
    </Suspense>
  );
}

function NewContactPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = Number(searchParams.get("id")) || null;
  const createPartner = useCreatePartner();
  const updatePartner = useUpdatePartner();
  const { data: existing } = usePartner(editId ?? 0);

  const isEdit = !!editId;

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [isSupplier, setIsSupplier] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Pré-remplissage en mode édition (une seule fois)
  useEffect(() => {
    if (!existing || loaded) return;
    setLoaded(true);
    setName(existing.name);
    setPhone(existing.phone ?? "");
    setEmail(existing.email ?? "");
    setCity(existing.addresses?.[0]?.city ?? "");
    setIsSupplier(existing.role === "supplier" || existing.role === "both");
  }, [existing, loaded]);

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) return setError("Nom requis.");
    const data = {
      name: name.trim(),
      phone: phone || undefined,
      email: email || undefined,
      role: isSupplier ? "supplier" : "client",
      addresses: city ? [{ address_type: "main", city }] : undefined,
    };
    try {
      if (isEdit) {
        await updatePartner.mutateAsync({ id: editId, data });
      } else {
        await createPartner.mutateAsync(data);
      }
      router.push("/dashboard/contacts");
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
          {isEdit ? "Modifier le contact" : "Nouveau contact"}
        </h1>
        <p className="text-sm text-gray-600">Client ou fournisseur</p>
      </div>

      <Card className="space-y-4 p-4">
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Nom *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex : Boutique Chez Fatou" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Téléphone</label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+225 …" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">E-mail</label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Ville</label>
            <Input value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <div className="flex items-center pt-6">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={isSupplier}
                onChange={(e) => setIsSupplier(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300"
              />
              Fournisseur
            </label>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleSubmit} disabled={createPartner.isPending || updatePartner.isPending}>
            {createPartner.isPending || updatePartner.isPending
              ? "Enregistrement…"
              : isEdit
                ? "Enregistrer les modifications"
                : "Créer le contact"}
          </Button>
          <Button variant="outline" onClick={() => router.push("/dashboard/contacts")}>
            Annuler
          </Button>
        </div>
      </Card>
    </div>
  );
}
