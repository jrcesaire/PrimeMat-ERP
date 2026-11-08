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
import { ANIMATED_APP_ICONS } from "@/components/icons/animated-icons";
import { APP_ICONS } from "@/components/icons/app-icons";
import { cn } from "@/lib/utils";

/**
 * Largeur d'une tuile : 4 par ligne sur grand écran (grille de la maquette),
 * 2 sur tablette, 1 sur mobile. Combinée à `justify-center` sur le conteneur,
 * elle **centre la dernière ligne incomplète** (14 applications → 4 + 4 + 4 + 2)
 * au lieu de la coller à gauche — et tout module ajouté vient s'y aligner sans
 * déséquilibrer la mise en page.
 *
 * Les retraits (`-0.375rem` / `-0.5625rem`) correspondent aux gouttières de
 * `gap-3` (0,75 rem) : une ligne complète + ses gouttières tient exactement dans
 * la largeur du conteneur.
 */
const TILE_WIDTH =
  "w-full sm:w-[calc(50%-0.375rem)] lg:w-[calc(25%-0.5625rem)]";

function Tile({ app, disabled = false }: { app: AppTile; disabled?: boolean }) {
  const tooltip = disabled
    ? `${app.label} — Désactivé`
    : `${app.label} — ${app.description}`;
  // Visuel animé quand il existe — il prime sur le tracé vectoriel —, sinon
  // l'icône SVG dédiée, sinon l'icône Lucide du registre.
  const animated = ANIMATED_APP_ICONS[app.key];
  const SvgIcon = APP_ICONS[app.key];
  const inner = (
    <Card
      title={tooltip}
      className={cn(
        "group relative flex cursor-pointer flex-col items-center justify-center gap-3 p-4 text-center transition-colors",
        disabled ? "cursor-default opacity-55 grayscale" : "hover:border-primary/40",
      )}
    >
      {!disabled && (
        <ArrowUpRight className="absolute right-3 top-3 h-3.5 w-3.5 shrink-0 text-faint transition-colors group-hover:text-primary" />
      )}
      {animated ? (
        // Les visuels animés ont un fond blanc opaque : la pastille passe en
        // blanc pour que l'icône s'y fonde. L'animation boucle sans fin, donc
        // elle est figée sur sa première image quand le visiteur a demandé
        // moins de mouvement.
        <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-card bg-white">
          <picture>
            <source
              srcSet={animated.staticSrc}
              media="(prefers-reduced-motion: reduce)"
            />
            <img
              src={animated.src}
              alt=""
              aria-hidden="true"
              loading="lazy"
              decoding="async"
              className="h-full w-full object-contain"
            />
          </picture>
        </div>
      ) : (
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-card bg-primary-soft">
          {SvgIcon ? (
            <SvgIcon className="h-9 w-9" />
          ) : (
            <app.icon className="h-8 w-8 text-primary" />
          )}
        </div>
      )}
      <p className="text-[14px] font-semibold text-ink">{app.label}</p>
    </Card>
  );

  if (disabled) return inner;
  return (
    // Pas de `h-full` ici : le conteneur de la grille occupe la hauteur restante
    // de l'écran, et `height: 100%` étirerait chaque tuile sur toute cette
    // hauteur. Les tuiles d'une même ligne s'égalisent d'elles-mêmes
    // (`align-items: stretch` sur une hauteur automatique).
    <Link href={app.href} aria-label={tooltip} title={tooltip} className={cn("block", TILE_WIDTH)}>
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
      <section className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="h-10 w-full max-w-md shrink-0 animate-pulse rounded-control bg-subtle" />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="my-auto flex flex-wrap justify-center gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className={cn("h-[118px] animate-pulse rounded-card bg-subtle", TILE_WIDTH)}
              />
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-3">
      {/* Recherche et compteur sur une seule ligne : la hauteur de l'écran
          reste consacrée aux tuiles. */}
      <div className="flex shrink-0 flex-wrap items-center gap-3">
        <div className="flex h-10 w-full max-w-md items-center gap-2 rounded-control border border-line bg-surface px-3">
          <Search className="h-4 w-4 shrink-0 text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Trouver une application…"
            aria-label="Trouver une application"
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink placeholder:text-faint focus:outline-none"
          />
        </div>
        <div className="ml-auto flex items-center gap-3">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
            Applications disponibles
          </h2>
          <span className="text-[11px] text-faint">
            {visibleApps.length} module{visibleApps.length > 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Grille des applications actives — seule zone défilante de l'écran.
          `my-auto` sur la rangée de tuiles les centre dans la hauteur restante
          quand il y a de la place, et se résout à 0 quand elles débordent : le
          défilement repart alors du haut, sans contenu rogné (contrairement à
          un `align-content: center`). */}
      {visibleApps.length === 0 ? (
        <p className="py-10 text-center text-[13px] text-muted">
          Aucune application ne correspond à « {query} ».
        </p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="my-auto flex flex-wrap justify-center gap-3">
            {visibleApps.map((app) => (
              <Tile key={app.key} app={app} />
            ))}
          </div>
        </div>
      )}

      {/* Bandeau d'aide vers les paramètres */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-surface px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-subtle">
            <Settings className="h-4 w-4 text-muted" />
          </div>
          <div>
            <p className="text-[12px] font-semibold text-ink">
              Un ERP adapté à votre organisation
            </p>
            <p className="text-[11px] text-muted">
              Organisation, utilisateurs, droits d&apos;accès et préférences.
            </p>
          </div>
        </div>
        <Link
          href="/dashboard/settings"
          className="text-[12px] font-medium text-primary hover:underline"
        >
          Ouvrir les paramètres →
        </Link>
      </div>

      {/* Modules installés mais désactivés */}
      {disabledApps.length > 0 && (
        <div className="shrink-0">
          <h3 className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
            <Sparkles className="h-3.5 w-3.5" />
            Autres applications disponibles
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
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
          <p className="mt-2 text-[11px] text-faint">
            Activez-les dans Paramètres → Modules. D&apos;autres applications
            pourront être ajoutées à l&apos;ERP.
          </p>
        </div>
      )}
    </section>
  );
}