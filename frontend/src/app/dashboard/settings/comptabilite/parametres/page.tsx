/**
 * Paramètres comptables — référentiel du plan comptable.
 *
 * Le référentiel (SYSCOHADA commercial ou SYCEBNL) se choisit à
 * l'initialisation, dans l'assistant de configuration. Il reste modifiable ici
 * **tant que la comptabilité est vierge** : un changement remplace tout le
 * plan, les codes de l'ancien référentiel n'ayant plus de sens dans le nouveau.
 * Le serveur refuse l'opération dès qu'une écriture, une immobilisation ou une
 * déclaration de TVA existe.
 */
"use client";

import { useEffect, useState } from "react";
import { AxiosError } from "axios";
import { CheckCircle2, Info, Loader2, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SettingsSectionHeader } from "@/components/settings/settings-section-header";
import { usePermission } from "@/hooks/useAuth";
import { useAccountingChart, useChangeAccountingChart } from "@/hooks/useOHADA";
import {
  CHART_OPTIONS,
  DEFAULT_CHART,
  chartLabel,
  type ChartOfAccounts,
} from "@/lib/accounting-charts";

export default function AccountingSettingsPage() {
  const { data: chart, isLoading } = useAccountingChart();
  const changeChart = useChangeAccountingChart();
  // La bascule exige « account:edit » côté serveur : on ne montre pas
  // l'interface à un profil qui n'a que la lecture.
  const canEdit = usePermission()("account:edit");

  const [selected, setSelected] = useState<ChartOfAccounts>(DEFAULT_CHART);
  const [notice, setNotice] = useState<{
    kind: "ok" | "error";
    text: string;
  } | null>(null);

  // Le référentiel courant pilote la sélection tant que rien n'a été appliqué.
  useEffect(() => {
    if (chart?.chart_of_accounts) {
      setSelected(chart.chart_of_accounts as ChartOfAccounts);
    }
  }, [chart?.chart_of_accounts]);

  const current = chart?.chart_of_accounts ?? DEFAULT_CHART;
  const dirty = chart !== undefined && selected !== current;
  const locked = chart !== undefined && !chart.can_change;

  const apply = async () => {
    setNotice(null);
    try {
      const result = await changeChart.mutateAsync(selected);
      setNotice({
        kind: "ok",
        text:
          `Plan ${result.label} chargé — ${result.account_count} comptes. ` +
          "Le plan précédent a été remplacé.",
      });
    } catch (error) {
      const detail =
        error instanceof AxiosError ? error.response?.data?.detail : undefined;
      setNotice({
        kind: "error",
        text: typeof detail === "string" ? detail : "Le changement a échoué.",
      });
    }
  };

  return (
    <div className="space-y-6">
      <SettingsSectionHeader
        title="Paramètres comptables"
        description="Référentiel du plan comptable de l'entreprise"
      />

      <Card className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-faint">
              Référentiel courant
            </p>
            <p className="text-lg font-semibold text-ink">
              {isLoading ? "…" : chart?.label ?? chartLabel(current)}
            </p>
          </div>
          <p className="text-sm text-muted">
            {chart ? `${chart.account_count} comptes chargés` : "—"}
          </p>
        </div>

        {locked && chart && (
          <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <Lock className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Le référentiel ne peut plus être changé : un autre référentiel
              renumérote tout le plan. Il reste pour l&apos;instant{" "}
              <strong>{chart.blockers.join(", ")}</strong>. Videz la
              comptabilité ou créez une nouvelle entreprise pour repartir sur un
              autre plan.
            </span>
          </div>
        )}

        {!locked && !canEdit && (
          <div className="flex gap-2 rounded-md border border-line bg-canvas px-4 py-3 text-sm text-muted">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Seul un profil autorisé à modifier la comptabilité peut changer de
              référentiel.
            </span>
          </div>
        )}

        {!locked && canEdit && (
          <>
            <div className="flex gap-2 rounded-md border border-line bg-canvas px-4 py-3 text-sm text-muted">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Changer de référentiel <strong>remplace</strong> le plan
                comptable : les comptes actuels sont supprimés et remplacés par
                ceux du référentiel choisi. Les journaux sont conservés.
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {CHART_OPTIONS.map((option) => {
                const active = selected === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setSelected(option.value)}
                    className={`rounded-lg border p-4 text-left transition-colors ${
                      active
                        ? "border-primary bg-canvas"
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
                    <span className="mt-2 block text-xs text-faint">
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

            <div className="flex items-center gap-3">
              <Button onClick={apply} disabled={!dirty || changeChart.isPending}>
                {changeChart.isPending && (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                )}
                Appliquer {chartLabel(selected)}
              </Button>
              {dirty && (
                <span className="text-sm text-muted">
                  Le plan actuel sera remplacé.
                </span>
              )}
            </div>
          </>
        )}

        {notice && (
          <div
            className={`flex gap-2 rounded-md border px-4 py-3 text-sm ${
              notice.kind === "ok"
                ? "border-success/30 bg-success-soft text-success"
                : "border-danger/30 bg-danger-soft text-danger"
            }`}
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{notice.text}</span>
          </div>
        )}
      </Card>
    </div>
  );
}
