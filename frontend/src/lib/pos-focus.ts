/**
 * État « mode focus caisse » — masque la sidebar et le header du dashboard
 * pendant la vente au comptoir (écran dédié, comme les maquettes POS).
 *
 * Petit store abonné par le dashboard layout ; la page POS appelle
 * `setPosFocus(true)` en vue « nouvelle vente » et le remet à false
 * au retour vers l'historique (ou au démontage).
 */
type Listener = (focus: boolean) => void;

let focus = false;
const listeners = new Set<Listener>();

export function setPosFocus(next: boolean): void {
  if (next === focus) return;
  focus = next;
  listeners.forEach((listener) => listener(focus));
}

export function subscribePosFocus(listener: Listener): () => void {
  listeners.add(listener);
  listener(focus);
  return () => {
    listeners.delete(listener);
  };
}
