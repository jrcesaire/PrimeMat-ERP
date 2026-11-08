/**
 * Accueil — lanceur d’applications (grille des modules actifs).
 *
 * L'écran est **calé sur la hauteur de la fenêtre** : en-tête, identité et
 * bandeaux sont fixes, la grille d'applications occupe la place restante et
 * défile seule si elle déborde — la page, elle, ne défile jamais.
 * Le tableau de bord détaillé reste accessible via la tuile dédiée.
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth/auth";
import { AppLauncher } from "@/components/dashboard/AppLauncher";
import { Header } from "@/components/layout/header";
import { useCurrentCompany } from "@/hooks/useAuth";

export default function HomePage() {
  const router = useRouter();
  const { data: company } = useCurrentCompany();
  // Attend le montage client avant de lire localStorage : le serveur et le
  // premier rendu client produisent le même HTML (pas de mismatch).
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && !isAuthenticated()) {
      router.push("/login");
    }
  }, [router, mounted]);

  if (!mounted || !isAuthenticated()) return null;

  return (
    <div className="flex h-screen flex-col bg-canvas">
      <Header title="Applications" showCompany={false} />
      {/* `min-h-0` autorise la grille à se comprimer ; `overflow-hidden` garantit
          que seul le lanceur défile, jamais la page. */}
      <main className="mx-auto flex min-h-0 w-full max-w-[1212px] flex-1 flex-col gap-4 overflow-hidden px-6 py-5">
        {/* Identité de l'entreprise — deux lignes maximum, hauteur fixe. */}
        {company?.logo ? (
          <div className="flex shrink-0 items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={company.logo}
              alt={`Logo ${company.name}`}
              className="h-10 w-10 shrink-0 rounded-[9px] object-contain"
            />
            <div className="min-w-0">
              <h1 className="truncate text-[17px] font-bold tracking-tight text-ink">
                {company.name}
              </h1>
              <p className="truncate text-[12px] text-muted">
                Bienvenue — choisissez une application
              </p>
            </div>
          </div>
        ) : (
          <div className="shrink-0">
            <h1 className="text-[17px] font-bold tracking-tight text-ink">
              Applications
            </h1>
            <p className="text-[12px] text-muted">Choisissez une application</p>
          </div>
        )}
        <AppLauncher />
      </main>
    </div>
  );
}
