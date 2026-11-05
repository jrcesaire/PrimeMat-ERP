/**
 * Lanceur d'applications — grille des modules ACTIVÉS.
 *
 * Design « GEA ERP » : recherche « Trouver une application… », en-tête de
 * section avec compteur, grille de 4 colonnes de tuiles (icône colorée, libellé,
 * flèche d'ouverture, description) et bandeau « Un ERP adapté à votre
 * organisation ».
 *
 * - Tuiles des applications dont le module backend est actif ;
 * - Section « Autres applications disponibles » : modules installés mais
 *   désactivés (tuiles grisées → Paramètres pour activer) ;
 * - Généré dynamiquement : désactiver un module dans Paramètres le retire
 *   instantanément de l'accueil.
 */
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Search, Settings, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useModuleStates } from "@/hooks/useModules";
import { APP_TILES, type AppTile } from "@/lib/module-registry";
import { APP_ICONS } from "@/components/icons/app-icons";
import { cn } from "@/lib/utils";

/**
 * Largeur d'une tuile : 4 par ligne sur grand écran, 2 sur tablette, 1 sur
 * mobile. Combinée à `justify-center` sur le conteneur, elle **centre la
 * dernière ligne incomplète** (ex. « Comptabilité » et « Reporting ») au lieu
 * de la coller à gauche — et tout module ajouté vient s'y aligner sans
 * déséquilibrer la mise en page.
 */
const TILE_WIDTH =
  "w-full sm:w-[calc(50%-0.5rem)] lg:w-[calc(25%-0.75rem)]";

function Tile({ app, disabled = false }: { app: AppTile; disabled?: boolean }) {
  const tooltip = disabled
    ? `${app.label} — Désactivé`
    : `${app.label} — ${app.description}`;
  // Icône SVG dédiée quand elle existe, sinon l'icône Lucide du registre.
  const SvgIcon = APP_ICONS[app.key];
  const inner = (
    <Card
      title={tooltip}
      className={cn(
        "group relative flex h-full cursor-pointer flex-col items-center justify-center gap-4 p-5 text-center transition-colors",
        disabled ? "cursor-default opacity-55 grayscale" : "hover:border-primary/40",
      )}
    >
      {!disabled && (
        <ArrowUpRight className="absolute right-4 top-4 h-4 w-4 shrink-0 text-faint transition-colors group-hover:text-primary" />
      )}
      <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-card bg-primary-soft">
        {SvgIcon ? (
          <SvgIcon className="h-10 w-10" />
        ) : (
          <app.icon className="h-9 w-9 text-primary" />
        )}
      </div>
      <p className="text-[15px] font-semibold text-ink">{app.label}</p>
    </Card>
  );

  if (disabled) return inner;
  return (
    <Link href={app.href} aria-label={tooltip} title={tooltip} className={cn("block h-full", TILE_WIDTH)}>
      {inner}
    </Link>
  );
}

export function AppLauncher() {
  const { data: moduleStates = [], isLoading } = useModuleStates();
  const [query, setQuery] = useState("");

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

  // Filtre de recherche local sur le libellé et la description.
  const visibleApps = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return activeApps;
    return activeApps.filter(
      (a) =>
        a.label.toLowerCase().includes(needle) ||
        a.description.toLowerCase().includes(needle),
    );
  }, [activeApps, query]);

  if (isLoading) {
    return (
      <section className="space-y-6">
        <div className="mx-auto h-10 w-full max-w-md animate-pulse rounded-control bg-subtle" />
        <div className="flex flex-wrap justify-center gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className={cn("h-36 animate-pulse rounded-card bg-subtle", TILE_WIDTH)}
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-8">
      {/* Recherche d'application */}
      <div className="mx-auto flex h-10 w-full max-w-md items-center gap-2 rounded-control border border-line bg-surface px-3">
        <Search className="h-4 w-4 shrink-0 text-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Trouver une application…"
          aria-label="Trouver une application"
          className="min-w-0 flex-1 bg-transparent text-[13px] text-ink placeholder:text-faint focus:outline-none"
        />
      </div>

      {/* En-tête de section */}
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
          Applications disponibles
        </h2>
        <span className="text-[11px] text-faint">
          {visibleApps.length} module{visibleApps.length > 1 ? "s" : ""}
        </span>
      </div>

      {/* Grille des applications actives */}
      {visibleApps.length === 0 ? (
        <p className="py-10 text-center text-[13px] text-muted">
          Aucune application ne correspond à « {query} ».
        </p>
      ) : (
        <div className="flex flex-wrap justify-center gap-4">
          {visibleApps.map((app) => (
            <Tile key={app.key} app={app} />
          ))}
        </div>
      )}

      {/* Bandeau d'aide vers les paramètres */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-line bg-surface p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-subtle">
            <Settings className="h-5 w-5 text-muted" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-ink">
              Un ERP adapté à votre organisation
            </p>
            <p className="text-[12px] text-muted">
              Organisation, utilisateurs, droits d&apos;accès et préférences.
            </p>
          </div>
        </div>
        <Link
          href="/dashboard/settings"
          className="text-[13px] font-medium text-primary hover:underline"
        >
          Ouvrir les paramètres →
        </Link>
      </div>

      {/* Modules installés mais désactivés */}
      {disabledApps.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
            <Sparkles className="h-4 w-4" />
            Autres applications disponibles
          </h3>
          <div className="flex flex-wrap justify-center gap-4">
            {disabledApps.map((app) => (
              <Link
                key={`off-${app.key}`}
                href="/dashboard/settings"
                className={TILE_WIDTH}
              >
                <Tile app={app} disabled />
              </Link>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-faint">
            Activez-les dans Paramètres → Modules. D&apos;autres applications
            pourront être ajoutées à l&apos;ERP.
          </p>
        </div>
      )}
    </section>
  );
}