/**
 * Modèle de navigation de la sidebar — source unique de vérité.
 *
 * Chaque module déclare son entrée principale (`href`) et, si nécessaire, ses
 * sous-menus dépliables (`children`). Deux sortes d'enfants :
 * - `NavLeaf` : une page (lien direct) ;
 * - `NavGroup` : un intitulé de regroupement (non cliquable, ex. « Autres »
 *   en comptabilité) suivi de ses pages.
 *
 * Les sous-menus pointent vers des sous-routes réelles (`/dashboard/sales/orders`,
 * `/dashboard/accounting/balance`, …) : l'URL reste partageable et la page
 * ouvre directement le bon onglet.
 */
import type { ElementType } from "react";
import {
  BarChart3,
  BookOpen,
  CreditCard,
  FileText,
  LayoutDashboard,
  Package,
  Receipt,
  Settings,
  ShoppingCart,
  Store,
  Tag,
  Truck,
  Users,
  Warehouse,
} from "lucide-react";

/** Page cible d'un sous-menu. */
export interface NavLeaf {
  label: string;
  href: string;
}

/** Intitulé de regroupement à l'intérieur d'un sous-menu. */
export interface NavGroup {
  label: string;
  items: NavLeaf[];
}

export type NavChild = NavLeaf | NavGroup;

/** Entrée principale de la sidebar. */
export interface NavItem {
  label: string;
  href: string;
  icon: ElementType;
  /** Sous-menu dépliable (facultatif). */
  children?: NavChild[];
}

/** Distingue un regroupement d'une page dans un sous-menu. */
export function isNavGroup(child: NavChild): child is NavGroup {
  return Array.isArray((child as NavGroup).items);
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard },
  { label: "Point de vente", href: "/dashboard/sales/pos", icon: Store },
  {
    label: "Catalogue",
    href: "/dashboard/catalogue",
    icon: Package,
    children: [
      { label: "Scanner un produit", href: "/dashboard/catalogue/scan" },
      { label: "Nouveau produit", href: "/dashboard/catalogue/new" },
    ],
  },
  {
    label: "Contacts",
    href: "/dashboard/contacts",
    icon: Users,
    children: [
      { label: "Tous", href: "/dashboard/contacts" },
      { label: "Clients", href: "/dashboard/contacts/clients" },
      { label: "Fournisseurs", href: "/dashboard/contacts/fournisseurs" },
    ],
  },
  {
    label: "Ventes",
    href: "/dashboard/sales",
    icon: ShoppingCart,
    children: [
      { label: "Nouveau devis", href: "/dashboard/sales/quotes/new" },
      { label: "Devis", href: "/dashboard/sales/quotes" },
      { label: "Commandes", href: "/dashboard/sales/orders" },
    ],
  },
  { label: "Stock", href: "/dashboard/stock", icon: Warehouse },
  {
    label: "Achats",
    href: "/dashboard/purchases",
    icon: Tag,
    children: [
      { label: "Nouvelle demande", href: "/dashboard/purchases/demandes" },
      { label: "Demandes", href: "/dashboard/purchases/demandes" },
      { label: "Bons de commande", href: "/dashboard/purchases/commandes" },
      { label: "Réceptions", href: "/dashboard/purchases/receptions" },
      { label: "Factures fournisseur", href: "/dashboard/purchases/factures" },
      { label: "Fournisseurs", href: "/dashboard/purchases/fournisseurs" },
      { label: "Suggestions", href: "/dashboard/purchases/suggestions" },
      { label: "Besoins (ventes)", href: "/dashboard/purchases/besoins" },
    ],
  },
  {
    label: "Livraison",
    href: "/dashboard/delivery",
    icon: Truck,
    children: [
      { label: "Créer un bon de livraison", href: "/dashboard/delivery/new" },
      { label: "Liste des bons", href: "/dashboard/delivery" },
    ],
  },
  {
    label: "Facturation",
    href: "/dashboard/invoicing",
    icon: FileText,
    children: [
      { label: "Créer une facture", href: "/dashboard/invoicing/new" },
      { label: "Liste des factures", href: "/dashboard/invoicing" },
    ],
  },
  {
    label: "Paiements",
    href: "/dashboard/payments",
    icon: CreditCard,
    children: [
      { label: "Encaisser", href: "/dashboard/payments/new" },
      { label: "Liste des paiements", href: "/dashboard/payments" },
    ],
  },
  {
    label: "Dépenses",
    href: "/dashboard/expenses",
    icon: Receipt,
    children: [
      { label: "Nouvelle dépense", href: "/dashboard/expenses/new" },
      { label: "Journal de dépenses", href: "/dashboard/expenses" },
    ],
  },
  {
    label: "Comptabilité",
    href: "/dashboard/accounting",
    icon: BookOpen,
    children: [
      { label: "Balance", href: "/dashboard/accounting/balance" },
      { label: "Compte de résultat", href: "/dashboard/accounting/income" },
      { label: "Bilan", href: "/dashboard/accounting/sheet" },
      { label: "Écritures", href: "/dashboard/accounting/entries" },
      {
        label: "Autres",
        items: [
          { label: "Lettrage", href: "/dashboard/accounting/allocations" },
          { label: "Avoirs", href: "/dashboard/accounting/credit-notes" },
          { label: "Régime fiscal", href: "/dashboard/accounting/fiscal-regime" },
          { label: "Balance âgée", href: "/dashboard/accounting/aged-balance" },
          { label: "Cash-flow", href: "/dashboard/accounting/cash-flow" },
          {
            label: "Assistant de configuration",
            href: "/dashboard/accounting/setup",
          },
        ],
      },
    ],
  },
  { label: "Reporting", href: "/dashboard/reporting", icon: BarChart3 },
  { label: "Paramètres", href: "/dashboard/settings", icon: Settings },
];
