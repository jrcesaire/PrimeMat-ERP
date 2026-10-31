/**
 * Dashboard d'accueil du module Point de Vente (PoS).
 *
 * Conforme au PRD « Improvements module PoS » :
 * - §4.2.1 Mode immersif : sidebar + header masqués, bouton « Quitter » en haut à gauche.
 * - §4.2.2 Écran d'accueil : 6 boutons centrés (Nouvelle Vente, Historique des Ventes,
 *   Ajout de Produits, Modifier Catalogue, Achats, Réglages), padding 80px à droite et
 *   à gauche (réduit à 20px sous 768px — §5.2).
 * - §7 Sécurité : la tuile « Réglages » n'est visible que pour les rôles
 *   Administrateur / Manager (ou superutilisateur).
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
  /** Libellé affiché sur le bouton. */
  label: string;
  /** Icône Lucide associée. */
  icon: React.ElementType;
  /** Destination au clic. */
  href: string;
  /** Bouton mis en avant (action principale du caissier). */
  primary?: boolean;
  /** Réservé aux rôles Administrateur / Manager (§7 du PRD). */
  restricted?: boolean;
}

const MENU_TILES: MenuTile[] = [
  {
    label: "Nouvelle Vente",
    icon: Plus,
    href: "/dashboard/sales/pos/vente?action=new",
    primary: true,
  },
  { label: "Historique des Ventes", icon: History, href: "/dashboard/sales/pos/vente" },
  { label: "Ajout de Produits", icon: PackagePlus, href: "/dashboard/catalogue/new" },
  { label: "Modifier Catalogue", icon: FolderCog, href: "/dashboard/catalogue" },
  { label: "Achats", icon: ShoppingBag, href: "/dashboard/purchases" },
  { label: "Réglages", icon: Settings, href: "/dashboard/sales/pos/reglages", restricted: true },
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
    <div className="min-h-screen bg-gray-50 flex flex-col px-[20px] md:px-[80px] py-6">
      {/* Bandeau : bouton « Quitter » en haut à gauche + info caisse en haut à droite */}
      <header className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={handleQuit}
          title="Quitter le mode PoS et revenir à l'ERP standard"
        >
          <LogOut className="h-4 w-4" />
          Quitter
        </Button>
        <div className="flex items-center gap-2 text-gray-600">
          <Store className="h-5 w-5" />
          <div className="text-right leading-tight">
            <div className="text-sm font-semibold text-gray-900">
              {company?.name ?? "Point de vente"}
            </div>
            <div className="text-xs text-gray-500">Caisse comptoir</div>
          </div>
        </div>
      </header>

      {/* Menu centralisé : centré horizontalement et verticalement (§4.2.2) */}
      <main className="flex-1 flex flex-col items-center justify-center gap-4 py-10">
        {tiles.map((tile) => (
          <Button
            key={tile.label}
            variant={tile.primary ? "default" : "outline"}
            size="lg"
            onClick={() => router.push(tile.href)}
            className={cn(
              "w-full max-w-[360px] h-14 justify-start gap-3 text-base",
              !tile.primary && "bg-white",
            )}
          >
            <tile.icon className="h-5 w-5" />
            {tile.label}
          </Button>
        ))}
      </main>
    </div>
  );
}
