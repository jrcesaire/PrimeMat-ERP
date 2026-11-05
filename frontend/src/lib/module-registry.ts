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
    label: "Ventes",
    description: "Devis et commandes clients",
    href: "/dashboard/sales",
    icon: ShoppingCart,
  },
  {
    key: "pos",
    module: "sales",
    label: "Point de vente",
    description: "Vente comptoir rapide",
    href: "/dashboard/sales/pos",
    icon: Store,
  },
  {
    key: "invoicing",
    module: "invoicing",
    label: "Facturation",
    description: "Factures clients",
    href: "/dashboard/invoicing",
    icon: FileText,
  },
  {
    key: "crm",
    module: "crm",
    label: "Contacts",
    description: "Clients et fournisseurs",
    href: "/dashboard/contacts",
    icon: Users,
  },
  {
    key: "catalogue",
    module: "catalogue",
    label: "Catalogue",
    description: "Produits et catégories",
    href: "/dashboard/catalogue",
    icon: Package,
  },
  {
    key: "stock",
    module: "stock",
    label: "Stock",
    description: "Inventaire et mouvements",
    href: "/dashboard/stock",
    icon: Warehouse,
  },
  {
    key: "delivery",
    module: "delivery",
    label: "Livraison",
    description: "Bons de livraison",
    href: "/dashboard/delivery",
    icon: Truck,
  },
  {
    key: "payments",
    module: "payments",
    label: "Paiements",
    description: "Encaissements et reçus",
    href: "/dashboard/payments",
    icon: CreditCard,
  },
  {
    key: "finance",
    module: "finance",
    label: "Dépenses",
    description: "Charges de l'entreprise",
    href: "/dashboard/expenses",
    icon: Receipt,
  },
  {
    key: "treasury",
    module: "finance",
    label: "Trésorerie",
    description: "Comptes, relevés et rapprochement",
    href: "/dashboard/treasury",
    icon: Landmark,
  },
  {
    key: "purchases",
    module: "purchases",
    label: "Achats",
    description: "Besoins d'achat fournisseurs",
    href: "/dashboard/purchases",
    icon: Tag,
  },
  {
    key: "accounting",
    module: "accounting",
    label: "Comptabilité",
    description: "Écritures et états financiers",
    href: "/dashboard/accounting",
    icon: BookOpen,
  },
  {
    key: "reporting",
    module: "reporting",
    label: "Reporting",
    description: "Indicateurs de performance",
    href: "/dashboard/reporting",
    icon: BarChart3,
  },
];