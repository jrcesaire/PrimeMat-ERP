/**
 * Tests du modèle de navigation (`src/lib/nav-config.ts`).
 *
 * Verrouille notamment l'absence de doublons : deux entrées de sous-menu ne
 * doivent jamais pointer vers la même route (un doublon « Nouvelle demande »
 * / « Demandes » existait sur `/dashboard/purchases/demandes`).
 */
import {
  ACCOUNTING_STATEMENTS,
  ACCOUNTING_STATEMENT_HREFS,
  accountingStatementFromPath,
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

describe("états financiers de la comptabilité", () => {
  const accounting = NAV_ITEMS.find(
    (item) => item.href === "/dashboard/accounting",
  );
  const accountingLeaves = leavesOf(accounting?.children ?? []);

  it("déclare les quatre états financiers dans l'ordre de l'écran", () => {
    expect(ACCOUNTING_STATEMENTS.map((statement) => statement.key)).toEqual([
      "balance",
      "income",
      "sheet",
      "entries",
    ]);
  });

  it("vise la route de module correspondante, et une seule", () => {
    for (const statement of ACCOUNTING_STATEMENTS) {
      expect(statement.href).toBe(`/dashboard/accounting/${statement.key}`);
    }
  });

  it("décrit des routes qui existent bien dans le sous-menu du module", () => {
    // C'est cette correspondance qui permet à `ModuleNav` de retirer les quatre
    // onglets de sa barre de chips : une route qui n'y figure pas laisserait un
    // doublon (ou une entrée fantôme).
    const hrefs = accountingLeaves.map((leaf) => leaf.href);
    for (const statement of ACCOUNTING_STATEMENTS) {
      expect(hrefs).toContain(statement.href);
    }
    expect(ACCOUNTING_STATEMENT_HREFS).toEqual(
      ACCOUNTING_STATEMENTS.map((statement) => statement.href),
    );
  });

  it("déduit l'onglet actif de l'URL, la racine ouvrant la balance", () => {
    expect(accountingStatementFromPath("/dashboard/accounting")).toBe("balance");
    expect(accountingStatementFromPath("/dashboard/accounting/sheet")).toBe(
      "sheet",
    );
    expect(accountingStatementFromPath("/dashboard/accounting/entries/")).toBe(
      "entries",
    );
    // Une page du module qui n'est pas un état financier retombe sur la balance.
    expect(accountingStatementFromPath("/dashboard/accounting/vat")).toBe(
      "balance",
    );
    expect(accountingStatementFromPath(null)).toBe("balance");
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
describe("réglages métier sortis du module Comptabilité", () => {
  const accounting = NAV_ITEMS.find(
    (item) => item.href === "/dashboard/accounting",
  );
  const accountingLeaves = leavesOf(accounting?.children ?? []);

  it("n'expose plus l'assistant ni les paramètres comptables", () => {
    // Ces deux écrans ont rejoint `/dashboard/settings` (rail Paramètres →
    // groupe Comptabilité) : les garder ici recréerait un doublon de route.
    const hrefs = accountingLeaves.map((leaf) => leaf.href);
    expect(hrefs).not.toContain("/dashboard/accounting/setup");
    expect(hrefs).not.toContain("/dashboard/accounting/settings");
  });

  it("ne référence ces deux routes nulle part dans la navigation", () => {
    const allHrefs = NAV_ITEMS.flatMap((item) => [
      item.href,
      ...leavesOf(item.children ?? []).map((leaf) => leaf.href),
    ]);
    expect(allHrefs).not.toContain("/dashboard/accounting/setup");
    expect(allHrefs).not.toContain("/dashboard/accounting/settings");
  });

  it("conserve les autres pages du module Comptabilité", () => {
    const hrefs = accountingLeaves.map((leaf) => leaf.href);
    expect(hrefs).toContain("/dashboard/accounting/vat");
    expect(hrefs).toContain("/dashboard/accounting/fiscal-year");
    expect(hrefs).toContain("/dashboard/accounting/audit");
  });
});

