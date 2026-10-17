/**
 * Wizard « Configuration société » — assistant comptable OHADA (Phase 1 PRD).
 *
 * Cinq étapes inspirées de l'assistant Sage, adaptées au SYSCOHADA :
 *  1. Identification de la société (raison sociale, forme juridique, pays)
 *  2. Monnaie de tenue de compte (devise + taux de change + TVA)
 *  3. Coordonnées de l'entreprise (activité, adresse, fiscalité)
 *  4. Exercice comptable (dates d'ouverture)
 *  5. Reprise des éléments comptables (plan standard OHADA + journaux)
 *
 * Les étapes 1-3 reposent sur les endpoints Société / Paramètres du core,
 * les étapes 4-5 sur les endpoints OHADA et le seed du plan comptable.
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Building2,
  CalendarRange,
  Coins,
  ListChecks,
  Loader2,
  MapPin,
  Settings2,
  TriangleAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useCurrentCompany, useCurrentUser } from "@/hooks/useAuth";
import {
  useOHADAConstraints,
  useCurrentFiscalYear,
  useCreateFiscalYear,
  useSeedOhadaPlan,
  useUpsertExchangeRate,
  useUpsertOHADAParameter,
  useUpsertSetting,
  useSetting,
  type SeedResult,
} from "@/hooks/useOHADA";
import { apiClient } from "@/lib/api/client";

// --- Constantes du wizard ---
const STEPS = [
  { label: "Identification", icon: Building2 },
  { label: "Monnaie", icon: Coins },
  { label: "Coordonnées", icon: MapPin },
  { label: "Exercice", icon: CalendarRange },
  { label: "Plan comptable", icon: ListChecks },
] as const;

interface OhadaCountry {
  code: string;
  name: string;
  currency: string;
}

/** Les 17 États membres OHADA avec leur devise courante. */
const OHADA_COUNTRIES: OhadaCountry[] = [
  { code: "BF", name: "Burkina Faso", currency: "XOF" },
  { code: "BJ", name: "Bénin", currency: "XOF" },
  { code: "CI", name: "Côte d'Ivoire", currency: "XOF" },
  { code: "SN", name: "Sénégal", currency: "XOF" },
  { code: "TG", name: "Togo", currency: "XOF" },
  { code: "ML", name: "Mali", currency: "XOF" },
  { code: "NE", name: "Niger", currency: "XOF" },
  { code: "GW", name: "Guinée-Bissau", currency: "XOF" },
  { code: "CM", name: "Cameroun", currency: "XAF" },
  { code: "GA", name: "Gabon", currency: "XAF" },
  { code: "CG", name: "Congo", currency: "XAF" },
  { code: "TD", name: "Tchad", currency: "XAF" },
  { code: "CF", name: "Centrafrique", currency: "XAF" },
  { code: "GQ", name: "Guinée équatoriale", currency: "XAF" },
  { code: "GN", name: "Guinée", currency: "GNF" },
  { code: "MR", name: "Mauritanie", currency: "MRU" },
  { code: "CD", name: "RD Congo", currency: "USD" },
];

const LEGAL_FORMS = [
  "SARL",
  "SAS",
  "SA",
  "SARLU",
  "SNC",
  "GIE",
  "EI",
  "Autre",
];

const inputClass =
  "w-full rounded-md border border-gray-300 px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-blue-600";

const labelClass =
  "mb-1 block text-sm font-medium text-gray-700";

interface CompanyInfo {
  id: number;
  name: string;
  code: string;
  currency_code: string;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  address?: Record<string, string>;
  ncc?: string | null;
  rccm?: string | null;
  share_capital?: string | null;
  tax_country?: string | null;
}

export default function AccountingSetupPage() {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: company } = useCurrentCompany() as { data: CompanyInfo | undefined };

  const settingLegalForm = useSetting("accounting_legal_form");
  const settingActivity = useSetting("accounting_naf_activity");
  const currentFiscalYear = useCurrentFiscalYear();
  const constraints = useOHADAConstraints();

  const upsertSetting = useUpsertSetting();
  const upsertParameter = useUpsertOHADAParameter();
  const upsertRate = useUpsertExchangeRate();
  const createFiscalYear = useCreateFiscalYear();
  const seedPlan = useSeedOhadaPlan();

  const [step, setStep] = useState(0);
  const [hydrated, setHydrated] = useState(false);
  const [notice, setNotice] = useState<{ kind: "ok" | "warn"; text: string } | null>(
    null,
  );
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);

  // Étape 1 — Identification
  const [legalName, setLegalName] = useState("");
  const [legalForm, setLegalForm] = useState("SARL");
  const [countryCode, setCountryCode] = useState("BF");

  // Étape 2 — Monnaie
  const [eurRate, setEurRate] = useState("0.00152");
  const [usdRate, setUsdRate] = useState("0.00163");
  const [vatRate, setVatRate] = useState("18");

  // Étape 3 — Coordonnées
  const [activity, setActivity] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [addressLine, setAddressLine] = useState("");
  const [city, setCity] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [ncc, setNcc] = useState("");
  const [rccm, setRccm] = useState("");
  const [capital, setCapital] = useState("");

  // Étape 4 — Exercice
  const currentYear = new Date().getFullYear();
  const [fyName, setFyName] = useState(`Exercice ${currentYear}`);
  const [fyStart, setFyStart] = useState(`${currentYear}-01-01`);
  const [fyEnd, setFyEnd] = useState(`${currentYear}-12-31`);

  const selectedCountry = useMemo(
    () => OHADA_COUNTRIES.find((c) => c.code === countryCode) ?? OHADA_COUNTRIES[0],
    [countryCode],
  );

  // Pré-remplissage depuis la société + les paramètres enregistrés
  useEffect(() => {
    if (hydrated) return;
    const companyReady = company !== undefined;
    const settingsReady =
      settingLegalForm.isSuccess && settingActivity.isSuccess;
    const fyReady = currentFiscalYear.isSuccess || currentFiscalYear.isError;
    if (!companyReady || !settingsReady || !fyReady) return;

    if (company) {
      setLegalName((prev) => prev || company.name);
      setPhone((prev) => prev || company.phone || "");
      setEmail((prev) => prev || company.email || "");
      setNcc((prev) => prev || company.ncc || "");
      setRccm((prev) => prev || company.rccm || "");
      setCapital((prev) => prev || company.share_capital || "");
      const addr = company.address ?? {};
      setAddressLine((prev) => prev || addr.line1 || addr.address || "");
      setCity((prev) => prev || addr.city || "");
      setPostalCode((prev) => prev || addr.postal_code || "");
      if (company.tax_country) {
        const found = OHADA_COUNTRIES.find(
          (c) => c.code === company.tax_country?.toUpperCase(),
        );
        if (found) setCountryCode(found.code);
      }
    }
    if (settingLegalForm.data?.value) {
      setLegalForm(settingLegalForm.data.value);
    }
    if (settingActivity.data?.value) {
      setActivity(settingActivity.data.value);
    }
    if (currentFiscalYear.data) {
      setFyName(currentFiscalYear.data.name);
      setFyStart(currentFiscalYear.data.start_date);
      setFyEnd(currentFiscalYear.data.end_date);
    }
    setHydrated(true);
  }, [
    hydrated,
    company,
    settingLegalForm.data,
    settingActivity.data,
    currentFiscalYear.data,
    settingLegalForm.isSuccess,
    settingActivity.isSuccess,
    currentFiscalYear.isSuccess,
    currentFiscalYear.isError,
  ]);

  const busy =
    upsertSetting.isPending ||
    upsertParameter.isPending ||
    upsertRate.isPending ||
    createFiscalYear.isPending ||
    seedPlan.isPending;

  /** PUT /core/companies/{id} — échoue en 403 si non super-admin (non bloquant). */
  const saveCompanyFields = async (payload: Record<string, unknown>) => {
    if (!company || !user) return false;
    try {
      await apiClient.put(`/core/companies/${company.id}`, payload);
      return true;
    } catch (error) {
      setNotice({
        kind: "warn",
        text:
          "Coordonnées non enregistrées (droits insuffisants — réservé à l'administrateur). Les autres paramètres ont bien été sauvegardés.",
      });
      return false;
    }
  };

  const nextFromIdentification = async () => {
    setNotice(null);
    if (!legalName.trim()) {
      setNotice({ kind: "warn", text: "La raison sociale est obligatoire." });
      return;
    }
    await upsertSetting.mutateAsync({
      key: "accounting_legal_form",
      value: legalForm,
      description: "Forme juridique (wizard configuration comptable)",
    });
    await saveCompanyFields({ name: legalName.trim(), tax_country: countryCode });
    setStep(1);
  };

  const nextFromCurrency = async () => {
    setNotice(null);
    const eur = parseFloat(eurRate.replace(",", "."));
    const vat = parseFloat(vatRate.replace(",", "."));
    if (!(eur > 0)) {
      setNotice({ kind: "warn", text: "Le taux de change vers l'EUR doit être positif." });
      return;
    }
    await upsertParameter.mutateAsync({
      country_code: countryCode,
      currency_code: selectedCountry.currency,
      tax_rate_percentage: Number.isFinite(vat) ? vat : 0,
      fiscal_year_start: `${fyStart.slice(0, 4)}-01-01`,
      fiscal_year_end: `${fyStart.slice(0, 4)}-12-31`,
      is_active: true,
    });
    await upsertRate.mutateAsync({
      base_currency: selectedCountry.currency,
      quote_currency: "EUR",
      rate: eur,
    });
    const usd = parseFloat(usdRate.replace(",", "."));
    if (Number.isFinite(usd) && usd > 0) {
      await upsertRate.mutateAsync({
        base_currency: selectedCountry.currency,
        quote_currency: "USD",
        rate: usd,
      });
    }
    setStep(2);
  };

  const nextFromCoords = async () => {
    setNotice(null);
    await upsertSetting.mutateAsync({
      key: "accounting_naf_activity",
      value: activity.trim(),
      description: "Code activité NAF/OHADA (wizard configuration comptable)",
    });
    await saveCompanyFields({
      phone: phone.trim() || null,
      email: email.trim() || null,
      ncc: ncc.trim() || null,
      rccm: rccm.trim() || null,
      share_capital: capital.trim() || null,
      address: {
        ...(company?.address ?? {}),
        line1: addressLine.trim(),
        city: city.trim(),
        postal_code: postalCode.trim(),
        country: selectedCountry.name,
      },
    });
    setStep(3);
  };

  const handleCreateFiscalYear = async () => {
    setNotice(null);
    if (fyStart >= fyEnd) {
      setNotice({
        kind: "warn",
        text: "La date de début doit précéder la date de fin de l'exercice.",
      });
      return;
    }
    await createFiscalYear.mutateAsync({
      name: fyName.trim() || `Exercice ${fyStart.slice(0, 4)}`,
      start_date: fyStart,
      end_date: fyEnd,
    });
    setNotice({
      kind: "ok",
      text: `Exercice « ${fyName} » créé et ouvert.`,
    });
  };

  const handleSeedPlan = async () => {
    setNotice(null);
    const result = await seedPlan.mutateAsync();
    setSeedResult(result);
  };
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Configuration de la comptabilité
        </h1>
        <p className="text-sm text-gray-600">
          Assistant OHADA — paramétrage conforme SYSCOHADA Révisé
        </p>
      </div>

      {/* Stepper */}
      <ol className="flex flex-wrap items-center gap-1">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const active = i === step;
          const done = i < step;
          return (
            <li key={s.label} className="flex items-center">
              <button
                type="button"
                onClick={() => done && setStep(i)}
                disabled={!done}
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-[#0a2a6b] text-white"
                    : done
                      ? "text-[#0a2a6b] hover:bg-blue-50"
                      : "text-gray-400"
                }`}
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                    active
                      ? "bg-amber-400 text-gray-900"
                      : done
                        ? "bg-blue-100"
                        : "bg-gray-100"
                  }`}
                >
                  {done ? <BadgeCheck className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <span className="hidden sm:inline">{s.label}</span>
                <Icon className="hidden h-4 w-4 opacity-60 md:inline" />
              </button>
              {i < STEPS.length - 1 && (
                <span className="mx-1 h-px w-6 bg-gray-300" />
              )}
            </li>
          );
        })}
      </ol>

      {notice && (
        <div
          className={`rounded-md border px-4 py-3 text-sm ${
            notice.kind === "ok"
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-amber-200 bg-amber-50 text-amber-800"
          }`}
        >
          {notice.kind === "warn" ? (
            <TriangleAlert className="mr-1 inline h-4 w-4" />
          ) : (
            <BadgeCheck className="mr-1 inline h-4 w-4" />
          )}
          {notice.text}
        </div>
      )}

      <Card>
        {/* ---------------- Etape 1 — Identification ---------------- */}
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Identification de la société
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Reprise automatique des informations générales de
                l&apos;entreprise — modifiables ici et dans les Paramètres.
              </p>
            </div>
            <div>
              <label className={labelClass}>Raison sociale</label>
              <input
                className={inputClass}
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                placeholder="Ex. PrimeMAT Distribution SARL"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Forme juridique</label>
                <select
                  className={inputClass}
                  value={legalForm}
                  onChange={(e) => setLegalForm(e.target.value)}
                >
                  {LEGAL_FORMS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Pays OHADA</label>
                <select
                  className={inputClass}
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                >
                  {OHADA_COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name} ({c.currency})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-500">
              Code entreprise : <strong>{company?.code ?? "—"}</strong> — devise
              de tenue de compte : <strong>{company?.currency_code ?? "—"}</strong>
            </p>
          </div>
        )}

        {/* ---------------- Etape 2 — Monnaie ---------------- */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Monnaie de tenue de compte
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Comptabilité tenue en <strong>{selectedCountry.currency}</strong> ({selectedCountry.name}). Renseignez les taux de change utilisés pour les états financiers.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass}>
                  Taux 1 {selectedCountry.currency} vers EUR
                </label>
                <input
                  className={inputClass}
                  value={eurRate}
                  onChange={(e) => setEurRate(e.target.value)}
                  inputMode="decimal"
                />
              </div>
              <div>
                <label className={labelClass}>
                  Taux 1 {selectedCountry.currency} vers USD
                </label>
                <input
                  className={inputClass}
                  value={usdRate}
                  onChange={(e) => setUsdRate(e.target.value)}
                  inputMode="decimal"
                />
              </div>
              <div>
                <label className={labelClass}>TVA par défaut (%)</label>
                <input
                  className={inputClass}
                  value={vatRate}
                  onChange={(e) => setVatRate(e.target.value)}
                  inputMode="decimal"
                />
              </div>
            </div>
            <p className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-500">
              Le paramètre OHADA du pays "{selectedCountry.name}" sera créé ou mis à jour avec ces valeurs (devise {selectedCountry.currency}).
            </p>
          </div>
        )}

        {/* ---------------- Étape 3 — Coordonnées ---------------- */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Coordonnées de l&apos;entreprise
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Ces informations alimentent le module Société et les documents
                comptables (annexes, états financiers).
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Activité (code NAF/OHADA)</label>
                <input
                  className={inputClass}
                  value={activity}
                  onChange={(e) => setActivity(e.target.value)}
                  placeholder="Ex. 46690 — Commerce de gros"
                />
              </div>
              <div>
                <label className={labelClass}>Ville</label>
                <input
                  className={inputClass}
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Ex. Ouagadougou"
                />
              </div>
            </div>
            <div>
              <label className={labelClass}>Adresse</label>
              <input
                className={inputClass}
                value={addressLine}
                onChange={(e) => setAddressLine(e.target.value)}
                placeholder="Rue, quartier, avenue…"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass}>Code postal</label>
                <input
                  className={inputClass}
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Téléphone</label>
                <input
                  className={inputClass}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Email</label>
                <input
                  className={inputClass}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass}>N° Contribuable (NCC)</label>
                <input
                  className={inputClass}
                  value={ncc}
                  onChange={(e) => setNcc(e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>RCCM</label>
                <input
                  className={inputClass}
                  value={rccm}
                  onChange={(e) => setRccm(e.target.value)}
                />
              </div>
              <div>
                <label className={labelClass}>Capital social</label>
                <input
                  className={inputClass}
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* ---------------- Étape 4 — Exercice ---------------- */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Exercice comptable
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                L&apos;exercice délimite les écritures comptables — aucune
                modification des dates après création.
              </p>
            </div>

            {currentFiscalYear.data ? (
              <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                <BadgeCheck className="mr-1 inline h-4 w-4" />
                Exercice « {currentFiscalYear.data.name} » ouvert du{" "}
                {currentFiscalYear.data.start_date} au{" "}
                {currentFiscalYear.data.end_date}.
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className={labelClass}>Nom de l&apos;exercice</label>
                  <input
                    className={inputClass}
                    value={fyName}
                    onChange={(e) => setFyName(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelClass}>Date de début</label>
                    <input
                      type="date"
                      className={inputClass}
                      value={fyStart}
                      onChange={(e) => setFyStart(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Date de fin</label>
                    <input
                      type="date"
                      className={inputClass}
                      value={fyEnd}
                      onChange={(e) => setFyEnd(e.target.value)}
                    />
                  </div>
                </div>
                <Button
                  onClick={handleCreateFiscalYear}
                  disabled={createFiscalYear.isPending}
                  className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
                >
                  {createFiscalYear.isPending && (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  )}
                  Créer et ouvrir l&apos;exercice
                </Button>
              </div>
            )}
          </div>
        )}

        {/* ---------------- Étape 5 — Plan comptable ---------------- */}
        {step === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Reprise des éléments comptables
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Le plan comptable SYSCOHADA Révisé (9 classes) et les journaux
                par défaut sont initialisés en une seule opération.
              </p>
            </div>

            <div className="space-y-2">
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-[#0a2a6b] bg-blue-50 p-3">
                <input
                  type="radio"
                  name="seed-mode"
                  checked
                  readOnly
                  className="mt-1"
                />
                <span className="text-sm">
                  <strong>Modèle standard OHADA (recommandé)</strong>
                  <br />
                  <span className="text-gray-600">
                    Plan comptable complet, journaux Achat/Vente/Banque/Caisse/
                    Paie/OD pré-configurés.
                  </span>
                </span>
              </label>
              <label className="flex cursor-not-allowed items-start gap-3 rounded-md border p-3 opacity-50">
                <input type="radio" name="seed-mode" disabled className="mt-1" />
                <span className="text-sm">Sélection partielle (bientôt)</span>
              </label>
              <label className="flex cursor-not-allowed items-start gap-3 rounded-md border p-3 opacity-50">
                <input type="radio" name="seed-mode" disabled className="mt-1" />
                <span className="text-sm">Paramétrage entièrement manuel (bientôt)</span>
              </label>
            </div>

            {!seedResult && (
              <Button
                onClick={handleSeedPlan}
                disabled={seedPlan.isPending}
                className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
              >
                {seedPlan.isPending && (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                )}
                Initialiser le plan comptable OHADA
              </Button>
            )}

            {seedResult && (
              <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                <BadgeCheck className="mr-1 inline h-4 w-4" />
                {seedResult.created > 0
                  ? `${seedResult.created} comptes créés`
                  : "Plan comptable déjà initialisé"}
                — {seedResult.total} comptes au total, {seedResult.journals_created}{" "}
                journaux par défaut.
              </div>
            )}

            {constraints.data && (
              <div
                className={`rounded-md border px-4 py-3 text-sm ${
                  constraints.data.can_open
                    ? "border-green-200 bg-green-50 text-green-800"
                    : "border-amber-200 bg-amber-50 text-amber-800"
                }`}
              >
                {constraints.data.can_open
                  ? "Contraintes OHADA validées — la saisie comptable peut commencer."
                  : `À compléter : ${constraints.data.message}`}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0 || busy}
        >
          <ArrowLeft className="mr-1 h-4 w-4" /> Précédent
        </Button>

        {step === 0 && (
          <Button
            onClick={nextFromIdentification}
            disabled={busy}
            className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
          >
            {busy && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
            Suivant <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        )}
        {step === 1 && (
          <Button
            onClick={nextFromCurrency}
            disabled={busy}
            className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
          >
            {busy && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
            Suivant <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        )}
        {step === 2 && (
          <Button
            onClick={nextFromCoords}
            disabled={busy}
            className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
          >
            {busy && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
            Suivant <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        )}
        {step === 3 &&
          (currentFiscalYear.data ? (
            <Button
              onClick={() => setStep(4)}
              disabled={busy}
              className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
            >
              Suivant <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleCreateFiscalYear}
              disabled={createFiscalYear.isPending}
              className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
            >
              {createFiscalYear.isPending && (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              )}
              Créer et ouvrir l&apos;exercice
            </Button>
          ))}
        {step === 4 && (
          <Button
            onClick={() => router.push("/dashboard/accounting")}
            className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
          >
            <Settings2 className="mr-1 h-4 w-4" />
            Accéder à la comptabilité
          </Button>
        )}
      </div>
    </div>
  );
}
