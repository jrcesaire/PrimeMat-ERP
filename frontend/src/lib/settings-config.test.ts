/**
 * Tests du modèle de navigation des Paramètres (`src/lib/settings-config.ts`).
 *
 * Le rail des Paramètres est la **seule** liste des écrans de paramètres : une
 * entrée fantôme (route déclarée sans page) ou un doublon de route casserait
 * l'écran. Le test verrouille les deux, ainsi que les règles d'affichage par
 * permission, puisqu'un écran de paramètres mal filtré expose des réglages à un
 * profil qui n'a pas les droits.
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { APP_TILES } from "./module-registry";
import {
  isSettingsLinkAllowed,
  SETTINGS_APP_GROUP,
  SETTINGS_GROUP_HREFS,
  SETTINGS_GROUPS,
  SETTINGS_MODULE_GROUPS,
  SETTINGS_MODULE_LINKS,
  type SettingsLink,
} from "./settings-config";

const frontend = join(__dirname, "..", "..");

/** Fichier de page attendu par Next.js pour une route `/dashboard/...`. */
function pageFile(href: string): string {
  return join(frontend, "src", "app", href, "page.tsx");
}

const allLinks: SettingsLink[] = SETTINGS_GROUPS.flatMap((group) => group.links);
/** Icône de référence pour les entrées fabriquées par les tests. */
const anyIcon = SETTINGS_APP_GROUP.links[0].icon;

describe("modèle des paramètres", () => {
  it("liste les réglages transverses puis un groupe par application", () => {
    expect(SETTINGS_GROUPS[0].key).toBe(SETTINGS_APP_GROUP.key);
    expect(SETTINGS_MODULE_GROUPS.map((group) => group.key)).toEqual(
      APP_TILES.filter((tile) => !tile.always).map((tile) => tile.key),
    );
  });

  it("n'a aucun doublon de route", () => {
    const hrefs = allLinks.map((link) => link.href);
    expect(SETTINGS_GROUP_HREFS).toEqual([...new Set(hrefs)]);
    expect(SETTINGS_GROUP_HREFS).toHaveLength(hrefs.length);
  });

  it("vise une page qui existe réellement", () => {
    for (const link of allLinks) {
      expect({ href: link.href, exists: existsSync(pageFile(link.href)) }).toEqual(
        { href: link.href, exists: true },
      );
    }
  });

  it("ne déclare que des routes du dashboard", () => {
    for (const link of allLinks) {
      expect(link.href.startsWith("/dashboard/")).toBe(true);
    }
  });

  it("rattache les réglages métier à une application du lanceur", () => {
    const keys = new Set(SETTINGS_MODULE_GROUPS.map((group) => group.key));
    for (const key of Object.keys(SETTINGS_MODULE_LINKS)) {
      expect(keys.has(key)).toBe(true);
    }
  });

  it("décrit chaque entrée (libellé, phrase d'aide, icône)", () => {
    for (const link of allLinks) {
      expect({ key: link.key, label: link.label.length > 0 }).toEqual({
        key: link.key,
        label: true,
      });
      expect(link.description.length).toBeGreaterThan(0);
      expect(link.icon).toBeDefined();
    }
  });

  it("protège les réglages comptables par les bonnes permissions", () => {
    expect(SETTINGS_MODULE_LINKS.accounting.map((link) => link.permissions)).toEqual([
      ["account:edit"],
      ["account:view"],
    ]);
  });
});

describe("isSettingsLinkAllowed", () => {
  const restricted: SettingsLink = {
    key: "test",
    label: "Test",
    description: "Entrée de test",
    href: "/dashboard/settings/general",
    icon: anyIcon,
    permissions: ["account:view"],
  };

  it("ouvre l'entrée au profil qui détient la permission", () => {
    expect(
      isSettingsLinkAllowed(restricted, {
        isSuperuser: false,
        permissions: ["account:view"],
      }),
    ).toBe(true);
  });

  it("la refuse au profil qui ne l'a pas", () => {
    expect(
      isSettingsLinkAllowed(restricted, { isSuperuser: false, permissions: [] }),
    ).toBe(false);
  });

  it("laisse le superadministrateur tout voir", () => {
    expect(
      isSettingsLinkAllowed(restricted, { isSuperuser: true, permissions: [] }),
    ).toBe(true);
    const modules = SETTINGS_APP_GROUP.links.find(
      (link) => link.superuserOnly === true,
    );
    expect(modules).toBeDefined();
    expect(
      isSettingsLinkAllowed(modules as SettingsLink, {
        isSuperuser: true,
        permissions: [],
      }),
    ).toBe(true);
  });

  it("réserve les entrées superuser aux superadministrateurs", () => {
    const modules = SETTINGS_APP_GROUP.links.find(
      (link) => link.superuserOnly === true,
    );
    expect(
      isSettingsLinkAllowed(modules as SettingsLink, {
        isSuperuser: false,
        permissions: ["user:create", "category:view"],
      }),
    ).toBe(false);
  });

  it("n'exige rien des entrées sans permission déclarée", () => {
    const open: SettingsLink = {
      key: "open",
      label: "Ouvert",
      description: "Entrée sans permission",
      href: "/dashboard/settings/general",
      icon: anyIcon,
    };
    expect(
      isSettingsLinkAllowed(open, { isSuperuser: false, permissions: [] }),
    ).toBe(true);
  });
});
