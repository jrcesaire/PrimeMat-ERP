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
        className="row-span-2 flex items-center justify-center rounded-control border border-primary bg-primary-soft px-2 text-[13px] font-semibold text-primary transition-colors hover:bg-primary/15 active:bg-primary/20"
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
        "h-11 rounded-control border text-[17px] font-semibold transition-colors active:scale-[0.97]",
        muted
          ? "border-line bg-subtle text-muted hover:bg-line"
          : "border-line bg-surface text-ink hover:bg-subtle",
      )}
    >
      {label}
    </button>
  );
}