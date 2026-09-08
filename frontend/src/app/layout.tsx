/**
 * Layout racine de l'application.
 *
 * Enveloppe toutes les pages avec :
 * - les providers (React Query, Theme)
 * - les styles globaux (Tailwind)
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

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
    <html lang="fr">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
