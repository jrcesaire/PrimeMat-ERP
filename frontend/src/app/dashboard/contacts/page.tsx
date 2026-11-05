/**
 * Page Contacts — clients et fournisseurs.
 */
"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Users, Phone, Mail, Upload } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ImportDialog } from "@/components/shared/import-dialog";
import { ExportButton } from "@/components/shared/export-button";
import { EmptyState } from "@/components/ui/empty-state";
import { CRM_KEYS, usePartners } from "@/hooks/useCRM";
import { cn, lastRouteSegment } from "@/lib/utils";

/** Filtre de rôle du module Contacts (sous-routes « Clients » / « Fournisseurs »). */
export type ContactsRole = "all" | "client" | "supplier";

/** Sous-route → filtre : /dashboard/contacts/clients ouvre les clients. */
function roleFromPath(pathname: string | null): ContactsRole {
  const segment = lastRouteSegment(pathname);
  if (segment === "clients") return "client";
  if (segment === "fournisseurs") return "supplier";
  return "all";
}

export default function ContactsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [role, setRole] = useState<ContactsRole>(roleFromPath(pathname));
  const [importOpen, setImportOpen] = useState(false);
  const { data: partners = [], isLoading } = usePartners(
    role === "all" ? undefined : role,
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-semibold leading-tight text-ink">Contacts</h1>
          <p className="text-sm text-muted">Clients et fournisseurs</p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton
            endpoint="/crm/partners/export"
            fallbackName="contacts"
            params={role === "all" ? undefined : { role }}
          />
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={() => setImportOpen(true)}
          >
            <Upload className="h-4 w-4" />
            Importer
          </Button>
        </div>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        endpoint="/crm/partners/import"
        title="Importer des contacts"
        columnsHint="nom, code, role (client/fournisseur), telephone, email, ville, adresse, type_entite (particulier/entreprise), ncc, limite_credit, delai_paiement"
        invalidateKeys={[CRM_KEYS.partners]}
      />

      {/* Filtres */}
      <div className="flex gap-4 border-b border-line">
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
                : "border-transparent text-muted hover:text-muted"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

            {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-[176px] animate-pulse rounded-card bg-subtle" />
          ))}
        </div>
      ) : partners.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Aucun contact"
          description="Ajoutez un client ou un fournisseur pour le voir apparaitre ici."
          className="rounded-card border border-line bg-surface"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {partners.map((p) => {
            const role =
              p.role === "supplier"
                ? { label: "Fournisseur", tone: "bg-warning-soft text-warning" }
                : p.role === "both"
                  ? { label: "Client + Fourn.", tone: "bg-primary-soft text-primary" }
                  : { label: "Client", tone: "bg-success-soft text-success" };
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => router.push(`/dashboard/contacts/new?id=${p.id}`)}
                className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4 text-left transition-colors hover:border-primary/40"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-soft text-[13px] font-semibold uppercase text-primary">
                    {p.name.slice(0, 2)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[14px] font-semibold text-ink">
                      {p.name}
                    </p>
                    <span
                      className={cn(
                        "mt-0.5 inline-flex rounded-chip px-2 py-0.5 text-[10px] font-medium",
                        role.tone,
                      )}
                    >
                      {role.label}
                    </span>
                  </div>
                </div>

                <div className="space-y-1 border-t border-line pt-3 text-[12px] text-muted">
                  <p className="flex items-center gap-2 truncate">
                    <Phone className="h-3.5 w-3.5 shrink-0 text-faint" />
                    {p.phone || "-"}
                  </p>
                  <p className="flex items-center gap-2 truncate">
                    <Mail className="h-3.5 w-3.5 shrink-0 text-faint" />
                    {p.email || "-"}
                  </p>
                  <p className="flex items-center gap-2 truncate">
                    <Users className="h-3.5 w-3.5 shrink-0 text-faint" />
                    {p.addresses?.[0]?.city ?? "-"}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
