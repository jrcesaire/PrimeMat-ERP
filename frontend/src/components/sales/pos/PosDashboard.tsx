/**
 * Menu d'accueil du module Point de Vente.
 *
 * Les six entrées sont présentées en **cartes sur 2 lignes et 3 colonnes**,
 * dans le même esprit que les tuiles du catalogue et des contacts : icône
 * encadrée, libellé et description, le tout centré dans la carte.
 *
 * Le mode immersif (sidebar + header masqués) reste porté par `setPosFocus`,
 * et la tuile « Réglages » demeure réservée aux rôles Administrateur /
 * Manager (PRD « Improvements module PoS » §7).
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  FolderCog,
  History,
  LogOut,
  PackagePlus,
  Plus,
  Settings,
  ShoppingBag,
  Store,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentCompany, useCurrentUser } from "@/hooks/useAuth";
import { setPosFocus } from "@/lib/pos-focus";
import { cn } from "@/lib/utils";

interface MenuTile {
  /** Libellé affiché sur la carte. */
  label: string;
  /** Phrase d'accompagnement. */
  description: string;
  /** Icône associée. */
  icon: React.ElementType;
  /** Destination au clic. */
  href: string;
  /** Carte mise en avant (action principale du caissier). */
  primary?: boolean;
  /** Réservée aux rôles Administrateur / Manager (§7 du PRD). */
  restricted?: boolean;
}

const MENU_TILES: MenuTile[] = [
  {
    label: "Nouvelle Vente",
    description: "Encaisser une vente comptoir",
    icon: Plus,
    href: "/dashboard/sales/pos/vente?action=new",
    primary: true,
  },
  {
    label: "Historique des Ventes",
    description: "Consulter et réimprimer les tickets",
    icon: History,
    href: "/dashboard/sales/pos/vente",
  },
  {
    label: "Ajout de Produits",
    description: "Créer un article au catalogue",
    icon: PackagePlus,
    href: "/dashboard/catalogue/new",
  },
  {
    label: "Modifier Catalogue",
    description: "Parcourir et corriger les articles",
    icon: FolderCog,
    href: "/dashboard/catalogue",
  },
  {
    label: "Achats",
    description: "Saisir un achat de quincaillerie",
    icon: ShoppingBag,
    href: "/dashboard/sales/pos/achats",
  },
  {
    label: "Réglages",
    description: "Paramétrer la caisse et les tickets",
    icon: Settings,
    href: "/dashboard/sales/pos/reglages",
    restricted: true,
  },
];

export function PosDashboard() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const { data: company } = useCurrentCompany();

  // Mode immersif : masquer sidebar + header tant qu'on reste dans le PoS.
  useEffect(() => {
    setPosFocus(true);
    return () => setPosFocus(false);
  }, []);

  // §7 — Réglages réservés aux rôles Administrateur / Manager.
  const canAccessSettings =
    currentUser?.is_superuser === true ||
    (currentUser?.roles ?? []).some(
      (role) => role.code === "admin" || role.code === "manager",
    );

  const tiles = MENU_TILES.filter((tile) => !tile.restricted || canAccessSettings);

  const handleQuit = () => {
    // Ferme l'interface PoS et restaure l'ERP standard (sidebar de nouveau visible).
    setPosFocus(false);
    router.push("/dashboard/sales");
  };

  return (
    <div className="flex min-h-screen flex-col bg-canvas px-8 py-6">
      {/* Bandeau : bouton « Quitter » à gauche, caisse courante à droite */}
      <header className="flex shrink-0 items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={handleQuit}
          title="Quitter le mode Point de vente et revenir à l'ERP"
        >
          <LogOut className="h-4 w-4" />
          Quitter
        </Button>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-control bg-primary-soft">
            <Store className="h-5 w-5 text-primary" />
          </div>
          <div className="text-right leading-tight">
            <p className="text-[13px] font-semibold text-ink">
              {company?.name ?? "Point de vente"}
            </p>
            <p className="text-[11px] text-muted">Caisse comptoir</p>
          </div>
        </div>
      </header>

      {/* Les six entrées, centrées dans la page */}
      <main className="flex flex-1 items-center justify-center py-8">
        <div className="grid w-full max-w-5xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {tiles.map((tile) => (
            <button
              key={tile.label}
              type="button"
              onClick={() => router.push(tile.href)}
              className={cn(
                "group flex min-h-[190px] flex-col items-center justify-center gap-4 rounded-card border p-6 text-center transition-colors",
                tile.primary
                  ? "border-primary bg-primary text-white hover:bg-primary-hover"
                  : "border-line bg-surface hover:border-primary/40",
              )}
            >
              <span
                className={cn(
                  "flex h-14 w-14 shrink-0 items-center justify-center rounded-control",
                  tile.primary ? "bg-white/15" : "bg-primary-soft",
                )}
              >
                <tile.icon
                  className={cn(
                    "h-7 w-7",
                    tile.primary ? "text-white" : "text-primary",
                  )}
                />
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block text-[15px] font-semibold",
                    tile.primary ? "text-white" : "text-ink",
                  )}
                >
                  {tile.label}
                </span>
                <span
                  className={cn(
                    "mt-1 block text-[12px] leading-snug",
                    tile.primary ? "text-white/80" : "text-muted",
                  )}
                >
                  {tile.description}
                </span>
              </span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
