/**
 * Scanner de codes-barres / QR — caméra via html5-qrcode.
 *
 * - Bouton « Scanner » ouvre la caméra et lit QR + codes-barres (EAN, UPC, Code 128/39).
 * - Repli manuel si la caméra est indisponible (saisie du code au clavier).
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Keyboard, X } from "lucide-react";
import type { Html5Qrcode } from "html5-qrcode";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const ELEMENT_ID = "barcode-scanner-region";
const FORMATS = [
  "QR_CODE", "EAN_13", "EAN_8", "UPC_A", "UPC_E", "CODE_128", "CODE_39", "ITF",
];

interface BarcodeScannerProps {
  /** Appelé avec le code détecté (ou saisi manuellement). */
  onScan: (code: string) => void;
  label?: string;
  className?: string;
}

export function BarcodeScanner({ onScan, label = "Scanner", className }: BarcodeScannerProps) {
  const [open, setOpen] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const startingRef = useRef(false);

  useEffect(() => {
    if (!open || manualMode) return;
    let cancelled = false;

    (async () => {
      try {
        const { Html5Qrcode: Scanner, Html5QrcodeSupportedFormats } = await import(
          "html5-qrcode"
        );
        if (cancelled) return;
        const formats = FORMATS.map(
          (f) =>
            Html5QrcodeSupportedFormats[f as keyof typeof Html5QrcodeSupportedFormats]
        ).filter((f) => f !== undefined);
        const scanner = new Scanner(
          ELEMENT_ID,
          formats.length ? { verbose: false, formatsToSupport: formats } : undefined
        );
        scannerRef.current = scanner;
        startingRef.current = true;
        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 260, height: 180 } },
          (decoded) => {
            void stopScanner();
            setOpen(false);
            onScan(decoded.trim());
          },
          () => {
            /* frames sans lecture — silencieux */
          }
        );
      } catch (e) {
        if (!cancelled) {
          setError(
            "Caméra indisponible — utilisez la saisie manuelle ou autorisez l'accès à la caméra."
          );
          setManualMode(true);
        }
      } finally {
        startingRef.current = false;
      }
    })();

    return () => {
      cancelled = true;
      void stopScanner();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, manualMode]);

  const stopScanner = async () => {
    const scanner = scannerRef.current;
    scannerRef.current = null;
    if (scanner) {
      try {
        await scanner.stop();
      } catch {
        /* deja arrete */
      }
      try {
        scanner.clear();
      } catch {
        /* no-op */
      }
    }
  };

  const close = async () => {
    await stopScanner();
    setOpen(false);
    setManualMode(false);
    setManualCode("");
    setError(null);
  };

  return (
    <>
      <Button
        type="button"
        variant="outline"
        className={className}
        onClick={() => setOpen(true)}
      >
        <Camera className="h-4 w-4" /> {label}
      </Button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md space-y-3 rounded-xl bg-white p-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Scanner un code
              </h3>
              <button
                onClick={close}
                className="text-gray-400 hover:text-gray-700"
                aria-label="Fermer le scanner"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {!manualMode ? (
              <>
                <div
                  id={ELEMENT_ID}
                  className="overflow-hidden rounded-lg bg-gray-900"
                  style={{ minHeight: 240 }}
                />
                <button
                  type="button"
                  className="flex w-full items-center justify-center gap-2 text-xs text-gray-500 hover:text-primary"
                  onClick={async () => {
                    await stopScanner();
                    setManualMode(true);
                  }}
                >
                  <Keyboard className="h-4 w-4" /> Saisie manuelle du code
                </button>
              </>
            ) : (
              <div className="space-y-3">
                {error && (
                  <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-700">{error}</p>
                )}
                <Input
                  autoFocus
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && manualCode.trim()) {
                      void close();
                      onScan(manualCode.trim());
                    }
                  }}
                  placeholder="Code-barres ou QR (ex. 3401234567890)"
                />
                <Button
                  type="button"
                  className="w-full"
                  disabled={!manualCode.trim()}
                  onClick={() => {
                    void close();
                    onScan(manualCode.trim());
                  }}
                >
                  Valider le code
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
