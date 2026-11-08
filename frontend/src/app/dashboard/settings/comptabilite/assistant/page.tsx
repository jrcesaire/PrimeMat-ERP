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
import { useCurrentCompany, useCurrentUser, useUpdateCompany } from "@/hooks/useAuth";
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
import {
  CHART_OPTIONS,
  DEFAULT_CHART,
  chartLabel,
  type ChartOfAccounts,
} from "@/lib/accounting-charts";
import { apiClient } from "@/lib/api/client";
import { COUNTRIES, countryByCode } from "@/lib/countries-currencies";

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
  "w-full rounded-md border border-line px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-faint focus:border-blue-600";

const labelClass =
  "mb-1 block text-sm font-medium text-muted";

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
  /** Renseignements d'entité (assistant de configuration fiscale). */
  greffe?: string | null;
  importer_code?: string | null;
  social_security_code?: string | null;
  activity_code?: string | null;
  closing_date?: string | null;
  fiscal_year_months?: number;
  /** Référentiel du plan comptable (SYSCOHADA commercial ou SYCEBNL). */
  chart_of_accounts?: ChartOfAccounts;
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
  const updateCompany = useUpdateCompany();

  const [step, setStep] = useState(0);
  const [hydrated, setHydrated] = useState(false);
  const [notice, setNotice] = useState<{ kind: "ok" | "warn"; text: string } | null>(
    null,
  );
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);
  // Référentiel comptable retenu à l'étape 5.
  const [chart, setChart] = useState<ChartOfAccounts>(DEFAULT_CHART);

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
  // Renseignements d'entité — repris sur les documents officiels.
  const [greffe, setGreffe] = useState("");
  const [importerCode, setImporterCode] = useState("");
  const [socialSecurityCode, setSocialSecurityCode] = useState("");
  const [closingDate, setClosingDate] = useState("31/12");
  const [fiscalYearMonths, setFiscalYearMonths] = useState("12");

  // Étape 4 — Exercice
  const currentYear = new Date().getFullYear();
  const [fyName, setFyName] = useState(`Exercice ${currentYear}`);
  const [fyStart, setFyStart] = useState(`${currentYear}-01-01`);
  const [fyEnd, setFyEnd] = useState(`${currentYear}-12-31`);

  // Le pays choisi pilote la devise de tenue de compte. Deux pays de la liste
  // sont déclarés sans devise (Antarctique, territoires palestiniens) : la
  // devise de l'entreprise prend alors le relais, plutôt que de laisser un code
  // vide dans les paramètres comptables.
  const selectedCountry = useMemo(() => {
    const found = countryByCode(countryCode);
    return {
      code: countryCode,
      name: found?.name ?? countryCode,
      currency: found?.currency || company?.currency_code || "XOF",
    };
  }, [countryCode, company?.currency_code]);

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
      // Renseignements d'entité déjà saisis à la configuration initiale.
      setGreffe((prev) => prev || company.greffe || "");
      setImporterCode((prev) => prev || company.importer_code || "");
      setSocialSecurityCode(
        (prev) => prev || company.social_security_code || "",
      );
      setClosingDate((prev) => prev || company.closing_date || "31/12");
      setFiscalYearMonths((prev) =>
        prev !== "12" ? prev : String(company.fiscal_year_months ?? 12),
      );
      if (company.chart_of_accounts) setChart(company.chart_of_accounts);
      const addr = company.address ?? {};
      setAddressLine((prev) => prev || addr.line1 || addr.address || "");
      setCity((prev) => prev || addr.city || "");
      setPostalCode((prev) => prev || addr.postal_code || "");
      if (company.tax_country) {
        const found = countryByCode(company.tax_country);
        if (found) setCountryCode(found.code);
      }
    }
    if (settingLegalForm.data?.value) {
      setLegalForm(settingLegalForm.data.value);
    }
    // Le code d'activité est porté par l'entreprise depuis la configuration
    // initiale : il prime sur le paramètre historique `accounting_naf_activity`.
    // Aucune valeur par défaut n'est proposée — le code dépend de l'activité
    // déclarée par l'entreprise.
    const storedActivity = company?.activity_code || settingActivity.data?.value;
    setActivity((prev) => prev || storedActivity || "");
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
      // Renseignements d'entité — figurent sur les documents officiels.
      greffe: greffe.trim() || null,
      importer_code: importerCode.trim() || null,
      social_security_code: socialSecurityCode.trim() || null,
      activity_code: activity.trim() || null,
      closing_date: closingDate.trim() || null,
      fiscal_year_months: Number(fiscalYearMonths) || 12,
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

  /**
   * Enregistre le référentiel retenu puis initialise le plan comptable.
   *
   * Le serveur charge le plan d'après ``Company.chart_of_accounts`` :
   * l'entreprise doit donc porter le bon référentiel *avant* le seed.
   */
  const handleSeedPlan = async () => {
    setNotice(null);
    if (company && chart !== (company.chart_of_accounts ?? DEFAULT_CHART)) {
      await updateCompany.mutateAsync({
        id: company.id,
        chart_of_accounts: chart,
      });
    }
    const result = await seedPlan.mutateAsync();
    setSeedResult(result);
  };
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-[28px] font-semibold leading-tight text-ink">
          Configuration de la comptabilité
        </h1>
        <p className="text-sm text-muted">
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
                      ? "text-ink hover:bg-info-soft"
                      : "text-faint"
                }`}
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                    active
                      ? "bg-accent text-white"
                      : done
                        ? "bg-info-soft"
                        : "bg-subtle"
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
              <h2 className="text-lg font-semibold text-ink">
                Identification de la société
              </h2>
              <p className="mt-1 text-sm text-muted">
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
                <label className={labelClass}>Pays</label>
                <select
                  className={inputClass}
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                >
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                      {c.currency ? ` (${c.currency})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="rounded-md bg-subtle px-3 py-2 text-xs text-muted">
              Code entreprise : <strong>{company?.code ?? "—"}</strong> — devise
              de tenue de compte : <strong>{company?.currency_code ?? "—"}</strong>
            </p>
          </div>
        )}

        {/* ---------------- Etape 2 — Monnaie ---------------- */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Monnaie de tenue de compte
              </h2>
              <p className="mt-1 text-sm text-muted">
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
            <p className="rounded-md bg-subtle px-3 py-2 text-xs text-muted">
              Le paramètre OHADA du pays "{selectedCountry.name}" sera créé ou mis à jour avec ces valeurs (devise {selectedCountry.currency}).
            </p>
          </div>
        )}

        {/* ---------------- Étape 3 — Coordonnées ---------------- */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Coordonnées de l&apos;entreprise
              </h2>
              <p className="mt-1 text-sm text-muted">
                Ces informations alimentent le module Société et les documents
                comptables (annexes, états financiers).
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Code activité principale</label>
                <input
                  className={inputClass}
                  value={activity}
                  onChange={(e) => setActivity(e.target.value)}
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

            {/* Renseignements d'entité — recommandés, repris sur les documents. */}
            <div className="border-t border-line pt-4">
              <p className="mb-1 text-sm font-semibold text-ink">
                Renseignements d&apos;entité
              </p>
              <p className="mb-3 text-xs text-muted">
                Facultatifs, mais exigés par l&apos;administration : ils
                apparaissent sur les documents officiels.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={labelClass}>Greffe (tribunal)</label>
                  <input
                    className={inputClass}
                    value={greffe}
                    onChange={(e) => setGreffe(e.target.value)}
                    placeholder="Ex. Tribunal de commerce d'Abidjan"
                  />
                </div>
                <div>
                  <label className={labelClass}>N° code importateur</label>
                  <input
                    className={inputClass}
                    value={importerCode}
                    onChange={(e) => setImporterCode(e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>N° de caisse sociale</label>
                  <input
                    className={inputClass}
                    value={socialSecurityCode}
                    onChange={(e) => setSocialSecurityCode(e.target.value)}
                  />
                </div>
                <div>
                  <label className={labelClass}>
                    Date d&apos;arrêté des comptes
                  </label>
                  <input
                    className={inputClass}
                    value={closingDate}
                    onChange={(e) => setClosingDate(e.target.value)}
                    placeholder="31/12"
                  />
                </div>
                <div>
                  <label className={labelClass}>
                    Durée de l&apos;exercice
                  </label>
                  <select
                    className={inputClass}
                    value={fiscalYearMonths}
                    onChange={(e) => setFiscalYearMonths(e.target.value)}
                  >
                    <option value="12">12 mois (année civile)</option>
                    <option value="9">9 mois</option>
                    <option value="6">6 mois</option>
                    <option value="3">3 mois</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- Étape 4 — Exercice ---------------- */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Exercice comptable
              </h2>
              <p className="mt-1 text-sm text-muted">
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
              <h2 className="text-lg font-semibold text-ink">
                Reprise des éléments comptables
              </h2>
              <p className="mt-1 text-sm text-muted">
                Choisissez le référentiel : le plan comptable complet (9 classes)
                et les journaux par défaut sont initialisés en une seule
                opération.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {CHART_OPTIONS.map((option) => {
                const active = chart === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => {
                      setChart(option.value);
                      // Le plan déjà chargé ne correspond plus : on redemande
                      // l'initialisation pour le nouveau référentiel.
                      setSeedResult(null);
                    }}
                    className={`rounded-lg border p-4 text-left transition-colors ${
                      active
                        ? "border-primary bg-info-soft"
                        : "border-line hover:border-primary/40"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="chart-of-accounts"
                        value={option.value}
                        checked={active}
                        readOnly
                        className="pointer-events-none"
                      />
                      <strong className="text-sm text-ink">{option.label}</strong>
                    </span>
                    <span className="mt-2 block text-sm text-muted">
                      {option.summary}
                    </span>
                    <span className="mt-2 block space-y-0.5 text-xs text-faint">
                      {option.highlights.map((item) => (
                        <span key={item} className="block">
                          {item}
                        </span>
                      ))}
                    </span>
                  </button>
                );
              })}
            </div>

            {!seedResult && (
              <Button
                onClick={handleSeedPlan}
                disabled={seedPlan.isPending || updateCompany.isPending}
                className="bg-[#0a2a6b] text-white hover:bg-[#0d3a8f]"
              >
                {seedPlan.isPending && (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                )}
                Initialiser le plan {chartLabel(chart)}
              </Button>
            )}

            {seedResult && (
              <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                <BadgeCheck className="mr-1 inline h-4 w-4" />
                {seedResult.created > 0
                  ? `${seedResult.created} comptes créés`
                  : "Plan comptable déjà initialisé"}{" "}
                au format {chartLabel(chart)} — {seedResult.total} comptes au
                total, {seedResult.journals_created} journaux par défaut.
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
