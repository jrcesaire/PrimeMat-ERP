/**
 * Layout racine de l'application.
 *
 * Enveloppe toutes les pages avec :
 * - les providers (React Query, Theme)
 * - les styles globaux (Tailwind)
 */
import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import "./globals.css";

import { Providers } from "./providers";

// Police globale de l'application. La variable CSS alimente `font-sans`
// (cf. `tailwind.config.js`), donc tout l'ERP en hérite.
const openSans = Open_Sans({
  subsets: ["latin"],
  variable: "--font-open-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ERP Matériaux de Construction",
  description: "ERP modulaire pour la gestion, le négoce et la distribution de matériaux de construction",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script
          id="theme-init"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var m=localStorage.getItem("erp-theme-mode");if(m==="dark"||(!m&&window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}}catch(e){}})()`,
          }}
        />
      </head>
      <body className={`${openSans.variable} font-sans`} suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
