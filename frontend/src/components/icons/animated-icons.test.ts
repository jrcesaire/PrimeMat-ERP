/**
 * Tests du registre d'icônes animées du lanceur (`animated-icons.ts`).
 *
 * Le registre associe une clé de module à deux fichiers servis depuis `public/`.
 * Les tests vérifient que ces fichiers existent réellement : un renommage ou un
 * oubli de régénération casserait silencieusement la tuile en production (le
 * navigateur afficherait une image vide sans erreur JS).
 */
import fs from "node:fs";
import path from "node:path";

import { ANIMATED_APP_ICONS } from "./animated-icons";

const PUBLIC_DIR = path.join(process.cwd(), "public");

function onDisk(relativePath: string): boolean {
  return fs.existsSync(path.join(PUBLIC_DIR, relativePath));
}

describe("ANIMATED_APP_ICONS", () => {
  const entries = Object.entries(ANIMATED_APP_ICONS);

  it("déclare au moins une icône animée", () => {
    expect(entries.length).toBeGreaterThan(0);
  });

  it.each(entries)(
    "« %s » pointe vers des fichiers présents dans public/",
    (_key, icon) => {
      expect(onDisk(icon.src)).toBe(true);
      expect(onDisk(icon.staticSrc)).toBe(true);
    },
  );

  it("sert une image fixe distincte de l'animation", () => {
    for (const icon of Object.values(ANIMATED_APP_ICONS)) {
      expect(icon.staticSrc).not.toBe(icon.src);
    }
  });

  it("utilise le WebP, nettement plus léger que le GIF d'origine", () => {
    for (const icon of Object.values(ANIMATED_APP_ICONS)) {
      expect(icon.src.endsWith(".webp")).toBe(true);
      expect(icon.staticSrc.endsWith(".webp")).toBe(true);
    }
  });
});
