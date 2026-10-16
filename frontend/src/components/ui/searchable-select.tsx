"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, UserPlus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export interface SearchableSelectOption {
  id: string | number;
  label: string;
  subLabel?: string;
}

interface SearchableSelectProps<TValue extends string | number> {
  value: TValue | null;
  displayLabel?: string | null;
  onChange: (id: TValue) => void;
  options?: SearchableSelectOption[];
  fetchOptions?: (q: string) => Promise<SearchableSelectOption[]>;
  limit?: number;
  placeholder?: string;
  createLabel?: string;
  onCreate?: (name: string) => Promise<SearchableSelectOption | null>;
  creatable?: boolean;
  className?: string;
  disabled?: boolean;
}

export function SearchableSelect<TValue extends string | number>({
  value,
  displayLabel,
  onChange,
  options,
  fetchOptions,
  limit = 5,
  placeholder = "Rechercher…",
  createLabel,
  onCreate,
  creatable = false,
  className,
  disabled,
}: SearchableSelectProps<TValue>) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchableSelectOption[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const loadDefault = useCallback(async () => {
    if (fetchOptions) {
      setBusy(true);
      try {
        const data = await fetchOptions("");
        setResults(data.slice(0, limit));
      } catch {
        setResults([]);
      } finally {
        setBusy(false);
      }
      setOpen(true);
    } else if (options) {
      setResults(options.slice(0, limit));
      setOpen(true);
    }
  }, [fetchOptions, options, limit]);

  const runSearch = useCallback(
    (q: string) => {
      let cancelled = false;
      const t = setTimeout(async () => {
        if (cancelled) return;
        setBusy(true);
        try {
          const data = fetchOptions
            ? await fetchOptions(q)
            : options?.filter((o) =>
                o.label.toLowerCase().includes(q.toLowerCase()),
              ) ?? [];
          if (cancelled) return;
          setResults(data.slice(0, limit));
          setOpen(true);
        } catch {
          if (!cancelled) setResults([]);
        } finally {
          if (!cancelled) setBusy(false);
        }
      }, 200);
      return () => {
        cancelled = true;
        clearTimeout(t);
      };
    },
    [fetchOptions, options, limit],
  );

  useEffect(() => {
    if (query.trim().length > 0) {
      const cancel = runSearch(query.trim());
      return () => cancel();
    }
    setResults([]);
  }, [query, runSearch]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const select = (opt: SearchableSelectOption) => {
    onChange(opt.id as TValue);
    setQuery(opt.label);
    setOpen(false);
  };

  const handleCreate = async () => {
    if (!query.trim() || creating || !onCreate || !creatable) return;
    setCreating(true);
    try {
      const created = await onCreate(query.trim());
      if (created) {
        select(created);
      }
    } finally {
      setCreating(false);
    }
  };

  return (
    <div ref={boxRef} className={`relative ${className ?? ""}`}>
      <Input
        disabled={disabled}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (query.trim().length > 0) {
            setOpen(true);
            return;
          }
          if (!initialized) {
            loadDefault();
            setInitialized(true);
          } else {
            setOpen(true);
          }
        }}
        placeholder={query ? "" : placeholder}
      />
      {!disabled && (
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4 pointer-events-none" />
      )}

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg max-h-60 overflow-y-auto">
          {busy && <div className="px-3 py-2 text-xs text-gray-400">Recherche…</div>}
          {results.length > 0 ? (
            results.map((opt) => (
              <button
                key={String(opt.id)}
                type="button"
                onClick={() => select(opt)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50"
              >
                <span className="font-medium text-gray-800">{opt.label}</span>
                {opt.subLabel && (
                  <span className="text-xs text-gray-500">{opt.subLabel}</span>
                )}
              </button>
            ))
          ) : (
            <div className="px-3 py-2 text-xs text-gray-400">
              Aucun résultat
            </div>
          )}
          {creatable && onCreate && (
            <div className="border-t border-gray-100 p-2">
              <Button
                size="sm"
                className="flex w-full items-center gap-2"
                disabled={busy || creating}
                onClick={handleCreate}
              >
                <UserPlus className="h-4 w-4" />
                {createLabel || `Créer « ${query.trim() || ""} »`}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
