/**
 * Téléchargement de fichiers protégés par JWT (export Excel / CSV, PDF…).
 *
 * Un simple lien <a href> échouerait en 401 : le token doit passer par
 * axios, puis le blob est diffusé côté navigateur.
 */
import { apiClient } from "@/lib/api/client";
import { hideLoader, showLoader } from "@/lib/loader";

/** Enregistre un blob sous le nom fourni (déclenche le téléchargement). */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Libère l'URL après un délai suffisant pour que le téléchargement démarre
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/**
 * Nom de fichier porté par l'en-tête Content-Disposition.
 *
 * Gère la forme RFC 5987 (`filename*=UTF-8''Re%C3%A7u%20…`, accents) puis le
 * repli ASCII (`filename="…"`). Retourne null si l'en-tête est absent
 * (repli d'URL, réponse sans nom…).
 */
export function filenameFromDisposition(header: unknown): string | null {
  if (typeof header !== "string" || !header) return null;
  const extended = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (extended?.[1]) {
    try {
      return decodeURIComponent(extended[1].trim());
    } catch {
      // En-tête illisible : on retombe sur la forme ASCII ci-dessous
    }
  }
  const simple = /filename="?([^";]+)"?/.exec(header);
  return simple?.[1]?.trim() ?? null;
}

/**
 * Télécharge une URL d'export et l'enregistre sous son nom serveur
 * (« Contacts_2026-10-02.xlsx »), avec repli sur ``fallbackName``.
 */
export async function downloadFile(
  path: string,
  fallbackName: string,
  timeout = 120_000,
): Promise<void> {
  showLoader("Téléchargement du fichier…");
  try {
    const res = await apiClient.get(path, { responseType: "blob", timeout });
    const filename =
      filenameFromDisposition(res.headers["content-disposition"]) ?? fallbackName;
    saveBlob(res.data as Blob, filename);
  } finally {
    hideLoader();
  }
}
