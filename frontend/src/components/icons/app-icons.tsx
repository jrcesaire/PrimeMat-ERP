/**
 * Icônes d'application du lanceur.
 *
 * Reproduites en SVG d'après les visuels fournis, mais **recolorées avec la
 * palette de l'application** : chaque icône n'emploie que des jetons du thème
 * (`--primary-hue`, `--secondary-hue`, `--accent-hue`, `--danger`, `--muted`).
 * Elles suivent donc le thème choisi dans le sélecteur de couleurs et le mode
 * sombre — ce qu'une image bitmap figée ne permettrait pas.
 */
import type { ComponentType, ReactNode, SVGProps } from "react";

/** Jetons de couleur du design system, utilisables dans un `fill` SVG. */
const C = {
  primary: "hsl(var(--primary-hue))",
  primarySoft: "hsl(var(--primary-hue) / 0.45)",
  secondary: "hsl(var(--secondary-hue))",
  accent: "hsl(var(--accent-hue))",
  danger: "hsl(var(--danger))",
  muted: "hsl(var(--muted))",
  onColor: "hsl(var(--surface))",
} as const;

export type AppIconProps = SVGProps<SVGSVGElement>;

function Base({ children, ...props }: AppIconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

/** Comptabilité — registre ouvert. */
export function AccountingIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <path
        d="M3.5 4.6A1.6 1.6 0 0 1 5.1 3H11v18H5.1a1.6 1.6 0 0 1-1.6-1.6z"
        fill={C.primary}
      />
      <path
        d="M13 3h5.9A1.6 1.6 0 0 1 20.5 4.6v14.8a1.6 1.6 0 0 1-1.6 1.6H13z"
        fill={C.primarySoft}
      />
      <rect x="5.4" y="6.2" width="3.4" height="3.4" rx="1" fill={C.secondary} />
      <rect x="5.4" y="11.4" width="3.4" height="3.4" rx="1" fill={C.accent} />
      <rect x="15.2" y="6.2" width="3.4" height="3.4" rx="1" fill={C.accent} />
      <rect x="15.2" y="11.4" width="3.4" height="3.4" rx="1" fill={C.secondary} />
    </Base>
  );
}

/** Dépenses — pièce justificative et calculatrice. */
export function ExpensesIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <path d="M4 3h9l4 4v10H4z" fill={C.accent} />
      <path d="M13 3l4 4h-4z" fill={C.accent} opacity="0.55" />
      <path
        d="M6.5 10.5h8M6.5 13h8M6.5 15.5h5"
        stroke={C.danger}
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <rect x="13" y="13.5" width="7.5" height="7.5" rx="1.4" fill={C.danger} />
      <rect x="14.6" y="15.1" width="4.3" height="1.7" rx="0.5" fill={C.accent} />
      <path
        d="M15.4 18.2h1M17.4 18.2h1M19.2 18.2h.4M15.4 19.6h1M17.4 19.6h1M19.2 19.6h.4"
        stroke={C.accent}
        strokeWidth="1"
        strokeLinecap="round"
      />
      <path
        d="M18.5 3v4.6M16.6 5.8l1.9 1.9 1.9-1.9"
        stroke={C.accent}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Base>
  );
}

/** Livraison — camion en mouvement. */
export function DeliveryIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <path
        d="M2.5 9.5h4M1.5 12h4M2.5 14.5h4"
        stroke={C.primary}
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M7 6.5h8.5v9H7z" fill={C.primary} />
      <path d="M10.5 6.5h2.4l1.4 3.4-2.6 2.1-2.6-2.1z" fill={C.muted} opacity="0.55" />
      <path d="M15.5 9h2.6l3 3.2v3.3h-5.6z" fill={C.primarySoft} />
      <path d="M17.4 10.2h1.9l1.5 1.7h-3.4z" fill={C.primary} opacity="0.7" />
      <circle cx="10" cy="17" r="2" fill={C.muted} />
      <circle cx="18" cy="17" r="2" fill={C.muted} />
      <circle cx="10" cy="17" r="0.8" fill={C.onColor} />
      <circle cx="18" cy="17" r="0.8" fill={C.onColor} />
    </Base>
  );
}

/** Paiements — carte bancaire remise en main. */
export function PaymentsIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <rect x="9" y="5" width="13" height="3" rx="1.4" fill={C.primary} />
      <rect x="9" y="8.6" width="13" height="8.4" rx="1.6" fill={C.primarySoft} />
      <rect x="16" y="12" width="4.4" height="2.2" rx="0.8" fill={C.primary} />
      <path
        d="M1.5 12.5h3.2l2.6-2.8 3.4 3.4-3.1 3.1H1.5z"
        fill={C.primary}
        opacity="0.75"
      />
      <path d="M5 16.2l3.6-3.6" stroke={C.primary} strokeWidth="1.5" strokeLinecap="round" />
    </Base>
  );
}

/** Ventes — chariot et encaissement. */
export function SalesIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <path d="M8.5 3h3.2l1.4 4.6H8.5z" fill={C.secondary} />
      <path d="M12 3h3.4l1.6 3-2.6 2.6-2.4-2.6z" fill={C.secondary} opacity="0.6" />
      <path d="M4.2 8.4h15l-1.6 7.2H6.4z" fill={C.accent} />
      <path
        d="M8.6 10.4v3.4M11.4 10.4v3.4M14.2 10.4v3.4"
        stroke={C.onColor}
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M3 6.4h1.6l1.2 9.2h11"
        stroke={C.danger}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="7.4" cy="19" r="1.6" fill={C.muted} />
      <circle cx="16.6" cy="19" r="1.6" fill={C.muted} />
    </Base>
  );
}

/** Stock — cartons et rayonnage. */
export function StockIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <rect x="2.5" y="4" width="10" height="9" rx="1.2" fill={C.accent} />
      <rect x="10.4" y="9" width="11" height="8" rx="1.2" fill={C.accent} opacity="0.6" />
      <path d="M7.5 4v4.6l1.8-1.2 1.8 1.2V4z" fill={C.danger} />
      <path d="M15.8 9v3.4l1.5-1 1.5 1V9z" fill={C.danger} opacity="0.75" />
      <rect x="1.5" y="19" width="21" height="2.4" rx="1.2" fill={C.primary} />
    </Base>
  );
}

/** Applications — lanceur (grille de quatre modules). */
export function ApplicationsIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <rect x="2.5" y="2.5" width="8.4" height="8.4" rx="1.4" fill={C.primary} />
      <rect x="13.1" y="2.5" width="8.4" height="8.4" rx="1.4" fill={C.primarySoft} />
      <rect x="2.5" y="13.1" width="8.4" height="8.4" rx="1.4" fill={C.primarySoft} />
      <rect x="13.1" y="13.1" width="8.4" height="8.4" rx="1.4" fill={C.primary} />
    </Base>
  );
}

/** Facturation — facture, calculatrice et montant. */
export function InvoicingIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <path d="M3.5 2.8h9.6l4 4v9.4H3.5z" fill={C.primary} />
      <path d="M13.1 2.8l4 4h-4z" fill={C.primarySoft} />
      <path
        d="M6 8.4h6M6 11h6M6 13.6h4"
        stroke={C.onColor}
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <rect x="12.6" y="13" width="8" height="8.2" rx="1.4" fill={C.danger} />
      <rect x="14.2" y="14.6" width="4.8" height="1.8" rx="0.5" fill={C.accent} />
      <path
        d="M15 17.8h1M17 17.8h1M19 17.8h.4M15 19.4h1M17 19.4h1M19 19.4h.4"
        stroke={C.accent}
        strokeWidth="1"
        strokeLinecap="round"
      />
      <circle cx="19.4" cy="9.4" r="3.4" fill={C.secondary} />
      <path
        d="M19.4 7.4v4M18.4 8.3h2M18.4 10.5h2"
        stroke={C.onColor}
        strokeWidth="1"
        strokeLinecap="round"
      />
    </Base>
  );
}

/** Reporting — histogramme et courbe de tendance. */
export function ReportingIcon(props: AppIconProps) {
  return (
    <Base {...props}>
      <rect x="2.5" y="13.6" width="4" height="7.4" rx="0.6" fill={C.secondary} opacity="0.45" />
      <rect x="7.6" y="10.6" width="4" height="10.4" rx="0.6" fill={C.secondary} opacity="0.65" />
      <rect x="12.7" y="7.6" width="4" height="13.4" rx="0.6" fill={C.secondary} opacity="0.85" />
      <rect x="17.8" y="4.6" width="4" height="16.4" rx="0.6" fill={C.secondary} />
      <path
        d="M3.4 11.6l4.4-2.6 4-1.6 4.2-2.8 3.6-1.8"
        stroke={C.primary}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="3.4" cy="11.6" r="1.3" fill={C.primary} />
      <circle cx="7.8" cy="9" r="1.3" fill={C.primary} />
      <circle cx="11.8" cy="7.4" r="1.3" fill={C.primary} />
      <path d="M19.6 2.4l2.6 1.6-2.6 1.6z" fill={C.primary} />
    </Base>
  );
}

/**
 * Correspondance entre la clé d'une tuile (`lib/module-registry`) et son icône.
 *
 * Les clés sont celles de `APP_TILES` : `finance` désigne la tuile
 * « Dépenses » et `dashboard` la tuile « Tableau de bord ».
 */
export const APP_ICONS: Record<string, ComponentType<AppIconProps>> = {
  dashboard: ApplicationsIcon,
  sales: SalesIcon,
  invoicing: InvoicingIcon,
  stock: StockIcon,
  delivery: DeliveryIcon,
  payments: PaymentsIcon,
  finance: ExpensesIcon,
  accounting: AccountingIcon,
  reporting: ReportingIcon,
};

