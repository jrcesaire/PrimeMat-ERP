/**
 * ConfirmProvider — clone du pattern `material-ui-confirm` sur notre Dialog shadcn.
 *
 * À monter une fois sous le ThemeProvider (déjà fait dans `app/providers.tsx`) :
 * les écrans appellent ensuite `const confirm = useConfirm()` puis
 * `const { confirmed } = await confirm(confirmDeleteOptions("le devis DEV-1"))`.
 */
"use client";

import * as React from "react";

import { ConfirmContext } from "./ConfirmContext";
import { ConfirmDialogView } from "./ConfirmDialogView";
import { Dialog } from "@/components/ui/dialog";

import type {
  ConfirmFn,
  ConfirmOptions,
  ConfirmRequest,
  ConfirmResult,
  ConfirmTone,
} from "./types";

const BASE_DEFAULTS: {
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  tone: ConfirmTone;
  allowClose: boolean;
  hideCancelButton: boolean;
  autoFocusConfirm: boolean;
} = {
  title: "Confirmer l'action",
  description: "Voulez-vous vraiment continuer ?",
  confirmLabel: "Confirmer",
  cancelLabel: "Annuler",
  tone: "info",
  allowClose: true,
  hideCancelButton: false,
  autoFocusConfirm: true,
};

let nextRequestId = 1;

function withDefaults(
  options: ConfirmOptions,
  defaults: typeof BASE_DEFAULTS & ConfirmOptions,
  id: number,
  resolve: (result: ConfirmResult) => void,
): ConfirmRequest {
  return {
    id,
    resolve,
    title: options.title ?? defaults.title ?? BASE_DEFAULTS.title,
    description: options.description ?? defaults.description,
    content: options.content ?? defaults.content,
    confirmLabel:
      options.confirmLabel ?? defaults.confirmLabel ?? BASE_DEFAULTS.confirmLabel,
    cancelLabel:
      options.cancelLabel ?? defaults.cancelLabel ?? BASE_DEFAULTS.cancelLabel,
    tone: options.tone ?? defaults.tone ?? BASE_DEFAULTS.tone,
    allowClose: options.allowClose ?? defaults.allowClose ?? true,
    hideCancelButton:
      options.hideCancelButton ?? defaults.hideCancelButton ?? false,
    requireKeyword: options.requireKeyword ?? defaults.requireKeyword,
    keywordLabel: options.keywordLabel ?? defaults.keywordLabel,
    acknowledgement: options.acknowledgement ?? defaults.acknowledgement,
    autoFocusConfirm:
      options.autoFocusConfirm ??
      defaults.autoFocusConfirm ??
      BASE_DEFAULTS.autoFocusConfirm,
  };
}

export function ConfirmProvider({
  children,
  defaultOptions,
}: {
  children: React.ReactNode;
  defaultOptions?: ConfirmOptions;
}) {
  const [queue, setQueue] = React.useState<ConfirmRequest[]>([]);
  const queueRef = React.useRef<ConfirmRequest[]>([]);
  React.useEffect(() => {
    queueRef.current = queue;
  }, [queue]);

  const defaults = React.useMemo(
    () => ({ ...BASE_DEFAULTS, ...defaultOptions }),
    [defaultOptions],
  );

  const confirm = React.useCallback<ConfirmFn>(
    (options = {}) =>
      new Promise<ConfirmResult>((resolve) => {
        const id = nextRequestId++;
        setQueue((q) => [...q, withDefaults(options, defaults, id, resolve)]);
      }),
    [defaults],
  );

  // Les demandes en attente lors du démontage sont résolues en "natural".
  React.useEffect(
    () => () => {
      queueRef.current.forEach((r) =>
        r.resolve({ confirmed: false, reason: "natural" }),
      );
    },
    [],
  );

  const settle = React.useCallback((result: ConfirmResult) => {
    const head = queueRef.current[0];
    if (!head) return;
    head.resolve(result);
    setQueue((q) => q.slice(1));
  }, []);

  const current = queue[0] ?? null;

  const handleOpenChange = (open: boolean) => {
    if (!open && current && current.allowClose) {
      settle({ confirmed: false, reason: "natural" });
    }
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog open={current !== null} onOpenChange={handleOpenChange}>
        {current && (
          <ConfirmDialogView
            key={current.id}
            request={current}
            onConfirm={() => settle({ confirmed: true, reason: "confirm" })}
            onCancel={() => settle({ confirmed: false, reason: "cancel" })}
          />
        )}
      </Dialog>
    </ConfirmContext.Provider>
  );
}
