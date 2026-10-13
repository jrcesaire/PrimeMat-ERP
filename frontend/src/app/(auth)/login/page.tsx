/**
 * Page de connexion — design inspiré de Kuzma02/Login-Page-In-React :
 * deux panneaux (visuel de marque à gauche, formulaire à droite),
 * champs à bordure basse, boutons « pill », police Poppins.
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Loader2 } from "lucide-react";

import { useLogin } from "@/hooks/useAuth";
import { useSetupStatus } from "@/hooks/useSetup";

const loginSchema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
  company_code: z.string().optional(),
});

type LoginForm = z.infer<typeof loginSchema>;

/** Monogramme de marque (remplace le logo importé du repo). */
function BrandLogo({ size = 56 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-label="Logo GEA"
      role="img"
    >
      <circle cx="32" cy="32" r="30" fill="#0a2a6b" />
      <circle cx="32" cy="32" r="26" fill="none" stroke="#f59e0b" strokeWidth="2" />
      <text
        x="32"
        y="40"
        textAnchor="middle"
        fill="#ffffff"
        fontSize="20"
        fontWeight="700"
        fontFamily="Poppins, sans-serif"
      >
        GEA
      </text>
    </svg>
  );
}

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Premier lancement (base vierge) → wizard de configuration initiale
  const { data: setupStatus } = useSetupStatus();
  useEffect(() => {
    if (setupStatus?.needs_admin) {
      router.replace("/setup");
    }
  }, [setupStatus, router]);

  const {
    register,
    handleSubmit,
    resetField,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useLogin();

  const onSubmit = async (data: LoginForm) => {
    try {
      setError(null);
      await loginMutation.mutateAsync(data);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Identifiants incorrects ou serveur injoignable",
      );
      // Vide les champs sensibles après une erreur
      resetField("password");
      resetField("company_code");
    }
  };

  const inputClass =
    "w-full rounded-none border-0 border-b border-gray-800 bg-transparent px-1 py-4 text-base outline-none transition-colors placeholder:text-gray-500 focus:border-blue-600";

  return (
    <div className="flex min-h-screen">
      {/* ------- Panneau gauche : identité visuelle ------- */}
      <div className="relative hidden flex-1 items-center justify-center overflow-hidden bg-gradient-to-br from-[#0a2a6b] via-[#0d3a8f] to-[#061a45] lg:flex">
        <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/5" />
        <div className="absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-white/5" />
        <div className="absolute left-1/4 top-1/3 h-24 w-24 rounded-full border border-white/10" />

        <div className="relative z-10 max-w-md px-10 text-center text-white">
          <div className="mb-8 flex justify-center">
            <BrandLogo size={96} />
          </div>
          <h1 className="text-3xl font-bold leading-snug">
            Groupe Entreprise AKA
          </h1>
          <p className="mt-3 text-lg font-light italic text-amber-400">
            Construisez l&apos;esprit tranquille !
          </p>
          <p className="mt-8 text-sm leading-relaxed text-white/70">
            Gestion complète de vos matériaux de construction : ventes,
            stock, facturation, livraison et point de vente — le tout
            réuni dans une seule plateforme.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3 text-xs text-white/50">
            {["Ventes", "Stock", "Facturation", "Livraison"].map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-white/20 px-4 py-1.5"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ------- Panneau droit : formulaire ------- */}
      <div className="flex flex-1 items-stretch justify-center">
        <div className="flex h-full w-[85%] max-w-lg flex-col justify-center py-10">
          <div className="mb-10 flex justify-center">
            <BrandLogo size={56} />
          </div>

          <div className="text-center">
            <h2 className="text-4xl font-semibold text-gray-900">
              Bon retour !
            </h2>
            <p className="mt-2 mb-10 text-lg text-gray-500">
              Veuillez saisir vos informations
            </p>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col">
            <input
              type="email"
              placeholder="Email"
              className={inputClass}
              aria-invalid={errors.email ? "true" : "false"}
              {...register("email")}
            />
            {errors.email && (
              <p className="mb-2 mt-1 text-left text-xs text-red-600">
                {errors.email.message}
              </p>
            )}

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Mot de passe"
                className={inputClass}
                aria-invalid={errors.password ? "true" : "false"}
                {...register("password")}
              />
              {showPassword ? (
                <EyeOff
                  className="absolute bottom-4 right-2 h-5 w-5 cursor-pointer text-gray-700"
                  onClick={() => setShowPassword(!showPassword)}
                />
              ) : (
                <Eye
                  className="absolute bottom-4 right-2 h-5 w-5 cursor-pointer text-gray-700"
                  onClick={() => setShowPassword(!showPassword)}
                />
              )}
            </div>
            {errors.password && (
              <p className="mb-2 mt-1 text-left text-xs text-red-600">
                {errors.password.message}
              </p>
            )}

            <input
              type="text"
              placeholder="Code entreprise (optionnel)"
              className={inputClass}
              {...register("company_code")}
            />

            <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  id="remember-checkbox"
                  className="h-3.5 w-3.5 cursor-pointer accent-blue-600"
                />
                <label
                  htmlFor="remember-checkbox"
                  className="cursor-pointer text-[13px] font-medium text-gray-800"
                >
                  Se souvenir de moi pendant 30 jours
                </label>
              </div>
              <a
                href="#"
                title="Contactez votre administrateur"
                className="text-[13px] text-gray-800 hover:underline"
              >
                Mot de passe oublié ?
              </a>
            </div>

            <div className="mt-10 flex flex-col gap-2.5">
              <button
                type="submit"
                disabled={isSubmitting || loginMutation.isPending}
                className="w-full cursor-pointer rounded-full border-[3px] border-black bg-black px-4 py-4 text-base font-semibold text-white transition-colors hover:border-gray-700 hover:bg-white hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting || loginMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                    Connexion...
                  </>
                ) : (
                  "Se connecter"
                )}
              </button>
            </div>
          </form>

          <p className="pb-10 pt-10 text-center text-[15px] text-gray-700">
            Pas encore de compte ?{" "}
            <a
              href="#"
              title="Contactez l'administrateur de votre entreprise"
              className="font-semibold text-gray-900 hover:underline"
            >
              Contactez votre administrateur
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
