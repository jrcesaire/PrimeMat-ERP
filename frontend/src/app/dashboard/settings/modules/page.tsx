/**
 * Paramètres — section « Modules » (activation / désactivation des modules).
 * Accès réservé au superadministrateur.
 */
import { SettingsScreen } from "@/components/settings/settings-screen";

export default function SettingsModulesPage() {
  return <SettingsScreen section="modules" />;
}
