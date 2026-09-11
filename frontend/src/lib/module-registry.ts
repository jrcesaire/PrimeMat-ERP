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
  /** Classes gradient de la tuile (façon icône colorée Odoo). */
  gradient: string;
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
    gradient: "from-blue-500 to-blue-700",
    always: true,
  },
  {
    key: "sales",
    module: "sales",
    label: "Ventes",
    description: "Devis et commandes clients",
    href: "/dashboard/sales",
    icon: ShoppingCart,
    gradient: "from-orange-400 to-orange-600",
  },
  {
    key: "pos",
    module: "sales",
    label: "Point de vente",
    description: "Vente comptoir rapide",
    href: "/dashboard/sales/pos",
    icon: Store,
    gradient: "from-teal-400 to-teal-600",
  },
  {
    key: "invoicing",
    module: "invoicing",
    label: "Facturation",
    description: "Factures clients",
    href: "/dashboard/invoicing",
    icon: FileText,
    gradient: "from-blue-400 to-blue-600",
  },
  {
    key: "crm",
    module: "crm",
    label: "Contacts",
    description: "Clients et fournisseurs",
    href: "/dashboard/contacts",
    icon: Users,
    gradient: "from-indigo-400 to-indigo-600",
  },
  {
    key: "catalogue",
    module: "catalogue",
    label: "Catalogue",
    description: "Produits et catégories",
    href: "/dashboard/catalogue",
    icon: Package,
    gradient: "from-violet-400 to-violet-600",
  },
  {
    key: "stock",
    module: "stock",
    label: "Stock",
    description: "Inventaire et mouvements",
    href: "/dashboard/stock",
    icon: Warehouse,
    gradient: "from-cyan-400 to-cyan-600",
  },
  {
    key: "delivery",
    module: "delivery",
    label: "Livraison",
    description: "Bons de livraison",
    href: "/dashboard/delivery",
    icon: Truck,
    gradient: "from-emerald-400 to-emerald-600",
  },
  {
    key: "payments",
    module: "payments",
    label: "Paiements",
    description: "Encaissements et reçus",
    href: "/dashboard/payments",
    icon: CreditCard,
    gradient: "from-rose-400 to-rose-600",
  },
  {
    key: "finance",
    module: "finance",
    label: "Dépenses",
    description: "Charges de l'entreprise",
    href: "/dashboard/expenses",
    icon: Receipt,
    gradient: "from-fuchsia-400 to-fuchsia-600",
  },
  {
    key: "purchases",
    module: "purchases",
    label: "Achats",
    description: "Besoins d'achat fournisseurs",
    href: "/dashboard/purchases",
    icon: Tag,
    gradient: "from-lime-400 to-lime-600",
  },
  {
    key: "accounting",
    module: "accounting",
    label: "Comptabilité",
    description: "Écritures et états financiers",
    href: "/dashboard/accounting",
    icon: BookOpen,
    gradient: "from-sky-400 to-sky-600",
  },
  {
    key: "reporting",
    module: "reporting",
    label: "Reporting",
    description: "Indicateurs de performance",
    href: "/dashboard/reporting",
    icon: BarChart3,
    gradient: "from-purple-400 to-purple-600",
  },
];