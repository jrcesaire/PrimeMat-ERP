/**
 * Hook `useConfirm` — pendant de `useConfirm()` de material-ui-confirm.
 *
 * ```tsx
 * const confirm = useConfirm();
 * const { confirmed } = await confirm({ title: "Supprimer ?" });
 * if (confirmed) await deleteItem(id);
 * ```
 */
"use client";

import { useContext } from "react";

import { ConfirmContext } from "./ConfirmContext";
import type { ConfirmFn } from "./types";

export function useConfirm(): ConfirmFn {
  const confirm = useContext(ConfirmContext);
  if (!confirm) {
    throw new Error("useConfirm doit être utilisé à l'intérieur de <ConfirmProvider>.");
  }
  return confirm;
}
