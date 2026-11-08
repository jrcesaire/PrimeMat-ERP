/**
 * Configuration initiale — étape 2 : profil de l'entreprise.
 *
 * Accessible après la création du compte administrateur. Les mentions
 * obligatoires — nom, téléphone, devise, adresse, ville, pays — figurent sur
 * les devis et les factures : sans elles, le serveur refuse la création d'un
 * document (409) et l'utilisateur est ramené ici.
 *
 * L'étape peut être reportée (« Plus tard ») : la connexion ne la reproposera
 * plus, mais l'écran revient à la première tentative de création d'un devis ou
 * d'une facture. Les informations fiscales, le logo et les CGV ne sont jamais
 * exigés — le logo est remplacé par une miniature si l'utilisateur n'en
 * fournit pas.
 */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AxiosError } from "axios";
import {
  Building2,
  CheckCircle2,
  ImagePlus,
  Loader2,
  TriangleAlert,
  X,
} from "lucide-react";

import { useCurrentUser } from "@/hooks/useAuth";
import {
  useSetupCompany,
  useSetupStatus,
  useSkipSetupCompany,
} from "@/hooks/useSetup";
import {
  COUNTRIES,
  CURRENCIES,
  currencyLabel,
} from "@/lib/countries-currencies";

interface CompanyForm {
  name: string;
  phone: string;
  currency_code: string;
  street: string;
  city: string;
  country: string;
  email: string;
  website: string;
  establishment: string;
  slogan: string;
  ncc: string;
  rccm: string;
  share_capital: string;
  cgv: string;
}

/**
 * Mentions obligatoires : sans elles, aucun devis ni facture n'est créé.
 *
 * Locale volontairement non exportée : un module de page Next.js ne peut
 * exporter que sa page (sinon `next build` refuse avec `checkFields`).
 */
const REQUIRED_FIELDS: { key: keyof CompanyForm; label: string }[] = [
  { key: "name", label: "Nom de l'entreprise" },
  { key: "phone", label: "N° de téléphone" },
  { key: "currency_code", label: "Devise" },
  { key: "street", label: "Adresse" },
  { key: "city", label: "Ville" },
  { key: "country", label: "Pays" },
];

const EMPTY_FORM: CompanyForm = {
  name: "",
  phone: "",
  currency_code: "XOF",
  street: "",
  city: "",
  country: "Côte d'Ivoire",
  email: "",
  website: "",
  establishment: "",
  slogan: "",
  ncc: "",
  rccm: "",
  share_capital: "",
  cgv: "",
};

const inputClass =
  "w-full rounded-md border border-gray-300 bg-surface px-3 py-2.5 text-sm text-ink outline-none transition-colors placeholder:text-ghost focus:border-blue-600";
const labelClass = "mb-1 block text-xs font-medium text-muted";
const errorClass = "mt-1 text-xs text-danger";

/** Le serveur plafonne la data URL du logo à 800 000 caractères. */
const MAX_LOGO_CHARS = 800_000;

/** Lit un fichier image en data URL. */
function readLogo(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Lecture du fichier impossible"));
    reader.readAsDataURL(file);
  });
}

/** Initiales servant de miniature quand aucun logo n'est fourni (locale). */
function monogram(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export default function SetupCompanyPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: status, isLoading: statusLoading } = useSetupStatus();
  const setupCompany = useSetupCompany();
  const skipSetup = useSkipSetupCompany();

  const [form, setForm] = useState<CompanyForm>(EMPTY_FORM);
  const [logo, setLogo] = useState<string | null>(null);
  const [errors, setErrors] = useState<
    Partial<Record<keyof CompanyForm, string>>
  >({});
  const [notice, setNotice] = useState<{
    kind: "ok" | "warn";
    text: string;
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const hydrated = useRef(false);

  // Non connecté → retour au login (le token vient d'être posé par /setup)
  useEffect(() => {
    if (!userLoading && !user) {
      window.location.href = "/login";
    }
  }, [user, userLoading]);

  // Cet écran n'est quitté que lorsque plus rien ne manque. Se fier au seul
  // drapeau « needs_company » renverrait au tableau de bord un utilisateur qui
  // vient d'y être ramené par le refus de création d'un document (409).
  useEffect(() => {
    if (status?.company_complete) {
      window.location.href = "/";
    }
  }, [status?.company_complete]);

  // Pré-remplissage : le nom et la devise viennent de l'étape précédente.
  useEffect(() => {
    if (hydrated.current || !status) return;
    hydrated.current = true;
    setForm((f) => ({
      ...f,
      name: f.name || status.company_name || "",
      currency_code: f.currency_code || status.currency_code || "XOF",
    }));
  }, [status]);

  const initials = useMemo(() => monogram(form.name), [form.name]);

  const update = (key: keyof CompanyForm, value: string) => {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => (e[key] ? { ...e, [key]: undefined } : e));
  };

  const onPickLogo = async (file: File | undefined) => {
    if (!file) return;
    try {
      const dataUrl = await readLogo(file);
      if (dataUrl.length > MAX_LOGO_CHARS) {
        setNotice({
          kind: "warn",
          text: "Ce logo est trop volumineux (600 Ko maximum). Choisissez une image plus légère.",
        });
        return;
      }
      setLogo(dataUrl);
      setNotice(null);
    } catch {
      setNotice({ kind: "warn", text: "Ce fichier n'a pas pu être lu." });
    }
  };

  const onSubmit = async () => {
    // Les mentions obligatoires conditionnent la création des documents :
    // enregistrer un profil incomplet ne débloquerait rien.
    const missing = REQUIRED_FIELDS.filter((f) => !form[f.key].trim());
    if (missing.length > 0) {
      setErrors(
        Object.fromEntries(
          missing.map((f) => [f.key, "Information obligatoire"]),
        ),
      );
      setNotice({
        kind: "warn",
        text: `Il manque : ${missing.map((f) => f.label).join(", ")}. Le logo et les informations fiscales, eux, ne sont pas exigés.`,
      });
      return;
    }

    setErrors({});
    setNotice(null);
    try {
      const result = await setupCompany.mutateAsync({
        ...form,
        logo: logo ?? undefined,
      });
      if (result.company_complete) {
        window.location.href = "/";
        return;
      }
      setNotice({
        kind: "warn",
        text: `Enregistré, mais il manque encore : ${result.missing_labels.join(", ")}.`,
      });
    } catch (error) {
      const detail =
        error instanceof AxiosError ? error.response?.data?.detail : undefined;
      setNotice({
        kind: "warn",
        text:
          typeof detail === "string"
            ? detail
            : "L'enregistrement a échoué. Réessayez.",
      });
    }
  };

  const onSkip = async () => {
    await skipSetup.mutateAsync();
    window.location.href = "/";
  };

  const busy = setupCompany.isPending || skipSetup.isPending;

  if (userLoading || statusLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-start justify-center bg-gradient-to-br from-[#0a2a6b] via-[#0d3a8f] to-[#061a45] p-6">
      <div className="my-8 w-full max-w-2xl rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#0a2a6b]">
            <Building2 className="h-7 w-7 text-amber-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">
            Informations de l&apos;entreprise
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Elles figurent sur vos devis et vos factures. Les champs suivis
            d&apos;une étoile sont obligatoires ; le reste est recommandé et
            modifiable plus tard dans les Paramètres.
          </p>
        </div>

        {notice && (
          <div
            className={`mb-4 flex gap-2 rounded-md border px-3 py-2.5 text-sm ${
              notice.kind === "ok"
                ? "border-green-200 bg-green-50 text-green-800"
                : "border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            {notice.kind === "ok" ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <span>{notice.text}</span>
          </div>
        )}

        {/* Logo — une miniature d'initiales prend le relais à défaut d'image. */}
        <div className="mb-5 flex items-center gap-4 rounded-lg border border-gray-200 p-4">
          {logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={logo}
              alt="Logo de l'entreprise"
              className="h-16 max-w-[9rem] object-contain"
            />
          ) : (
            <div
              aria-hidden
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-[#0a2a6b] text-xl font-bold text-amber-400"
            >
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-800">
              {logo ? "Logo de l'entreprise" : "Miniature de substitution"}
            </p>
            <p className="mt-0.5 text-xs text-gray-500">
              {logo
                ? "Il apparaîtra en tête de vos documents."
                : "Le logo est facultatif : à défaut, ces initiales s'affichent sur les documents."}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                <ImagePlus className="h-3.5 w-3.5" />
                {logo ? "Changer le logo" : "Ajouter un logo"}
              </button>
              {logo && (
                <button
                  type="button"
                  onClick={() => setLogo(null)}
                  className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-50"
                >
                  <X className="h-3.5 w-3.5" />
                  Retirer
                </button>
              )}
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml"
            className="hidden"
            onChange={(e) => void onPickLogo(e.target.files?.[0])}
          />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void onSubmit();
          }}
          className="space-y-5"
        >
          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Informations obligatoires
            </legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Nom de l&apos;entreprise *</label>
                <input
                  className={inputClass}
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                />
                {errors.name && <p className={errorClass}>{errors.name}</p>}
              </div>
              <div>
                <label className={labelClass}>N° de téléphone *</label>
                <input
                  className={inputClass}
                  placeholder="+225 27 22 00 00 00"
                  value={form.phone}
                  onChange={(e) => update("phone", e.target.value)}
                />
                {errors.phone && <p className={errorClass}>{errors.phone}</p>}
              </div>
            </div>
            <div>
              <label className={labelClass}>Devise *</label>
              <select
                className={inputClass}
                value={form.currency_code}
                onChange={(e) => update("currency_code", e.target.value)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {currencyLabel(c.code)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Adresse *</label>
              <input
                className={inputClass}
                placeholder="Rue, quartier, lot"
                value={form.street}
                onChange={(e) => update("street", e.target.value)}
              />
              {errors.street && <p className={errorClass}>{errors.street}</p>}
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Ville *</label>
                <input
                  className={inputClass}
                  value={form.city}
                  onChange={(e) => update("city", e.target.value)}
                />
                {errors.city && <p className={errorClass}>{errors.city}</p>}
              </div>
              <div>
                <label className={labelClass}>Pays *</label>
                <input
                  className={inputClass}
                  list="setup-countries"
                  value={form.country}
                  onChange={(e) => update("country", e.target.value)}
                />
                <datalist id="setup-countries">
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.name} />
                  ))}
                </datalist>
                {errors.country && (
                  <p className={errorClass}>{errors.country}</p>
                )}
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Coordonnées et identité
            </legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Établissement</label>
                <input
                  className={inputClass}
                  placeholder="Siège, Agence Sud…"
                  value={form.establishment}
                  onChange={(e) => update("establishment", e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Slogan</label>
                <input
                  className={inputClass}
                  value={form.slogan}
                  onChange={(e) => update("slogan", e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Email</label>
                <input
                  type="email"
                  className={inputClass}
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Site web</label>
                <input
                  className={inputClass}
                  value={form.website}
                  onChange={(e) => update("website", e.target.value)}
                />
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Informations fiscales — recommandées
            </legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label className={labelClass}>NCC (n° contribuable)</label>
                <input
                  className={inputClass}
                  value={form.ncc}
                  onChange={(e) => update("ncc", e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>RCCM</label>
                <input
                  className={inputClass}
                  value={form.rccm}
                  onChange={(e) => update("rccm", e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Capital social</label>
                <input
                  className={inputClass}
                  value={form.share_capital}
                  onChange={(e) => update("share_capital", e.target.value)}
                />
              </div>
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-gray-500">
              Conditions générales de vente — facultatives
            </legend>
            <p className="text-xs text-gray-500">
              Ce texte s&apos;affiche en fin de devis et de facture.
            </p>
            <textarea
              className={`${inputClass} min-h-[6rem]`}
              placeholder="Ex. Les marchandises vendues ne sont ni reprises ni échangées."
              value={form.cgv}
              onChange={(e) => update("cgv", e.target.value)}
            />
          </fieldset>

          <div className="flex flex-col gap-3 sm:flex-row-reverse sm:items-center">
            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-[#0a2a6b] px-4 py-3 text-base font-semibold text-white transition-colors hover:bg-[#0d3a8f] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {setupCompany.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              Enregistrer et continuer
            </button>
            <button
              type="button"
              onClick={() => void onSkip()}
              disabled={busy}
              className="w-full rounded-full border border-gray-300 px-4 py-3 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {skipSetup.isPending ? "…" : "Plus tard"}
            </button>
          </div>
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          Vous pouvez reporter cette étape. Elle reviendra à la première
          création d&apos;un devis ou d&apos;une facture, dont ces mentions sont
          indissociables.
        </p>
      </div>
    </div>
  );
}
