/**
 * Sous-menu dépliable d'une entrée de la sidebar.
 *
 * Dépliage / enroulage animés (hauteur + opacité, 300 ms) : la liste « pousse »
 * les entrées suivantes du menu. Si elle dépasse la hauteur allouée, elle
 * devient défilable (barre de défilement fine) — et à l'ouverture elle est
 * ramenée dans la zone visible de la sidebar.
 */
"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { isNavGroup, type NavChild } from "@/lib/nav-config";

/** Hauteur maximale de la liste dépliée — au-delà : défilement interne. */
const MAX_HEIGHT = "max-h-80";
/** Durée de l'animation de dépliage (doit rester alignée sur `duration-300`). */
const ANIMATION_MS = 320;

interface NavSubmenuProps {
  items: NavChild[];
  open: boolean;
  pathname: string | null;
}

export function NavSubmenu({ items, open, pathname }: NavSubmenuProps) {
  const listRef = useRef<HTMLDivElement>(null);

  // À l'ouverture, on amène la liste dépliée dans la zone visible de la sidebar
  // (après la fin de l'animation, pour que la position finale soit connue).
  useEffect(() => {
    if (!open) return;
    const el = listRef.current;
    if (!el) return;
    const timer = window.setTimeout(() => {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }, ANIMATION_MS);
    return () => window.clearTimeout(timer);
  }, [open]);

  return (
    <div
      ref={listRef}
      aria-hidden={!open}
      className={cn(
        "overflow-x-hidden overflow-y-auto transition-[max-height,opacity] duration-300 ease-in-out",
        "[scrollbar-color:rgb(75_85_99)_transparent] [scrollbar-width:thin]",
        open
          ? cn("mt-1 opacity-100", MAX_HEIGHT)
          : // `invisible` retire les liens du parcours clavier quand c'est replié.
            "invisible max-h-0 opacity-0",
      )}
    >
      <div className="space-y-0.5 pb-1">
        {items.map((child) =>
          isNavGroup(child) ? (
            <div key={child.label} className="pt-2">
              <p className="px-3 pl-10 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                {child.label}
              </p>
              <div className="mt-0.5 space-y-0.5">
                {child.items.map((leaf) => (
                  <SubmenuLink
                    key={leaf.label}
                    label={leaf.label}
                    href={leaf.href}
                    pathname={pathname}
                  />
                ))}
              </div>
            </div>
          ) : (
            <SubmenuLink
              key={child.label}
              label={child.label}
              href={child.href}
              pathname={pathname}
            />
          ),
        )}
      </div>
    </div>
  );
}

/** Lien d'un sous-menu (état actif = route courante). */
function SubmenuLink({
  label,
  href,
  pathname,
}: {
  label: string;
  href: string;
  pathname: string | null;
}) {
  const route = (pathname ?? "").replace(/\/+$/, "") || "/";
  const active = route === href;
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center rounded-md py-1.5 pl-10 pr-3 text-xs transition-colors",
        active
          ? "bg-gray-800 font-medium text-white"
          : "text-gray-400 hover:bg-gray-800 hover:text-white",
      )}
    >
      <span className="truncate">{label}</span>
    </Link>
  );
}
