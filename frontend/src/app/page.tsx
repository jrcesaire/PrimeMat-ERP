/**
 * Accueil — lanceur d’applications (grille des modules actifs).
 * Le tableau de bord détaillé reste accessible via la tuile dédiée.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth/auth";
import { AppLauncher } from "@/components/dashboard/AppLauncher";
import { Header } from "@/components/layout/header";
import { useCurrentCompany } from "@/hooks/useAuth";

export default function HomePage() {
  const router = useRouter();
  const { data: company } = useCurrentCompany();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
    }
  }, [router]);

  if (!isAuthenticated()) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Applications" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        {company?.logo ? (
          <div className="mb-6 flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={company.logo}
              alt={"Logo"}
              className="h-12 w-12 rounded-lg bg-white object-contain p-1 shadow-sm"
            />
            <div>
              <h1 className="text-xl font-bold text-gray-900">{company.name}</h1>
              <p className="text-sm text-gray-500">Bienvenue — choisissez une application</p>
            </div>
          </div>
        ) : (
          <div className="mb-6">
            <h1 className="text-xl font-bold text-gray-900">Applications</h1>
            <p className="text-sm text-gray-500">Choisissez une application</p>
          </div>
        )}
        <AppLauncher />
      </main>
    </div>
  );
}
