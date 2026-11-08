/**
 * Catalogue d'affichage des modules — identité visuelle du lanceur d'applications.
 *
 * Chaque application du lanceur est rattachée à un module backend (`module`).
 * Une application n'apparaît que si son module est actif ; la même logique
 * pilotera les futurs modules (Discussion, Calendrier, Paie, …).
 */
import {
  BarChart3,
  LayoutDashboard,
  BookOpen,
  CreditCard,
  FileText,
  Landmark,
  Package,
  Receipt,
  ShoppingCart,
  Store,
  Tag,
  Truck,
  Users,
  Warehouse,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export interface AppTile {
  key: string;
  /** Module backend requis pour afficher l'application. */
  module: string;
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
  /**
   * Permission requise pour **voir** l'application (`ressource:action`).
   * Absente = visible par tous. Le superadministrateur voit toujours tout.
   * Une tuile dont l'utilisateur n'a pas la permission ne s'affiche pas :
   * l'accueil ne propose que ce qu'il est habilité à utiliser.
   */
  permission?: string;
  /** Toujours affichée, indépendamment de l état des modules. */
  always?: boolean;
}

export const APP_TILES: AppTile[] = [
  {
    key: "dashboard",
    module: "core",
    label: "Tableau de bord",
    description: "Vue d’ensemble de l’activité",
    href: "/dashboard",
    icon: LayoutDashboard,
    always: true,
  },
  {
    key: "sales",
    module: "sales",
    permission: "order:view",
    label: "Ventes",
    description: "Devis et commandes clients",
    href: "/dashboard/sales",
    icon: ShoppingCart,
  },
  {
    key: "pos",
    module: "sales",
    permission: "pos:view",
    label: "Point de vente",
    description: "Vente comptoir rapide",
    href: "/dashboard/sales/pos",
    icon: Store,
  },
  {
    key: "invoicing",
    module: "invoicing",
    permission: "invoice:view",
    label: "Facturation",
    description: "Factures clients",
    href: "/dashboard/invoicing",
    icon: FileText,
  },
  {
    key: "crm",
    module: "crm",
    permission: "partner:view",
    label: "Contacts",
    description: "Clients et fournisseurs",
    href: "/dashboard/contacts",
    icon: Users,
  },
  {
    key: "catalogue",
    module: "catalogue",
    permission: "product:view",
    label: "Catalogue",
    description: "Produits et catégories",
    href: "/dashboard/catalogue",
    icon: Package,
  },
  {
    key: "stock",
    module: "stock",
    permission: "stock_level:view",
    label: "Stock",
    description: "Inventaire et mouvements",
    href: "/dashboard/stock",
    icon: Warehouse,
  },
  {
    key: "delivery",
    module: "delivery",
    permission: "delivery:view",
    label: "Livraison",
    description: "Bons de livraison",
    href: "/dashboard/delivery",
    icon: Truck,
  },
  {
    key: "payments",
    module: "payments",
    permission: "payment:view",
    label: "Paiements",
    description: "Encaissements et reçus",
    href: "/dashboard/payments",
    icon: CreditCard,
  },
  {
    key: "finance",
    module: "finance",
    permission: "expense:view",
    label: "Dépenses",
    description: "Charges de l'entreprise",
    href: "/dashboard/expenses",
    icon: Receipt,
  },
  {
    key: "treasury",
    module: "finance",
    permission: "treasury:view",
    label: "Trésorerie",
    description: "Comptes, relevés et rapprochement",
    href: "/dashboard/treasury",
    icon: Landmark,
  },
  {
    key: "purchases",
    module: "purchases",
    permission: "purchase:view",
    label: "Achats",
    description: "Besoins d'achat fournisseurs",
    href: "/dashboard/purchases",
    icon: Tag,
  },
  {
    key: "accounting",
    module: "accounting",
    permission: "account:view",
    label: "Comptabilité",
    description: "Écritures et états financiers",
    href: "/dashboard/accounting",
    icon: BookOpen,
  },
  {
    key: "reporting",
    module: "reporting",
    permission: "report:view",
    label: "Reporting",
    description: "Indicateurs de performance",
    href: "/dashboard/reporting",
    icon: BarChart3,
  },
  {
    key: "payroll",
    module: "payroll",
    permission: "payslip:view",
    label: "Paie",
    description: "Employés, bulletins et déclarations",
    href: "/dashboard/payroll",
    icon: Wallet,
  },
];

export interface LauncherModuleState {
  name: string;
  status: string;
  is_active: boolean;
}

/**
 * Répartition des tuiles du lanceur selon l'état des modules et les droits.
 *
 * Une application sans ligne `module_infos` ne peut pas apparaître : la
 * synchronisation du registre backend est donc indispensable pour les modules
 * livrés après la création de la base. Une tuile désactivée reste proposée dans
 * la section d'activation, mais une tuile sans permission reste toujours cachée.
 */
export function partitionAppTiles(
  moduleStates: readonly LauncherModuleState[] | undefined,
  isAllowed: (app: AppTile) => boolean,
): { active: AppTile[]; disabled: AppTile[] } {
  if (!moduleStates) return { active: [], disabled: [] };

  const activeModules = new Set(
    moduleStates
      .filter(
        (module) =>
          module.is_active && module.status === "active" && module.name !== "core",
      )
      .map((module) => module.name),
  );
  const active = APP_TILES.filter(
    (app) =>
      (app.always || activeModules.has(app.module)) && isAllowed(app),
  );

  const knownModules = new Set(
    APP_TILES.filter((app) => !app.always).map((app) => app.module),
  );
  const inactiveModules = moduleStates.filter(
    (module) =>
      module.name !== "core" &&
      knownModules.has(module.name) &&
      !activeModules.has(module.name) &&
      module.status !== "uninstalled",
  );
  const inactive = APP_TILES.filter(
    (app) =>
      !app.always &&
      inactiveModules.some((module) => module.name === app.module) &&
      isAllowed(app),
  );

  // Une seule tuile par module désactivé, même si plusieurs routes en dépendent.
  const seen = new Set<string>();
  const disabled = inactive.filter((app) => {
    if (seen.has(app.module)) return false;
    seen.add(app.module);
    return true;
  });
  return { active, disabled };
}