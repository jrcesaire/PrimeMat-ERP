/**
 * Loader global de téléchargement.
 *
 * Store léger hors React (compteur + message) : les utilitaires de
 * téléchargement (`downloadFile`, `openPdf`…) incrémentent le compteur avant
 * la requête et le décrémentent après, quel que soit le résultat. L'overlay
 * `<DownloadLoader />` monté dans les providers s'abonne et s'affiche tant
 * qu'au moins un téléchargement est en vol.
 *
 * Le compteur rend le composant sûr pour des téléchargements concurrents :
 * l'overlay ne disparaît que lorsque le dernier est terminé.
 */

export interface LoaderState {
  /** Nombre de téléchargements actuellement en vol */
  count: number;
  /** Message affiché sous le spinner */
  message: string;
}

const DEFAULT_MESSAGE = "Préparation du document…";

let state: LoaderState = { count: 0, message: DEFAULT_MESSAGE };
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

/** S'abonne aux changements du loader (API `useSyncExternalStore`). */
export function subscribeLoader(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** État courant (référence stable entre deux changements). */
export function getLoaderState(): LoaderState {
  return state;
}

/** Ouvre (ou prolonge) un chargement avec un message personnalisé. */
export function showLoader(message: string = DEFAULT_MESSAGE): void {
  state = { count: state.count + 1, message };
  emit();
}

/** Ferme un chargement — l'overlay disparaît à count = 0. */
export function hideLoader(): void {
  if (state.count === 0) return;
  state = { count: state.count - 1, message: state.message };
  emit();
}

/**
 * Exécute une tâche de téléchargement sous le loader global :
 * le spinner s'affiche dès l'appel et disparaît à la résolution ou à
 * l'erreur (le `finally` garantit qu'aucun compteur ne reste bloqué).
 */
export async function withLoader<T>(
  task: Promise<T>,
  message: string = DEFAULT_MESSAGE,
): Promise<T> {
  showLoader(message);
  try {
    return await task;
  } finally {
    hideLoader();
  }
}