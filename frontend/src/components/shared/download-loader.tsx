/**
 * Overlay global de téléchargement (spinner plein écran).
 *
 * Rendu uniquement quand au moins un téléchargement est en vol — voir
 * `@/lib/loader`. Monté une fois dans `app/providers.tsx`, il couvre donc
 * tous les appels (exports Excel/CSV, PDF de documents, tickets POS…)
 * sans rien changer dans les pages.
 */
"use client";

import { useSyncExternalStore, type CSSProperties } from "react";

import { FadeArc } from "@/components/loading-ui/fade-arc";
import { getLoaderState, subscribeLoader } from "@/lib/loader";

export function DownloadLoader() {
  const { count, message } = useSyncExternalStore(
    subscribeLoader,
    getLoaderState,
    getLoaderState,
  );

  if (count === 0) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/50"
    >
      <div className="flex flex-col items-center gap-3 rounded-xl bg-white px-8 py-7 shadow-2xl dark:bg-slate-800">
        <FadeArc
          className="h-9 w-9 text-blue-600"
          style={{ "--duration": "1.2s" } as CSSProperties}
        />
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {message}
        </p>
      </div>
    </div>
  );
}