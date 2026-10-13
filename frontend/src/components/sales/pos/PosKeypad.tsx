/**
 * Pavé numérique tactile (maquette caisse B) — saisie du montant reçu.
 *
 * Composant totalement contrôlé : la valeur est une chaîne gérée par le
 * parent (« », « 1500 », « 1500.50 »), ce qui évite tout désynchronisation
 * avec l'affichage.
 */
"use client";

import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (value: string) => void;
  /** Remplace la saisie par le montant exact du panier (bouton « Exact »). */
  onExact?: () => void;
}

export function PosKeypad({ value, onChange, onExact }: Props) {
  const press = (k: string) => {
    if (k === "." && value.includes(".")) return;
    if (k === "00" && (value === "" || value === "0")) return;
    if (value.length >= 12) return;
    // Supprime le zéro non significatif avant un chiffre (« 0 » + « 5 » → « 5 »).
    const next = value === "0" && k !== "." ? k : value + k;
    onChange(next);
  };

  return (
    <div className="grid grid-cols-4 gap-2">
      {["7", "8", "9"].map((d) => (
        <Key key={d} label={d} onPress={() => press(d)} />
      ))}
      <Key label="⌫" muted onPress={() => onChange(value.slice(0, -1))} />

      {["4", "5", "6"].map((d) => (
        <Key key={d} label={d} onPress={() => press(d)} />
      ))}
      <Key label="C" muted onPress={() => onChange("")} />

      {["1", "2", "3"].map((d) => (
        <Key key={d} label={d} onPress={() => press(d)} />
      ))}
      {/* Exact occupe les deux dernières rangées de la colonne droite. */}
      <button
        type="button"
        onClick={onExact}
        disabled={!onExact}
        className="row-span-2 flex items-center justify-center rounded-md border border-green-600 bg-green-50 px-2 text-sm font-bold text-green-700 transition hover:bg-green-100 active:bg-green-200"
      >
        Exact
      </button>

      <Key label="." onPress={() => press(".")} />
      <Key label="0" onPress={() => press("0")} />
      <Key label="00" onPress={() => press("00")} />
    </div>
  );
}

function Key({
  label,
  onPress,
  muted,
}: {
  label: string;
  onPress: () => void;
  muted?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onPress}
      className={cn(
        "h-12 rounded-md border text-lg font-semibold shadow-sm transition active:scale-[0.97]",
        muted
          ? "border-gray-300 bg-gray-100 text-gray-600 hover:bg-gray-200"
          : "border-gray-200 bg-white text-gray-900 hover:bg-gray-50",
      )}
    >
      {label}
    </button>
  );
}