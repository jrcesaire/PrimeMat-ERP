/**
 * Paramètres — section « Utilisateurs » (comptes, rôles, droits d'accès).
 * Accès réservé aux profils autorisés à gérer les utilisateurs.
 */
import { SettingsScreen } from "@/components/settings/settings-screen";

export default function SettingsUsersPage() {
  return <SettingsScreen section="users" />;
}
