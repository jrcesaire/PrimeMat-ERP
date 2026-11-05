/**
 * Tests du modèle de navigation (`src/lib/nav-config.ts`).
 *
 * Verrouille notamment l'absence de doublons : deux entrées de sous-menu ne
 * doivent jamais pointer vers la même route (un doublon « Nouvelle demande »
 * / « Demandes » existait sur `/dashboard/purchases/demandes`).
 */
import {
  filterNavChildren,
  isNavGroup,
  NAV_ITEMS,
  NAV_SECTIONS,
  visibleNavModules,
  type NavChild,
} from "./nav-config";

/** Toutes les feuilles d'une liste d'enfants, groupes dépliés. */
function leavesOf(children: NavChild[]): { label: string; href: string }[] {
  return children.flatMap((child) =>
    isNavGroup(child) ? child.items : [child],
  );
}

const allowAll = () => true;

describe("NAV_ITEMS", () => {
  it("n'a aucun doublon de route entre les entrées principales", () => {
    const hrefs = NAV_ITEMS.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("n'a aucun doublon de route dans les sous-menus d'un même module", () => {
    for (const item of NAV_ITEMS) {
      const leaves = leavesOf(item.children ?? []);
      const hrefs = leaves.map((leaf) => leaf.href);
      expect({ module: item.label, hrefs }).toEqual({
        module: item.label,
        hrefs: [...new Set(hrefs)],
      });
    }
  });

  it("n'a aucun doublon de libellé dans les sous-menus d'un même module", () => {
    for (const item of NAV_ITEMS) {
      const leaves = leavesOf(item.children ?? []);
      const labels = leaves.map((leaf) => leaf.label);
      expect({ module: item.label, labels }).toEqual({
        module: item.label,
        labels: [...new Set(labels)],
      });
    }
  });

  it("expose l'entrée « Point de vente » (mode immersif du PoS)", () => {
    const pos = NAV_ITEMS.find((item) => item.href === "/dashboard/sales/pos");
    expect(pos).toBeDefined();
    expect(pos?.permission).toBe("pos:view");
  });

  it("expose les modules de la phase 2 comptable", () => {
    const hrefs = NAV_ITEMS.map((item) => item.href);
    expect(hrefs).toContain("/dashboard/treasury");
    expect(hrefs).toContain("/dashboard/accounting");
  });

  it("pointe vers des routes absolues du dashboard", () => {
    for (const item of NAV_ITEMS) {
      expect(item.href.startsWith("/dashboard")).toBe(true);
      for (const leaf of leavesOf(item.children ?? [])) {
        expect(leaf.href.startsWith("/dashboard")).toBe(true);
      }
    }
  });
});

describe("NAV_SECTIONS", () => {
  it("déclare les trois sections de la maquette, dans l'ordre", () => {
    expect(NAV_SECTIONS.map((section) => section.key)).toEqual([
      "workspace",
      "commercial",
      "finance",
    ]);
  });

  it("n'affecte chaque module qu'à une section déclarée", () => {
    const declared = new Set(NAV_SECTIONS.map((section) => section.key));
    for (const item of NAV_ITEMS) {
      if (item.section) {
        expect(declared.has(item.section)).toBe(true);
      }
    }
  });

  it("range les modules dans la section attendue", () => {
    const sectionOf = (label: string) =>
      NAV_ITEMS.find((item) => item.label === label)?.section;
    expect(sectionOf("Tableau de bord")).toBe("workspace");
    expect(sectionOf("Point de vente")).toBe("workspace");
    expect(sectionOf("Ventes")).toBe("commercial");
    expect(sectionOf("Achats")).toBe("commercial");
    expect(sectionOf("Livraison")).toBe("commercial");
    expect(sectionOf("Facturation")).toBe("finance");
    expect(sectionOf("Comptabilité")).toBe("finance");
    expect(sectionOf("Trésorerie")).toBe("finance");
  });

  it("laisse Reporting et Paramètres hors section (affichés à part)", () => {
    expect(
      NAV_ITEMS.find((item) => item.label === "Reporting")?.section,
    ).toBeUndefined();
    expect(
      NAV_ITEMS.find((item) => item.label === "Paramètres")?.section,
    ).toBeUndefined();
  });
});

describe("filterNavChildren", () => {
  const children: NavChild[] = [
    { label: "Demandes", href: "/a", permission: "purchase_request:view" },
    { label: "Besoins", href: "/b", permission: "product:view" },
    {
      label: "Autres",
      items: [{ label: "Caché", href: "/c", permission: "admin:view" }],
    },
  ];

  it("conserve les feuilles autorisées et retire les autres", () => {
    const filtered = filterNavChildren(
      children,
      (permission) => permission === "purchase_request:view",
    );
    expect(filtered).toHaveLength(1);
    expect(isNavGroup(filtered[0])).toBe(false);
    expect((filtered[0] as { href: string }).href).toBe("/a");
  });

  it("supprime les groupes devenus vides", () => {
    const filtered = filterNavChildren(children, allowAll);
    expect(filtered).toHaveLength(3);
    const emptyGroup = filterNavChildren(
      children,
      (permission) => permission !== "admin:view",
    );
    expect(emptyGroup).toHaveLength(2);
    expect(emptyGroup.every((child) => !isNavGroup(child))).toBe(true);
  });

  it("transmet `undefined` au prédicat pour une feuille sans permission", () => {
    const filtered = filterNavChildren(
      [{ label: "Libre", href: "/libre" }],
      (permission) => permission === undefined,
    );
    expect(filtered).toHaveLength(1);
  });

  it("retire une feuille sans permission si le prédicat la refuse", () => {
    const filtered = filterNavChildren(
      [{ label: "Libre", href: "/libre" }],
      () => false,
    );
    expect(filtered).toHaveLength(0);
  });
});

describe("visibleNavModules", () => {
  it("masque un module dont la page et le sous-menu sont interdits", () => {
    const modules = visibleNavModules(() => false);
    expect(modules).toHaveLength(0);
  });

  it("affiche un module autorisé avec ses sous-menus filtrés", () => {
    const modules = visibleNavModules(
      (permission) => permission === "pos:view",
    );
    const labels = modules.map(({ item }) => item.label);
    expect(labels).toContain("Point de vente");
    expect(labels).not.toContain("Comptabilité");
  });

  it("conserve un module interdit qui garde une page accessible", () => {
    // Le vendeur n'a pas `purchase:view` mais voit « Besoins (ventes) »
    // (permission `order:view`) : le module « Achats » reste affiché.
    const modules = visibleNavModules(
      (permission) => permission === "order:view",
    );
    const achats = modules.find(({ item }) => item.label === "Achats");
    expect(achats).toBeDefined();
    expect(achats?.children.length).toBeGreaterThan(0);
    expect(achats?.children).toEqual([
      {
        label: "Besoins (ventes)",
        href: "/dashboard/purchases/besoins",
        permission: "order:view",
      },
    ]);
  });

  it("injecte les sections du module Paramètres", () => {
    const modules = visibleNavModules(allowAll, [
      { label: "Général", href: "/dashboard/settings/general" },
    ]);
    const settings = modules.find(
      ({ item }) => item.href === "/dashboard/settings",
    );
    expect(settings?.children).toEqual([
      { label: "Général", href: "/dashboard/settings/general" },
    ]);
  });
});
