/**
 * Point d'entrée `/dashboard/settings` (cible de l'entrée « Paramètres » de la
 * sidebar) : redirige vers la première section, « Général ».
 */
import { redirect } from "next/navigation";

export default function SettingsIndexPage() {
  return redirect("/dashboard/settings/general");
}
