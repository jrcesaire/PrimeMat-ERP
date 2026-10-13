/**
 * Rendu d'un dialogue de confirmation (tons danger / warning / info,
 * mot-clé à retaper, case d'acquittement).
 */
"use client";

import { AlertTriangle, Info } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

import type { ConfirmRequest } from "./types";

function toneIcon(tone: ConfirmRequest["tone"]): React.ReactNode {
  if (tone === "danger") {
    return (
      <AlertTriangle className="h-5 w-5 shrink-0 text-red-600 dark:text-red-400" />
    );
  }
  if (tone === "warning") {
    return (
      <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
    );
  }
  return <Info className="h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400" />;
}

export function ConfirmDialogView({
  request,
  onConfirm,
  onCancel,
}: {
  request: ConfirmRequest;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [keyword, setKeyword] = React.useState("");
  const [acknowledged, setAcknowledged] = React.useState(false);
  const confirmRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    if (request.autoFocusConfirm) confirmRef.current?.focus();
  }, [request.autoFocusConfirm]);

  const keywordOk =
    !request.requireKeyword || keyword.trim() === request.requireKeyword;
  const ackOk = !request.acknowledgement || acknowledged;
  const canConfirm = keywordOk && ackOk;

  return (
    <DialogContent
      hideCloseButton={!request.allowClose}
      onEscapeKeyDown={(e) => {
        if (!request.allowClose) e.preventDefault();
      }}
      onInteractOutside={(e) => {
        if (!request.allowClose) e.preventDefault();
      }}
    >
      <DialogHeader>
        <div className="flex items-start gap-3 pr-6">
          <span className="mt-0.5">{toneIcon(request.tone)}</span>
          <div className="flex flex-col gap-1.5">
            <DialogTitle>{request.title}</DialogTitle>
            {request.description && (
              <DialogDescription>{request.description}</DialogDescription>
            )}
          </div>
        </div>
      </DialogHeader>

      {request.content}

      {request.requireKeyword && (
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor={`confirm-keyword-${request.id}`}
            className="text-sm text-gray-600 dark:text-slate-300"
          >
            {request.keywordLabel ??
              `Tapez « ${request.requireKeyword} » pour confirmer`}
          </label>
          <input
            id={`confirm-keyword-${request.id}`}
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder={request.requireKeyword}
            autoComplete="off"
            className="h-10 rounded-md border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>
      )}

      {request.acknowledgement && (
        <label className="flex cursor-pointer items-start gap-2 text-sm text-gray-600 dark:text-slate-300">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 accent-primary"
          />
          <span>{request.acknowledgement}</span>
        </label>
      )}

      <DialogFooter>
        {!request.hideCancelButton && (
          <Button variant="outline" onClick={onCancel}>
            {request.cancelLabel}
          </Button>
        )}
        <Button
          ref={confirmRef}
          variant={request.tone === "danger" ? "destructive" : "default"}
          className={cn(
            request.tone === "warning" &&
              "bg-amber-600 text-white hover:bg-amber-700",
          )}
          disabled={!canConfirm}
          onClick={onConfirm}
        >
          {request.confirmLabel}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
