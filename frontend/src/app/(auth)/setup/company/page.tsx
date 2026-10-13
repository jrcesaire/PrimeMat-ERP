/**
 * Configuration initiale — étape 2 : profil de l'entreprise.
 *
 * Accessible uniquement au super-administrateur après la création du
 * compte (premier lancement) : complète le profil affiché sur les
 * documents (téléphone, adresse, NCC, RCCM...). Une fois validée,
 * l'entrée `/setup` n'est plus proposée.
 */
"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Building2, Loader2 } from "lucide-react";

import { useCurrentUser } from "@/hooks/useAuth";
import { useSetupCompany, useSetupStatus } from "@/hooks/useSetup";

type CompanyForm = {
  establishment: string;
  slogan: string;
  phone: string;
  email: string;
  website: string;
  address_line1: string;
  address_city: string;
  ncc: string;
  rccm: string;
  share_capital: string;
};

const inputClass =
  "w-full rounded-md border border-gray-300 px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-blue-600";

export default function SetupCompanyPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: status, isLoading: statusLoading } = useSetupStatus();
  const setupCompany = useSetupCompany();
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<CompanyForm>();

  // Non connecté → retour au login (le token vient d'être posé par /setup)
  useEffect(() => {
    if (!userLoading && !user) {
      window.location.href = "/login";
    }
  }, [user, userLoading]);

  // Déjà configurée → tableau de bord
  useEffect(() => {
    if (status && !status.needs_company) {
      window.location.href = "/";
    }
  }, [status]);

  if (userLoading || statusLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const onSubmit = async (data: CompanyForm) => {
    // Nettoie les champs vides
    const payload = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v && v.trim() !== ""),
    );
    await setupCompany.mutateAsync(payload);
    window.location.href = "/";
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#0a2a6b] via-[#0d3a8f] to-[#061a45] p-6">
      <div className="w-full max-w-xl rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#0a2a6b]">
            <Building2 className="h-7 w-7 text-amber-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">
            Profil de l&apos;entreprise
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Ces informations apparaissent sur les devis et factures —
            tout est modifiable plus tard dans les Paramètres.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Établissement (ex. Siège, Agence Sud)"
              className={inputClass}
              {...register("establishment")}
            />
            <input
              placeholder="Slogan"
              className={inputClass}
              {...register("slogan")}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Téléphone"
              className={inputClass}
              {...register("phone")}
            />
            <input
              type="email"
              placeholder="Email"
              className={inputClass}
              {...register("email")}
            />
          </div>
          <input
            placeholder="Site web"
            className={inputClass}
            {...register("website")}
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Adresse"
              className={inputClass}
              {...register("address_line1")}
            />
            <input
              placeholder="Ville"
              className={inputClass}
              {...register("address_city")}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <input
              placeholder="NCC (n° fiscal)"
              className={inputClass}
              {...register("ncc")}
            />
            <input
              placeholder="RCCM"
              className={inputClass}
              {...register("rccm")}
            />
            <input
              placeholder="Capital social"
              className={inputClass}
              {...register("share_capital")}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || setupCompany.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-[#0a2a6b] px-4 py-3 text-base font-semibold text-white transition-colors hover:bg-[#0d3a8f] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {(isSubmitting || setupCompany.isPending) && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Terminer la configuration
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          Connecté en tant qu&apos;administrateur — étape finale du premier
          lancement.
        </p>
      </div>
    </div>
  );
}
