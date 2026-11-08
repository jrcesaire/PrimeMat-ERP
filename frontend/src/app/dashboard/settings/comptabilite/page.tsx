/**
 * `/dashboard/settings/comptabilite` — redirige vers le premier réglage du
 * groupe (mêmes conventions que `/dashboard/settings` → « Général »).
 */
import { redirect } from "next/navigation";

export default function SettingsAccountingIndexPage() {
  return redirect("/dashboard/settings/comptabilite/parametres");
}
