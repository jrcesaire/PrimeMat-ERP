/**
 * Boîte de dialogue d'import Excel / CSV (réutilisable).
 *
 * Choisir un fichier .xlsx / .csv → POST multipart vers l'endpoint
 * d'import → affiche le bilan (créés / mis à jour / erreurs).
 * Les requêtes de liste passées dans ``invalidateKeys`` sont invalidées.
 */
"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Download, FileSpreadsheet, Loader2, Upload, X } from "lucide-react";

import { apiClient } from "@/lib/api/client";
import { downloadFile } from "@/lib/api/download";

export interface ImportResult {
  created?: number;
  updated?: number;
  orders_created?: number;
  lines_created?: number;
  errors?: { line: string | number; error: string }[];
  total?: number;
}

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  /** Endpoint backend, ex. "/catalogue/products/import" */
  endpoint: string;
  title: string;
  /** Description des colonnes attendues (première ligne du fichier) */
  columnsHint: string;
  /** Clés de requête react-query à invalider après succès */
  invalidateKeys?: string[];
  /**
   * Endpoint d'export servant de modèle vierge (en-têtes seuls).
   * Dérivé de ``endpoint`` par défaut : « .../import » → « .../export ».
   */
  templateEndpoint?: string;
}

export function ImportDialog({
  open,
  onClose,
  endpoint,
  title,
  columnsHint,
  invalidateKeys = [],
  templateEndpoint,
}: ImportDialogProps) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  /** Modèle vierge : mêmes en-têtes que l'import (endpoint « .../export »). */
  const exportEndpoint =
    templateEndpoint ?? endpoint.replace(/\/import\/?$/, "/export");

  if (!open) return null;

  const reset = () => {
    setResult(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Sélectionnez un fichier (.xlsx ou .csv).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post(endpoint, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000, // imports potentiellement volumineux
      });
      setResult(res.data as ImportResult);
      invalidateKeys.forEach((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      );
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(
        typeof detail === "string" ? detail : "Échec de l'import du fichier.",
      );
    } finally {
      setBusy(false);
    }
  };

  /** Télécharge le modèle vierge : en-têtes seuls, prêts à remplir. */
  const onDownloadTemplate = async () => {
    setDownloading(true);
    try {
      await downloadFile(`${exportEndpoint}?template=1`, "modele_import.xlsx");
    } catch {
      alert("Téléchargement du modèle impossible.");
    } finally {
      setDownloading(false);
    }
  };

  const imported = result
    ? (result.created ?? 0) + (result.updated ?? 0) + (result.orders_created ?? 0)
    : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
              <FileSpreadsheet className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              <p className="text-xs text-gray-500">
                Fichier Excel (.xlsx) ou CSV — première ligne = en-têtes
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fermer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {result ? (
          <div className="mt-5 space-y-3">
            <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-800">
              <p className="font-semibold">Import terminé</p>
              <p className="mt-1">
                {imported} élément(s) traité(s)
                {result.updated ? ` (${result.updated} mis à jour)` : ""}
                {result.orders_created
                  ? ` — ${result.orders_created} commande(s), ${result.lines_created ?? 0} ligne(s)`
                  : ""}
              </p>
            </div>
            {result.errors && result.errors.length > 0 && (
              <div className="max-h-40 overflow-y-auto rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                <p className="font-semibold">
                  {result.errors.length} ligne(s) en erreur :
                </p>
                <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs">
                  {result.errors.slice(0, 20).map((e, i) => (
                    <li key={i}>
                      Ligne {e.line} : {e.error}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={reset}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Importer un autre fichier
              </button>
              <button
                onClick={handleClose}
                className="rounded-md bg-primary px-4 py-2 text-sm text-white hover:bg-primary-hover"
              >
                Fermer
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="mt-5 rounded-md bg-gray-50 px-4 py-3 text-xs text-gray-600">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-gray-700">Colonnes attendues :</p>
                  <p className="mt-1 leading-relaxed">{columnsHint}</p>
                </div>
                {exportEndpoint !== endpoint && (
                  <button
                    type="button"
                    onClick={onDownloadTemplate}
                    disabled={downloading}
                    className="flex shrink-0 items-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
                  >
                    {downloading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5" />
                    )}
                    Modèle vierge
                  </button>
                )}
              </div>
            </div>

            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 px-4 py-8 text-sm text-gray-500 hover:border-primary hover:bg-gray-50">
              <Upload className="h-6 w-6" />
              <span>Cliquez pour choisir un fichier</span>
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.xlsm,.csv"
                className="hidden"
              />
            </label>

            {error && (
              <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={handleClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={onSubmit}
                disabled={busy}
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-white hover:bg-primary-hover disabled:opacity-60"
              >
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                Importer
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
