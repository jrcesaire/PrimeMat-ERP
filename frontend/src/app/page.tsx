/**
 * Page d'accueil — redirige vers le dashboard ou la page de login.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.push("/dashboard");
    } else {
      router.push("/login");
    }
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold">ERP Matériaux de Construction</h1>
        <p className="mt-2 text-gray-600">Chargement...</p>
      </div>
    </div>
  );
}
