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
  Landmark,
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
  /**
   * Permission requise pour afficher l'entrée (code « ressource:action »,
   * ex. `invoice:create`). Absente = visible par tous.
   *
   * Les codes reprennent ceux réellement exigés par les endpoints backend :
   * afficher une entrée que l'API refuse (403) n'aurait pas de sens.
   * Le superadministrateur voit toujours tout (cf. `usePermission`).
   */
  permission?: string;
}

/** Intitulé de regroupement à l'intérieur d'un sous-menu. */
export interface NavGroup {
  label: string;
  items: NavLeaf[];
}

export type NavChild = NavLeaf | NavGroup;

/**
 * Regroupements de la sidebar, dans l'ordre d'affichage de la maquette.
 * Une entrée sans `section` est affichée seule, après les groupes.
 */
export type NavSection = "workspace" | "commercial" | "finance";

export const NAV_SECTIONS: { key: NavSection; label: string }[] = [
  { key: "workspace", label: "Espace de travail" },
  { key: "commercial", label: "Gestion commerciale" },
  { key: "finance", label: "Finances" },
];

/** Entrée principale de la sidebar. */
export interface NavItem {
  label: string;
  href: string;
  icon: ElementType;
  /**
   * Permission exigée par la page d'accueil du module (ex. `pos:view` pour
   * « Point de vente »). Absente = module visible par tous.
   *
   * Un module reste affiché même sans cette permission dès lors que son
   * sous-menu conserve au moins une page accessible (cf. `Sidebar`) : le
   * vendeur voit ainsi « Achats » pour « Besoins (ventes) ».
   */
  permission?: string;
  /** Groupe d'affichage dans la sidebar (cf. `NAV_SECTIONS`). */
  section?: NavSection;
  /** Sous-menu dépliable (facultatif). */
  children?: NavChild[];
}

/** Distingue un regroupement d'une page dans un sous-menu. */
export function isNavGroup(child: NavChild): child is NavGroup {
  return Array.isArray((child as NavGroup).items);
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard, section: "workspace" },
  {
    label: "Point de vente",
    href: "/dashboard/sales/pos",
    icon: Store,
    permission: "pos:view",
    section: "workspace",
  },
  {
    label: "Catalogue",
    href: "/dashboard/catalogue",
    icon: Package,
    permission: "product:view",
    section: "commercial",
    children: [
      {
        label: "Scanner un produit",
        href: "/dashboard/catalogue/scan",
        permission: "product:view",
      },
      {
        label: "Nouveau produit",
        href: "/dashboard/catalogue/new",
        permission: "product:create",
      },
    ],
  },
  {
    label: "Contacts",
    href: "/dashboard/contacts",
    icon: Users,
    permission: "partner:view",
    section: "commercial",
    children: [
      { label: "Tous", href: "/dashboard/contacts", permission: "partner:view" },
      {
        label: "Clients",
        href: "/dashboard/contacts/clients",
        permission: "partner:view",
      },
      {
        label: "Fournisseurs",
        href: "/dashboard/contacts/fournisseurs",
        permission: "partner:view",
      },
    ],
  },
  {
    label: "Ventes",
    href: "/dashboard/sales",
    icon: ShoppingCart,
    permission: "quote:view",
    section: "commercial",
    children: [
      {
        label: "Nouveau devis",
        href: "/dashboard/sales/quotes/new",
        permission: "quote:create",
      },
      {
        label: "Devis",
        href: "/dashboard/sales/quotes",
        permission: "quote:view",
      },
      {
        label: "Commandes",
        href: "/dashboard/sales/orders",
        permission: "order:view",
      },
    ],
  },
  {
    label: "Stock",
    href: "/dashboard/stock",
    icon: Warehouse,
    permission: "stock_level:view",
    section: "commercial",
  },
  {
    label: "Achats",
    href: "/dashboard/purchases",
    icon: Tag,
    permission: "purchase:view",
    section: "commercial",
    children: [
      {
        label: "Demandes",
        href: "/dashboard/purchases/demandes",
        permission: "purchase_request:view",
      },
      {
        label: "Bons de commande",
        href: "/dashboard/purchases/commandes",
        permission: "purchase_order:view",
      },
      {
        label: "Réceptions",
        href: "/dashboard/purchases/receptions",
        permission: "purchase_reception:view",
      },
      {
        label: "Factures fournisseur",
        href: "/dashboard/purchases/factures",
        permission: "purchase_invoice:view",
      },
      {
        label: "Fournisseurs",
        href: "/dashboard/purchases/fournisseurs",
        permission: "purchase:view",
      },
      {
        label: "Suggestions",
        href: "/dashboard/purchases/suggestions",
        permission: "purchase:view",
      },
      {
        label: "Besoins (ventes)",
        href: "/dashboard/purchases/besoins",
        permission: "order:view",
      },
    ],
  },
  {
    label: "Livraison",
    href: "/dashboard/delivery",
    icon: Truck,
    permission: "delivery:view",
    section: "commercial",
    children: [
      {
        label: "Créer un bon de livraison",
        href: "/dashboard/delivery/new",
        permission: "delivery:create",
      },
      {
        label: "Liste des bons",
        href: "/dashboard/delivery",
        permission: "delivery:view",
      },
    ],
  },
  {
    label: "Facturation",
    href: "/dashboard/invoicing",
    icon: FileText,
    permission: "invoice:view",
    section: "finance",
    children: [
      {
        label: "Créer une facture",
        href: "/dashboard/invoicing/new",
        permission: "invoice:create",
      },
      {
        label: "Liste des factures",
        href: "/dashboard/invoicing",
        permission: "invoice:view",
      },
    ],
  },
  {
    label: "Paiements",
    href: "/dashboard/payments",
    icon: CreditCard,
    permission: "payment:view",
    section: "finance",
    children: [
      {
        label: "Encaisser",
        href: "/dashboard/payments/new",
        permission: "payment:create",
      },
      {
        label: "Liste des paiements",
        href: "/dashboard/payments",
        permission: "payment:view",
      },
    ],
  },
  {
    label: "Dépenses",
    href: "/dashboard/expenses",
    icon: Receipt,
    permission: "expense:view",
    section: "finance",
    children: [
      {
        label: "Nouvelle dépense",
        href: "/dashboard/expenses/new",
        permission: "expense:create",
      },
      {
        label: "Journal de dépenses",
        href: "/dashboard/expenses",
        permission: "expense:view",
      },
    ],
  },
  {
    label: "Trésorerie",
    href: "/dashboard/treasury",
    icon: Landmark,
    permission: "treasury:view",
    section: "finance",
  },
  {
    label: "Comptabilité",
    href: "/dashboard/accounting",
    icon: BookOpen,
    permission: "account:view",
    section: "finance",
    children: [
      {
        label: "Balance",
        href: "/dashboard/accounting/balance",
        permission: "account:view",
      },
      {
        label: "Compte de résultat",
        href: "/dashboard/accounting/income",
        permission: "account:view",
      },
      {
        label: "Bilan",
        href: "/dashboard/accounting/sheet",
        permission: "account:view",
      },
      {
        label: "Écritures",
        href: "/dashboard/accounting/entries",
        permission: "account:view",
      },
      {
        label: "Autres",
        items: [
          {
            label: "Lettrage",
            href: "/dashboard/accounting/allocations",
            permission: "account:view",
          },
          {
            label: "Avoirs",
            href: "/dashboard/accounting/credit-notes",
            permission: "journal_entry:view",
          },
          {
            label: "Régime fiscal",
            href: "/dashboard/accounting/fiscal-regime",
            permission: "company:view",
          },
          {
            label: "Balance âgée",
            href: "/dashboard/accounting/aged-balance",
            permission: "account:view",
          },
          {
            label: "Cash-flow",
            href: "/dashboard/accounting/cash-flow",
            permission: "account:view",
          },
          {
            label: "Grand livre",
            href: "/dashboard/accounting/ledger",
            permission: "account:view",
          },
          {
            label: "Grand livre auxiliaire",
            href: "/dashboard/accounting/partner-ledger",
            permission: "account:view",
          },
          {
            label: "Chéancier",
            href: "/dashboard/accounting/payment-schedule",
            permission: "account:view",
          },
          {
            label: "TVA déclarative",
            href: "/dashboard/accounting/vat",
            permission: "account:view",
          },
          {
            label: "Immobilisations",
            href: "/dashboard/accounting/fixed-assets",
            permission: "account:view",
          },
          {
            label: "Clôture d'exercice",
            href: "/dashboard/accounting/fiscal-year",
            permission: "fiscal_year:view",
          },
          {
            label: "Journal d'audit",
            href: "/dashboard/accounting/audit",
            permission: "audit_log:view",
          },
          {
            label: "Assistant de configuration",
            href: "/dashboard/accounting/setup",
            permission: "account:edit",
          },
        ],
      },
    ],
  },
  { label: "Reporting", href: "/dashboard/reporting", icon: BarChart3 },
  { label: "Paramètres", href: "/dashboard/settings", icon: Settings },
];

/**
 * Retire d'une liste de sous-menus les pages dont la permission manque.
 *
 * Un groupe (ex. « Autres ») dont toutes les pages sont retirées disparaît à
 * son tour : aucun intitulé ne reste sans contenu. Fonction pure — la règle
 * « superadministrateur » est portée par `isAllowed` (`usePermission`).
 */
export function filterNavChildren(
  items: NavChild[],
  isAllowed: (permission?: string) => boolean,
): NavChild[] {
  return items
    .map((child) =>
      isNavGroup(child)
        ? {
            ...child,
            items: child.items.filter((leaf) => isAllowed(leaf.permission)),
          }
        : child,
    )
    .filter((child) =>
      isNavGroup(child) ? child.items.length > 0 : isAllowed(child.permission),
    );
}

/** Route du module Paramètres — ses sections viennent de `useSettingsNav`. */
export const SETTINGS_HREF = "/dashboard/settings";

/**
 * Modules à afficher dans la sidebar, chacun avec son sous-menu déjà filtré.
 *
 * Un module dont la page d'accueil est interdite disparaît, sauf s'il conserve
 * au moins une page accessible dans son sous-menu : le vendeur garde ainsi
 * « Achats » pour « Besoins (ventes) » sans détenir `purchase:view`.
 *
 * `settingsChildren` reçoit les sections du module Paramètres, calculées par un
 * hook (`useSettingsNav`) et déjà filtrées par permission.
 */
export function visibleNavModules(
  isAllowed: (permission?: string) => boolean,
  settingsChildren: NavLeaf[] = [],
): { item: NavItem; children: NavChild[] }[] {
  return NAV_ITEMS.map((item) => ({
    item,
    children:
      item.href === SETTINGS_HREF
        ? settingsChildren
        : filterNavChildren(item.children ?? [], isAllowed),
  })).filter(
    ({ item, children }) => isAllowed(item.permission) || children.length > 0,
  );
}
