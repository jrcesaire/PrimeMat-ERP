/**
 * Tests du store « mode immersif » du PoS (`src/lib/pos-focus.ts`).
 *
 * Couvre le PRD « Improvements module PoS » §4.2.1 (US1) : l'entrée dans le
 * module PoS masque la sidebar et le header de l'ERP, la sortie les restaure.
 */
import { setPosFocus, subscribePosFocus } from "./pos-focus";

describe("store du mode immersif PoS", () => {
  beforeEach(() => {
    // Le store est un singleton de module : on repart d'un état connu.
    setPosFocus(false);
  });

  it("notifie immédiatement l'abonné avec l'état courant", () => {
    const listener = jest.fn();
    const unsubscribe = subscribePosFocus(listener);

    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenLastCalledWith(false);

    unsubscribe();
  });

  it("propage l'activation puis la désactivation du mode immersif", () => {
    const listener = jest.fn();
    const unsubscribe = subscribePosFocus(listener);
    listener.mockClear();

    setPosFocus(true);
    expect(listener).toHaveBeenLastCalledWith(true);

    setPosFocus(false);
    expect(listener).toHaveBeenLastCalledWith(false);
    expect(listener).toHaveBeenCalledTimes(2);

    unsubscribe();
  });

  it("n'émet rien si l'état demandé est déjà en place", () => {
    const listener = jest.fn();
    const unsubscribe = subscribePosFocus(listener);
    listener.mockClear();

    setPosFocus(true);
    setPosFocus(true);
    setPosFocus(true);

    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
  });

  it("notifie tous les abonnés", () => {
    const first = jest.fn();
    const second = jest.fn();
    const unsubscribeFirst = subscribePosFocus(first);
    const unsubscribeSecond = subscribePosFocus(second);
    first.mockClear();
    second.mockClear();

    setPosFocus(true);

    expect(first).toHaveBeenCalledWith(true);
    expect(second).toHaveBeenCalledWith(true);

    unsubscribeFirst();
    unsubscribeSecond();
  });

  it("cesse de notifier après désabonnement", () => {
    const listener = jest.fn();
    const unsubscribe = subscribePosFocus(listener);
    listener.mockClear();

    unsubscribe();
    setPosFocus(true);

    expect(listener).not.toHaveBeenCalled();
  });

  it("applique le nouvel état au moment de l'abonnement", () => {
    setPosFocus(true);

    const listener = jest.fn();
    const unsubscribe = subscribePosFocus(listener);

    expect(listener).toHaveBeenLastCalledWith(true);

    unsubscribe();
  });
});
