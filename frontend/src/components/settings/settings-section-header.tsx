/**
 * En-tête d'une section de Paramètres.
 *
 * Mêmes proportions que l'en-tête de `SettingsScreen` (titre 28 px + phrase de
 * contexte) pour que les sections historiques et les sections rattachées à un
 * module se ressemblent.
 */
export function SettingsSectionHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div>
      <h1 className="text-[28px] font-semibold leading-tight text-ink">{title}</h1>
      {description && <p className="mt-1 text-[13px] text-muted">{description}</p>}
    </div>
  );
}
