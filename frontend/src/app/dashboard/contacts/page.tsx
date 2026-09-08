/**
 * Page Contacts — clients et fournisseurs.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Phone, Mail } from "lucide-react";
import { Card } from "@/components/ui/card";
import { usePartners } from "@/hooks/useCRM";

export default function ContactsPage() {
  const router = useRouter();
  const [role, setRole] = useState<"all" | "customer" | "supplier">("all");
  const { data: partners = [], isLoading } = usePartners(
    role === "all" ? undefined : role,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
        <p className="text-sm text-gray-600">Clients et fournisseurs</p>
      </div>

      {/* Filtres */}
      <div className="flex gap-4 border-b border-gray-200">
        {[
          { key: "all", label: "Tous" },
          { key: "client", label: "Clients" },
          { key: "supplier", label: "Fournisseurs" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setRole(t.key as typeof role)}
            className={`border-b-2 px-4 pb-2 text-sm font-medium ${
              role === t.key
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500">Chargement…</p>
        ) : partners.length === 0 ? (
          <div className="p-10 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="text-sm text-gray-500">Aucun contact.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Téléphone</th>
                <th className="px-4 py-3">E-mail</th>
                <th className="px-4 py-3">Ville</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => router.push(`/dashboard/contacts/new?id=${p.id}`)}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 hover:text-primary hover:underline">{p.name}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                      {p.role === "supplier"
                        ? "Fournisseur"
                        : p.role === "both"
                          ? "Client + Fourn."
                          : "Client"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.phone ? (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {p.phone}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.email ? (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {p.email}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.addresses?.[0]?.city ?? "—"}
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
