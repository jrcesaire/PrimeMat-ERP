/**
 * Recherche globale du header — « Rechercher dans … ⌘ K ».
 *
 * Filtre les modules et leurs pages déclarés dans `lib/nav-config` (source
 * unique de vérité) et navigue vers la page choisie. Raccourci `⌘ K` / `Ctrl K`
 * pour donner le focus, `Échap` pour fermer.
 *
 * Les entrées sont filtrées par permission, comme la sidebar : la recherche ne
 * propose jamais une page que l'API refuserait.
 */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { isNavGroup, NAV_ITEMS, type NavChild } from "@/lib/nav-config";
import { usePermission } from "@/hooks/useAuth";

interface SearchEntry {
  label: string;
  href: string;
  /** Module de rattachement, affiché en second plan dans les résultats. */
  module: string;
  permission?: string;
}

/** Aplatit `NAV_ITEMS` (module + sous-pages) en une liste cherchable. */
export function flattenNavEntries(): SearchEntry[] {
  const entries: SearchEntry[] = [];
  const pushLeaves = (module: string, children: NavChild[]) => {
    for (const child of children) {
      if (isNavGroup(child)) {
        pushLeaves(module, child.items);
        continue;
      }
      entries.push({
        label: child.label,
        href: child.href,
        module,
        permission: child.permission,
      });
    }
  };

  for (const item of NAV_ITEMS) {
    entries.push({
      label: item.label,
      href: item.href,
      module: item.label,
      permission: item.permission,
    });
    if (item.children) pushLeaves(item.label, item.children);
  }
  return entries;
}

export function GlobalSearch({ className }: { className?: string }) {
  const router = useRouter();
  const can = usePermission();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  // `⌘ K` (macOS) / `Ctrl K` (Windows, Linux) place le focus dans la recherche.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const entries = useMemo(
    () => flattenNavEntries().filter((e) => !e.permission || can(e.permission)),
    [can],
  );

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return [];
    return entries
      .filter(
        (e) =>
          e.label.toLowerCase().includes(needle) ||
          e.module.toLowerCase().includes(needle),
      )
      .slice(0, 8);
  }, [entries, query]);

  const go = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };

  return (
    <div className={cn("relative", className)}>
      <div className="flex h-10 items-center gap-2 rounded-control bg-subtle px-3">
        <Search className="h-4 w-4 shrink-0 text-faint" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && results[0]) go(results[0].href);
          }}
          placeholder="Rechercher…"
          aria-label="Recherche globale"
          className="min-w-0 flex-1 bg-transparent text-[13px] text-ink placeholder:text-faint focus:outline-none"
        />
        <kbd className="hidden shrink-0 rounded-chip border border-line px-1.5 py-0.5 text-[10px] text-faint sm:inline-block">
          ⌘ K
        </kbd>
      </div>

      {open && results.length > 0 && (
        <ul className="absolute left-0 right-0 top-11 z-50 max-h-80 overflow-y-auto rounded-card border border-line bg-surface py-1 shadow-pop">
          {results.map((entry) => (
            <li key={`${entry.module}-${entry.href}`}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => go(entry.href)}
                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-subtle"
              >
                <span className="truncate text-[13px] text-ink">{entry.label}</span>
                <span className="shrink-0 text-[11px] text-faint">
                  {entry.module}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}