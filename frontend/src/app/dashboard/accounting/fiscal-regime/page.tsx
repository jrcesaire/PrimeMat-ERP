/**
 * Page Configuration fiscale — régime d'imposition Côte d'Ivoire (TEE / RME / RSI / RNI).
 */
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TriangleAlert,
  CheckCircle2,
  Coins,
  Loader2,
  Save,
  TrendingUp,
} from "lucide-react";
import {
  useDetectCATreshold,
  useFiscalRegime,
  useUpdateFiscalRegime,
  REGIMES,
  REGIME_BY_CODE,
} from "@/hooks/useFiscalRegime";

function formatFCFA(value: number | null): string {
  if (value === null || value === undefined) return "Aucun plafond";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "XOF",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function FiscalRegimePage() {
  const [busy, setBusy] = useState(false);
  const [detectBusy, setDetectBusy] = useState(false);

  const { data: regime, isLoading, refetch } = useFiscalRegime();
  const updateRegime = useUpdateFiscalRegime();
  const detectCA = useDetectCATreshold();

  const currentRegimeInfo = regime?.tax_regime
    ? REGIME_BY_CODE[regime.tax_regime]
    : null;
  const suggestedInfo = regime?.suggested_tax_regime
    ? REGIME_BY_CODE[regime.suggested_tax_regime]
    : null;

  async function handleSave(taxRegime: string) {
    setBusy(true);
    try {
      await updateRegime.mutateAsync({ tax_regime: taxRegime });
      await refetch();
    } finally {
      setBusy(false);
    }
  }

  async function handleDetectCA() {
    if (!regime?.tax_regime) return;
    setDetectBusy(true);
    try {
      const caThreshold = currentRegimeInfo?.ca_threshold ?? 0;
      const caToTest = window.prompt(
        `Saisissez le CA annuel TTC en FCFA (seuil actuel : ${formatFCFA(caThreshold)}):`,
        String(caThreshold),
      );
      if (caToTest === null) return;
      const caValue = parseFloat(caToTest.replace(/[^\d]/g, "")) || 0;
      await detectCA.mutateAsync(caValue);
      await refetch();
    } finally {
      setDetectBusy(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configuration fiscale</h1>
          <p className="text-sm text-gray-600">
            Régime d'imposition SYSCOHADA — Côte d'Ivoire (TEE / RME / RSI / RNI)
          </p>
        </div>
        <Button onClick={() => refetch()} disabled={isLoading} className="ml-auto">
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Rafraîchir
        </Button>
      </div>

      {/* Carte principale : régime actuel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Coins className="h-5 w-5" />
            Régime fiscal actuel
          </CardTitle>
          <CardDescription>
            Sélection du régime d'imposition de l'entreprise.
            Aucun basculement automatique n'est appliqué : le changement reste
            une décision manuelle.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {regime && (
            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-lg border p-4">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Régime actuel
                </p>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{regime.tax_regime ?? "Non défini"}</span>
                  <Badge variant={regime.tva_blocked ? "destructive" : "default"} className="ml-auto">
                    {regime.tva_blocked ? "TVA bloquée" : "TVA autorisée"}
                  </Badge>
                </div>
                {currentRegimeInfo && (
                  <p className="mt-2 text-sm text-gray-600">{currentRegimeInfo.description}</p>
                )}
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Seuil de CA annuel
                </p>
                <div className="mt-1 text-2xl font-bold">{formatFCFA(currentRegimeInfo?.ca_threshold ?? null)}</div>
              </div>
            </div>
          )}

          <div className="pt-4 border-t space-y-4">
            <p className="text-sm font-medium text-gray-700">Changer le régime fiscal</p>
            <div className="space-y-2">
              {REGIMES.map((r) => (
                <button
                  key={r.code}
                  onClick={() => handleSave(r.code)}
                  disabled={busy || regime?.tax_regime === r.code}
                  className={`w-full flex justify-between items-center px-4 py-3 rounded-lg border transition-colors ${
                    regime?.tax_regime === r.code
                      ? "bg-blue-50 border-blue-200 text-blue-700"
                      : "bg-white border-gray-200 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span>{r.label}</span>
                  {regime?.tax_regime === r.code && <span className="text-xs">Actuel</span>}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alerte de dépassement de seuil */}
      {regime && regime.ca_exceeds_threshold && suggestedInfo && (
        <Alert className="border-amber-200 bg-amber-50">
          <TriangleAlert className="h-4 w-4" />
          <AlertTitle>Dépassement de seuil CA détecté</AlertTitle>
          <AlertDescription className="sm:flex">
            Votre CA annuel dépasse le plafond du régime{" "}
            <strong>{regime.tax_regime}</strong> (
            {formatFCFA(regime.ca_threshold)}). Un passage vers le régime{" "}
            <strong>{suggestedInfo.code}</strong> est suggéré :{" "}
            {suggestedInfo.description}. Le changement reste à valider manuellement
            ci-dessus — aucun basculement automatique n'est effectué.
          </AlertDescription>
        </Alert>
      )}

      {/* Information TVA */}
      {regime && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {regime.tva_blocked ? (
                <TriangleAlert className="h-5 w-5 text-orange-500" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              )}
              Statut TVA
            </CardTitle>
            <CardDescription>
              Régime <strong>{regime.tax_regime}</strong> — la TVA est{" "}
              {regime.tva_blocked ? "bloquée" : "autorisée"} pour cette entreprise.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              {regime.tva_blocked ? (
                <>
                  <p className="text-sm text-orange-600 font-medium">TVA non collectable</p>
                  <p className="text-xs text-gray-500">
                    Les factures émises ne comportent pas de TVA.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm text-green-600 font-medium">TVA collectable et déductible</p>
                  <p className="text-xs text-gray-500">
                    Les factures comportent la TVA applicable selon le taux configuré.
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bouton de détection de dépassement */}
      {regime && currentRegimeInfo && (
        <Card>
          <CardHeader>
            <CardTitle>Test de dépassement de seuil CA</CardTitle>
            <CardDescription>
              Saisissez un CA annuel TTC pour vérifier si le régime actuel est
              dépassé. Aucune modification n'est apportée — seule une suggestion
              de changement est affichée.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row gap-4 items-end">
            <Button
              onClick={handleDetectCA}
              disabled={detectBusy}
              className="flex-1 sm:flex-auto"
            >
              {detectBusy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <TrendingUp className="mr-2 h-4 w-4" />
              Tester le dépassement
            </Button>
            <p className="text-sm text-gray-500">
              Seuil actuel : {formatFCFA(currentRegimeInfo.ca_threshold)}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}