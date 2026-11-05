/**
 * Layout des paramètres.
 *
 * Affiche la navigation secondaire du module « Paramètres » (mêmes sections que
 * le sous-menu de la sidebar, cf. `components/settings/settings-nav.tsx`)
 * au-dessus de l'écran de la section courante.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSettingsNav } from "@/components/settings/settings-nav";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const items = useSettingsNav();

  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-1 border-b border-line">
        {items.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-t-md px-4 py-2 text-sm transition-colors",
                isActive
                  ? "border-b-2 border-blue-600 font-medium text-blue-600"
                  : "text-muted hover:bg-subtle",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
