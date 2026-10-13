/**
 * Lanceur d'applications — grille façon Odoo des modules ACTIVÉS.
 *
 * - Tuiles colorées des applications dont le module backend est actif
 * - Section « Autres applications disponibles » : modules installés mais
 *   désactivés (tuiles grisées → Paramètres pour activer)
 * - Généré dynamiquement : désactiver un module dans Paramètres le retire
 *   instantanément de l'accueil
 */
"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useModuleStates } from "@/hooks/useModules";
import { APP_TILES, type AppTile } from "@/lib/module-registry";
import { cn } from "@/lib/utils";

function Tile({
  app,
  disabled = false,
}: {
  app: AppTile;
  disabled?: boolean;
}) {
  const tooltip = disabled
    ? `${app.label} — Désactivé`
    : `${app.label} — ${app.description}`;
  const inner = (
    <Card
      title={tooltip}
      className={cn(
        "group flex cursor-pointer flex-col items-center gap-2 p-3 transition-all duration-200",
        disabled
          ? "cursor-default opacity-55 grayscale"
          : "hover:-translate-y-0.5 hover:shadow-lg"
      )}
    >
      <div
        className={cn(
          "flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-sm",
          app.gradient
        )}
      >
        <app.icon className="h-6 w-6" />
      </div>
      <p className="text-center text-sm font-semibold text-gray-900">{app.label}</p>
    </Card>
  );

  if (disabled) return inner;
  return (
    <Link href={app.href} aria-label={tooltip} title={tooltip}>
      {inner}
    </Link>
  );
}

export function AppLauncher() {
  const { data: moduleStates = [], isLoading } = useModuleStates();

  // Modules backend actifs (core exclu — pas une application métier)
  const activeModules = new Set(
    moduleStates
      .filter((m) => m.is_active && m.status === "active" && m.name !== "core")
      .map((m) => m.name)
  );

  const activeApps = APP_TILES.filter(
    (a) => a.always || activeModules.has(a.module)
  );

  // Modules installés mais désactivés → section « autres applications »
  const knownModules = new Set(
    APP_TILES.filter((a) => !a.always).map((a) => a.module)
  );
  const inactiveModules = moduleStates.filter(
    (m) =>
      m.name !== "core" &&
      knownModules.has(m.name) &&
      !activeModules.has(m.name) &&
      m.status !== "uninstalled"
  );

  // Applications du catalogue rattachées à un module désactivé
  const inactiveApps = APP_TILES.filter(
    (a) => !a.always && inactiveModules.some((m) => m.name === a.module)
  );
  // Dé-duplique : une seule tuile par module désactivé
  const seen = new Set<string>();
  const disabledApps = inactiveApps.filter((a) => {
    if (seen.has(a.module)) return false;
    seen.add(a.module);
    return true;
  });

  if (isLoading) {
    return (
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Applications</h2>
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-lg bg-gray-100"
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Applications</h2>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {activeApps.map((app) => (
          <Tile key={app.key} app={app} />
        ))}
      </div>

      {(disabledApps.length > 0 || activeApps.length === 0) && (
        <div className="mt-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-500">
            <Sparkles className="h-4 w-4" />
            Autres applications disponibles
          </h3>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {disabledApps.map((app) => (
              <Link key={`off-${app.key}`} href="/dashboard/settings">
                <Tile app={app} disabled />
              </Link>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Activez-les dans Paramètres → Modules. D&apos;autres applications
            pourront être ajoutées à l&apos;ERP.
          </p>
        </div>
      )}
    </section>
  );
}