/**
 * Page de configuration initiale (premier lancement).
 *
 * Visible uniquement si la base est vierge (aucun compte) — le backend
 * verrouille l'endpoint dès qu'un utilisateur existe. Crée l'entreprise,
 * l'agence, les rôles et le compte administrateur, puis connecte
 * automatiquement l'administrateur (→ étape profil entreprise).
 */
"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2, Rocket } from "lucide-react";

import { useSetupAdmin, useSetupStatus } from "@/hooks/useSetup";
import { useLogin } from "@/hooks/useAuth";

const CURRENCIES = [
  { code: "XOF", label: "Franc CFA (XOF)" },
  { code: "EUR", label: "Euro (EUR)" },
  { code: "USD", label: "Dollar US (USD)" },
  { code: "NGN", label: "Naira (NGN)" },
];

const setupSchema = z
  .object({
    company_name: z.string().min(2, "Nom d'entreprise requis"),
    company_code: z
      .string()
      .min(2, "Code requis")
      .max(20)
      .regex(/^[A-Za-z0-9_-]+$/, "Lettres, chiffres et tirets uniquement"),
    currency_code: z.string().length(3),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    email: z.string().email("Email invalide"),
    password: z
      .string()
      .min(8, "8 caractères minimum")
      .regex(/[A-Z]/, "Ajoutez une majuscule")
      .regex(/[a-z]/, "Ajoutez une minuscule")
      .regex(/[0-9]/, "Ajoutez un chiffre"),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirm"],
  });

type SetupForm = z.infer<typeof setupSchema>;

const inputClass =
  "w-full rounded-md border border-gray-300 px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-blue-600";

export default function SetupPage() {
  const { data: status, isLoading } = useSetupStatus();
  const setupAdmin = useSetupAdmin();
  const login = useLogin();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SetupForm>({
    resolver: zodResolver(setupSchema),
    defaultValues: { currency_code: "XOF" },
  });

  // Instance déjà configurée → retour à la connexion
  useEffect(() => {
    if (status && !status.needs_admin) {
      window.location.href = "/login";
    }
  }, [status]);

  const onSubmit = async (data: SetupForm) => {
    setError(null);
    try {
      await setupAdmin.mutateAsync({
        company_name: data.company_name,
        company_code: data.company_code,
        currency_code: data.currency_code,
        email: data.email,
        password: data.password,
        first_name: data.first_name || "",
        last_name: data.last_name || "",
      });
      // Connexion automatique → le hook useLogin redirige vers
      // /setup/company (profil entreprise) puis le tableau de bord.
      await login.mutateAsync({
        email: data.email,
        password: data.password,
        company_code: data.company_code.toUpperCase(),
      });
      window.location.href = "/setup/company";
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Erreur lors de la configuration initiale",
      );
    }
  };

  if (isLoading || (status && !status.needs_admin)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#0a2a6b] via-[#0d3a8f] to-[#061a45] p-6">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#0a2a6b]">
            <Rocket className="h-7 w-7 text-amber-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">
            Bienvenue — configuration initiale
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Créez votre entreprise et le compte administrateur principal.
          </p>
        </div>

        {error && (
          <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Entreprise
            </legend>
            <div>
              <input
                placeholder="Nom de l'entreprise *"
                className={inputClass}
                {...register("company_name")}
              />
              {errors.company_name && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.company_name.message}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <input
                  placeholder="Code * (ex. GEA)"
                  className={inputClass}
                  {...register("company_code")}
                />
                {errors.company_code && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.company_code.message}
                  </p>
                )}
              </div>
              <select className={inputClass} {...register("currency_code")}>
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Compte administrateur
            </legend>
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="Prénom"
                className={inputClass}
                {...register("first_name")}
              />
              <input
                placeholder="Nom"
                className={inputClass}
                {...register("last_name")}
              />
            </div>
            <div>
              <input
                type="email"
                placeholder="Email administrateur *"
                className={inputClass}
                {...register("email")}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Mot de passe * (8+ caractères, Aa1)"
                className={inputClass}
                {...register("password")}
              />
              {showPassword ? (
                <EyeOff
                  className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 cursor-pointer text-gray-500"
                  onClick={() => setShowPassword(false)}
                />
              ) : (
                <Eye
                  className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 cursor-pointer text-gray-500"
                  onClick={() => setShowPassword(true)}
                />
              )}
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>
            <div>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Confirmation du mot de passe *"
                className={inputClass}
                {...register("confirm")}
              />
              {errors.confirm && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.confirm.message}
                </p>
              )}
            </div>
          </fieldset>

          <button
            type="submit"
            disabled={isSubmitting || setupAdmin.isPending || login.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-[#0a2a6b] px-4 py-3 text-base font-semibold text-white transition-colors hover:bg-[#0d3a8f] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {(isSubmitting || setupAdmin.isPending || login.isPending) && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Créer l&apos;entreprise et se connecter
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          Cette page n&apos;est disponible qu&apos;au premier lancement.
        </p>
      </div>
    </div>
  );
}
