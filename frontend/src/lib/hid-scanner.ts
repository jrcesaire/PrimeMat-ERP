/**
 * Support AIDC — douchettes / terminaux USB en mode « clavier » (HID).
 *
 * Une douchette émule un clavier : les caractères du code arrivent en
 * rafale (< 30 ms entre touches) et se terminent par « Entrée ». Un
 * écouteur global capture cette signature — le champ actif n'a pas
 * besoin d'avoir le focus — et appelle ``onScan`` avec le code lu.
 *
 * La saisie clavier humaine est naturellement ignorée : les frappes
 * manuelles ne maintiennent jamais un écart < 30 ms sur 6 caractères.
 *
 * Usage :
 *   useEffect(() => attachHidScanner(handleScan), []);
 */
export interface HidScannerOptions {
  /** Longueur minimale du code (défaut 6). */
  minLength?: number;
  /** Écart maximal entre deux touches (ms, défaut 30). */
  gapMs?: number;
  /** Durée maximale totale de la saisie (ms, défaut 500). */
  maxDurationMs?: number;
  /** Bip de confirmation (défaut true). */
  beep?: boolean;
}

export function attachHidScanner(
  onScan: (code: string) => void,
  options: HidScannerOptions = {},
): () => void {
  const {
    minLength = 6,
    gapMs = 30,
    maxDurationMs = 500,
    beep = true,
  } = options;

  let buffer = "";
  let firstKeyAt = 0;
  let lastKeyAt = 0;

  const handler = (e: KeyboardEvent) => {
    if (e.isComposing || e.ctrlKey || e.altKey || e.metaKey) return;

    const now = performance.now();

    if (e.key === "Enter") {
      const code = buffer;
      const elapsed = now - firstKeyAt;
      buffer = "";
      lastKeyAt = 0;
      firstKeyAt = 0;
      if (code.length >= minLength && elapsed <= maxDurationMs) {
        e.preventDefault(); // le code est consommé, pas soumis au formulaire
        if (beep) playBeep();
        onScan(code);
      }
      return;
    }

    if (e.key.length !== 1) {
      // Touches spéciales (Tab, flèches...) : cassent le buffer.
      buffer = "";
      lastKeyAt = 0;
      firstKeyAt = 0;
      return;
    }

    if (lastKeyAt === 0 || now - lastKeyAt <= gapMs) {
      if (lastKeyAt === 0) firstKeyAt = now;
      buffer += e.key;
      lastKeyAt = now;
      if (buffer.length > 48) {
        buffer = "";
        lastKeyAt = 0;
        firstKeyAt = 0;
      }
    } else {
      // Frappe trop lente : saisie humaine — on repart à zéro.
      buffer = e.key;
      firstKeyAt = now;
      lastKeyAt = now;
    }
  };

  window.addEventListener("keydown", handler, true);
  return () => window.removeEventListener("keydown", handler, true);
}

/** Bip court de confirmation du scan (WebAudio). */
function playBeep(): void {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 1200;
    gain.gain.value = 0.08;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.08);
    osc.onended = () => void ctx.close();
  } catch {
    /* audio indisponible — silencieux */
  }
}
