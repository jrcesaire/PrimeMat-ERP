/**
 * ModuleNav — navigation secondaire d'un module, en chips.
 *
 * C'est la seconde moitié du modèle de navigation : la sidebar garde ses
 * sous-menus dépliables, et **les modules riches exposent aussi leurs pages en
 * chips directement dans l'écran** (comme « Lettrage · Avoirs · Régime fiscal… »
 * sur l'écran Comptabilité de la maquette). L'utilisateur n'a donc pas besoin de
 * déplier le menu latéral pour changer de vue.
 *
 * Les entrées proviennent de `lib/nav-config` — la source unique de vérité — et
 * sont filtrées par permission exactement comme la sidebar.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Chip } from "@/components/ui/chip";
import { isNavGroup, NAV_ITEMS, type NavChild } from "@/lib/nav-config";
import { useCurrentUser, usePermission } from "@/hooks/useAuth";

/** Toutes les feuilles d'un sous-menu, groupes dépliés. */
function flattenLeaves(children: NavChild[] = []): { label: string; href: string; permission?: string }[] {
  return children.flatMap((child) =>
    isNavGroup(child) ? flattenLeaves(child.items) : [child],
  );
}

export function ModuleNav({
  moduleHref,
  className,
  /** Retire l'entrée qui pointe vers la racine du module (déjà dans l'en-tête). */
  excludeRoot = true,
}: {
  /** Route d'accueil du module, ex. `/dashboard/accounting`. */
  moduleHref: string;
  className?: string;
  excludeRoot?: boolean;
}) {
  const pathname = usePathname();
  const { data: currentUser } = useCurrentUser();
  const can = usePermission();
  // Profil non chargé : aucun filtrage (évite un clignotement au premier rendu).
  const isAllowed = (permission?: string) =>
    !permission || !currentUser || can(permission);

  const navItem = NAV_ITEMS.find((item) => item.href === moduleHref);
  const leaves = flattenLeaves(navItem?.children).filter(
    (leaf) => isAllowed(leaf.permission) && !(excludeRoot && leaf.href === moduleHref),
  );

  if (leaves.length === 0) return null;

  const route = (pathname ?? "").replace(/\/+$/, "") || "/";

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {leaves.map((leaf) => {
        const active = route === leaf.href;
        return (
          <Link key={leaf.href} href={leaf.href} aria-current={active ? "page" : undefined}>
            <Chip active={active}>{leaf.label}</Chip>
          </Link>
        );
      })}
    </div>
  );
}