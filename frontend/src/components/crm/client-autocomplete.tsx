/**
 * Autocomplete client — saisie libre, suggestions, création à la volée.
 *
 * - Tape ≥ 2 caractères → recherche API (`/crm/partners?search=…`)
 * - Si des clients correspondent → sélection dans la liste
 * - Sinon deux actions :
 *   1. « Créer et continuer » — crée le client (nom seul) et le sélectionne
 *   2. « Créer et compléter » — crée puis ouvre le formulaire détaillé
 *      (téléphone, e-mail, adresse…) avant de reprendre le devis
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { UserPlus, PencilLine } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { Partner } from "@/lib/types";

interface Props {
  value: number | null;
  onChange: (partnerId: number | null) => void;
}

interface QuickForm {
  name: string;
  phone: string;
  email: string;
  city: string;
  line_1: string;
}

export function ClientAutocomplete({ value, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Partner[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Partner | null>(null);
  const [form, setForm] = useState<QuickForm>({
    name: "", phone: "", email: "", city: "", line_1: "",
  });
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value && selectedName && query === selectedName) return;
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const res = await apiClient.get(
          `/crm/partners?role=client&search=${encodeURIComponent(q)}`
        );
        setResults(res.data ?? []);
        setOpen(true);
      } catch {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query, value, selectedName]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);
  const select = (p: Partner) => {
    onChange(p.id);
    setSelectedName(p.name);
    setQuery(p.name);
    setOpen(false);
  };


  const createPartner = async (detailed: boolean) => {
    if (!query.trim() || busy) return;
    setBusy(true);
    try {
      const res = await apiClient.post("/crm/partners", {
        name: query.trim(),
        role: "client",
        entity_type: "individual",
      });
      const p: Partner = res.data;
      onChange(p.id);
      setSelectedName(p.name);
      setQuery(p.name);
      setResults([]);
      setOpen(false);
      if (detailed) {
        setEditing(p);
        setForm({
          name: p.name, phone: p.phone ?? "", email: p.email ?? "",
          city: "", line_1: "",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const saveDetails = async () => {
    if (!editing || busy) return;
    setBusy(true);
    try {
      await apiClient.put(`/crm/partners/${editing.id}`, {
        name: form.name || editing.name,
        phone: form.phone || undefined,
        email: form.email || undefined,
      });
      if (form.line_1 || form.city) {
        await apiClient.post(`/crm/partners/${editing.id}/addresses`, {
          address_type: "delivery",
          line_1: form.line_1 || undefined,
          city: form.city || undefined,
          is_primary: true,
        });
      }
      setEditing(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={boxRef} className="relative">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { if (query.trim().length >= 2) setOpen(true); }}
        placeholder="Tapez le nom du client…"
      />
      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
          {results.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => select(p)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span className="font-medium text-gray-800">{p.name}</span>
              <span className="text-xs text-gray-500">{p.phone ?? ""}</span>
            </button>
          ))}
          {query.trim().length >= 2 && (
            <div className="border-t border-gray-100 p-2">
              <Button
                size="sm"
                className="flex w-full items-center gap-2"
                disabled={busy}
                onClick={() => createPartner(false)}
              >
                <UserPlus className="h-4 w-4" />
                Créer « {query.trim()} » et continuer le devis
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 flex w-full items-center gap-2"
                disabled={busy}
                onClick={() => createPartner(true)}
              >
                <PencilLine className="h-4 w-4" />
                Créer et compléter le contact
              </Button>
            </div>
          )}
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">
              Compléter le contact
            </h3>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Nom</label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500">Téléphone</label>
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500">E-mail</label>
                  <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Adresse</label>
                <Input value={form.line_1} onChange={(e) => setForm({ ...form, line_1: e.target.value })} placeholder="Rue, quartier…" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Ville</label>
                <Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditing(null)}>Annuler</Button>
              <Button onClick={saveDetails} disabled={busy}>Enregistrer</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
