/**
 * Réglages du Point de Vente (PRD « Improvements module PoS » §4.2.2.6).
 *
 * Écran immersif (sidebar + header masqués, bouton « Retour ») ouvert depuis
 * la tuile « Réglages » du dashboard PoS. Il ne regroupe que les paramètres
 * propres au Point de Vente :
 * - heure de clôture automatique des sessions de caisse (§4.1.2.3) ;
 * - heure-valeur de l'écriture comptable des ventes ;
 * - URL publique imprimée dans le QR code des tickets de caisse.
 *
 * §7 Sécurité : écran réservé aux rôles Administrateur / Gérant — matérialisé
 * par la permission « pos:edit » (le backend applique la même règle).
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, Clock, QrCode, Save, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePermission } from "@/hooks/useAuth";
import { usePosSettings, useUpdatePosSettings } from "@/hooks/usePosSettings";
import { setPosFocus } from "@/lib/pos-focus";

/** Heures proposées dans les listes déroulantes (0 → 23). */
const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

/** Libellé d'une heure de la journée : « 08h00 ». */
function hourLabel(hour: number): string {
  return `${String(hour).padStart(2, "0")}h00`;
}

/** Style des listes déroulantes, aligné sur le composant Input. */
const SELECT_CLASS =
  "flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50";

export function PosSettings() {
  const router = useRouter();
  const can = usePermission();
  // §7 — écriture des réglages réservée aux rôles Administrateur / Gérant.
  const canEdit = can("pos:edit");

  const { data, isLoading } = usePosSettings();
  const updateSettings = useUpdatePosSettings();

  const [closingHour, setClosingHour] = useState(0);
  const [writeupHour, setWriteupHour] = useState(0);
  const [ticketUrl, setTicketUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mode immersif : sidebar + header masqués tant qu'on reste dans le PoS.
  useEffect(() => {
    setPosFocus(true);
    return () => setPosFocus(false);
  }, []);

  // Hydratation du formulaire avec les réglages enregistrés.
  useEffect(() => {
    if (!data) return;
    setClosingHour(data.closing_hour ?? 0);
    setWriteupHour(data.accounting_write_up_hour ?? 0);
    setTicketUrl(data.ticket_url ?? "");
  }, [data]);

  const isDirty =
    data != null &&
    (closingHour !== data.closing_hour ||
      writeupHour !== data.accounting_write_up_hour ||
      ticketUrl !== (data.ticket_url ?? ""));

  const handleSave = async () => {
    setError(null);
    setSaved(false);
    try {
      await updateSettings.mutateAsync({
        closing_hour: closingHour,
        accounting_write_up_hour: writeupHour,
        ticket_url: ticketUrl,
      });
      setSaved(true);
    } catch {
      setError("L'enregistrement des réglages a échoué. Veuillez réessayer.");
    }
  };

  const goBack = () => {
    setPosFocus(false);
    router.push("/dashboard/sales/pos");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col px-[20px] md:px-[80px] py-6">
      {/* Bandeau : retour vers le menu du PoS */}
      <header className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={goBack}
          title="Revenir au menu du Point de Vente"
        >
          <ArrowLeft className="h-4 w-4" /> Retour
        </Button>
        <div className="text-right leading-tight">
          <div className="text-sm font-semibold text-gray-900">
            Réglages du Point de Vente
          </div>
          <div className="text-xs text-gray-500">Paramètres de la caisse</div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-[760px] mx-auto py-8 space-y-6">
        {!canEdit ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldAlert className="h-5 w-5 text-amber-600" />
                Accès réservé
              </CardTitle>
              <CardDescription>
                Les réglages du Point de Vente sont réservés aux rôles
                Administrateur et Gérant.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <PosSettingsForm
            isLoading={isLoading}
            isDirty={isDirty}
            isSaving={updateSettings.isPending}
            saved={saved}
            error={error}
            closingHour={closingHour}
            writeupHour={writeupHour}
            ticketUrl={ticketUrl}
            onClosingHourChange={(hour) => {
              setSaved(false);
              setClosingHour(hour);
            }}
            onWriteupHourChange={(hour) => {
              setSaved(false);
              setWriteupHour(hour);
            }}
            onTicketUrlChange={(url) => {
              setSaved(false);
              setTicketUrl(url);
            }}
            onSave={handleSave}
          />
        )}
      </main>
    </div>
  );
}

interface PosSettingsFormProps {
  isLoading: boolean;
  isDirty: boolean;
  isSaving: boolean;
  saved: boolean;
  error: string | null;
  closingHour: number;
  writeupHour: number;
  ticketUrl: string;
  onClosingHourChange: (hour: number) => void;
  onWriteupHourChange: (hour: number) => void;
  onTicketUrlChange: (url: string) => void;
  onSave: () => void;
}

/** Formulaire des réglages PoS (extrait du composant pour rester lisible). */
function PosSettingsForm({
  isLoading,
  isDirty,
  isSaving,
  saved,
  error,
  closingHour,
  writeupHour,
  ticketUrl,
  onClosingHourChange,
  onWriteupHourChange,
  onTicketUrlChange,
  onSave,
}: PosSettingsFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="h-5 w-5" /> Sessions de caisse
        </CardTitle>
        <CardDescription>
          Les heures définies ici sont recopiées sur chaque nouvelle session de
          caisse ouverte.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="pos-closing-hour">
              Heure de clôture automatique
            </Label>
            <select
              id="pos-closing-hour"
              className={SELECT_CLASS}
              value={closingHour}
              disabled={isLoading}
              onChange={(e) => onClosingHourChange(Number(e.target.value))}
            >
              {HOURS.map((hour) => (
                <option key={hour} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500">
              Passé cette heure, la session de caisse encore ouverte est
              clôturée automatiquement (tâche planifiée horaire).
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="pos-writeup-hour">
              Heure d&apos;écriture comptable
            </Label>
            <select
              id="pos-writeup-hour"
              className={SELECT_CLASS}
              value={writeupHour}
              disabled={isLoading}
              onChange={(e) => onWriteupHourChange(Number(e.target.value))}
            >
              {HOURS.map((hour) => (
                <option key={hour} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500">
              Heure-valeur retenue pour l&apos;écriture comptable des ventes
              comptoir.
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="pos-ticket-url" className="flex items-center gap-2">
            <QrCode className="h-4 w-4" /> URL du QR code des tickets
          </Label>
          <Input
            id="pos-ticket-url"
            type="url"
            placeholder="https://mon-entreprise.com"
            value={ticketUrl}
            disabled={isLoading}
            onChange={(e) => onTicketUrlChange(e.target.value)}
          />
          <p className="text-xs text-gray-500">
            Adresse encodée dans le QR code imprimé au bas des tickets de caisse
            (site web, page de contact, avis client…).
          </p>
        </div>

        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          <Button onClick={onSave} disabled={!isDirty || isSaving}>
            <Save className="h-4 w-4" />
            {isSaving ? "Enregistrement…" : "Enregistrer"}
          </Button>
          {saved && !isDirty && (
            <span className="flex items-center gap-1 text-sm text-green-700">
              <Check className="h-4 w-4" /> Réglages enregistrés
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
