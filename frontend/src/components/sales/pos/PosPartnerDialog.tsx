/**
 * Popup « Nouveau client » depuis la caisse — permet d'ajouter un client
 * absent de la liste sans quitter la vente (le partenaire walk-in
 * « Client de passage » reste le défaut).
 */
"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { UserRound } from "lucide-react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCreatePartner } from "@/hooks/useCRM";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Appelé avec l'id du partenaire créé (présélection en caisse). */
  onCreated: (partnerId: number) => void;
}

const EMPTY = { name: "", phone: "", email: "" };

export function PosPartnerDialog({ open, onOpenChange, onCreated }: Props) {
  const createPartner = useCreatePartner();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const close = (o: boolean) => {
    if (!o) {
      setForm(EMPTY);
      setError(null);
    }
    onOpenChange(o);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const name = form.name.trim();
    if (!name) {
      setError("Le nom du client est obligatoire.");
      return;
    }
    setError(null);
    try {
      const partner = await createPartner.mutateAsync({
        name,
        role: "client",
        ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
        ...(form.email.trim() ? { email: form.email.trim() } : {}),
      });
      onCreated(partner.id);
      setForm(EMPTY);
    } catch (err: unknown) {
      // Détail backend (ex. permission « partner.create » refusée au caissier).
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      setError(
        typeof detail === "string" && detail
          ? detail
          : "Création du client impossible. Vérifiez les champs saisis.",
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserRound className="h-5 w-5" /> Nouveau client
          </DialogTitle>
          <DialogDescription>
            Ajoutez un client en quelques secondes — la vente en cours est
            conservée.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="pos-partner-name"
              className="text-sm font-medium text-gray-700"
            >
              Nom du client <span className="text-red-600">*</span>
            </label>
            <Input
              id="pos-partner-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ex. : Entreprise BAT SARL"
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label
                htmlFor="pos-partner-phone"
                className="text-sm font-medium text-gray-700"
              >
                Téléphone
              </label>
              <Input
                id="pos-partner-phone"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="Ex. : 0700000000"
              />
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="pos-partner-email"
                className="text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <Input
                id="pos-partner-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Ex. : client@exemple.com"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Annuler
              </Button>
            </DialogClose>
            <Button
              type="submit"
              disabled={createPartner.isPending}
              className="bg-green-600 text-white hover:bg-green-700"
            >
              {createPartner.isPending ? "Création…" : "Créer et sélectionner"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
