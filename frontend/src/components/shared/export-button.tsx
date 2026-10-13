"use client";

import { useState } from "react";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { downloadFile } from "@/lib/api/download";

type ExportFormat = "xlsx" | "csv";

interface ExportButtonProps {
  /** Endpoint backend, ex. "/crm/partners/export" */
  endpoint: string;
  /** Nom de repli si l'en-tête Content-Disposition est absent */
  fallbackName?: string;
  /** Libellé du bouton */
  label?: string;
  /** Paramètres de requête supplémentaires (filtres de la page) */
  params?: Record<string, string>;
  className?: string;
  disabled?: boolean;
}

/**
 * Bouton « Exporter » avec choix du format (Excel / CSV).
 *
 * Symétrique du bouton « Importer » : le fichier produit par l'endpoint
 * ``…/export`` reprend les mêmes colonnes que l'import, il se réimporte
 * donc tel quel.
 */
export function ExportButton({
  endpoint,
  fallbackName = "export.xlsx",
  label = "Exporter",
  params,
  className,
  disabled = false,
}: ExportButtonProps) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);

  const run = async (format: ExportFormat) => {
    if (busy) return;
    setBusy(format);
    try {
      const query = new URLSearchParams({ format, ...(params ?? {}) });
      await downloadFile(`${endpoint}?${query.toString()}`, `${fallbackName}.${format}`);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail;
      alert(typeof detail === "string" ? detail : "Échec de l'export.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={className ?? "flex items-center gap-2"}
          disabled={disabled || busy !== null}
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {busy ? "Export…" : label}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => run("xlsx")}>
          <FileSpreadsheet className="mr-2 h-4 w-4" />
          Excel (.xlsx)
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => run("csv")}>
          <FileText className="mr-2 h-4 w-4" />
          CSV (.csv)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
