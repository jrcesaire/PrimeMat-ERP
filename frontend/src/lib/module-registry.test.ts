import { partitionAppTiles, type LauncherModuleState } from "./module-registry";

const CORE_AND_PAYROLL: LauncherModuleState[] = [
  { name: "core", status: "active", is_active: true },
  { name: "payroll", status: "active", is_active: true },
];

describe("partitionAppTiles — tuile Paie", () => {
  it("affiche Paie quand le module est actif et la permission accordée", () => {
    const result = partitionAppTiles(
      CORE_AND_PAYROLL,
      (app) => !app.permission || app.permission === "payslip:view",
    );
    expect(result.active.map((app) => app.key)).toContain("payroll");
    expect(result.disabled.map((app) => app.key)).not.toContain("payroll");
  });

  it("ne masque pas Paie comme une simple tuile désactivée si le droit manque", () => {
    const result = partitionAppTiles(CORE_AND_PAYROLL, () => false);
    expect(result.active.map((app) => app.key)).not.toContain("payroll");
    expect(result.disabled.map((app) => app.key)).not.toContain("payroll");
  });

  it("propose Paie dans les applications à activer si le module est inactif", () => {
    const result = partitionAppTiles(
      [
        CORE_AND_PAYROLL[0],
        { name: "payroll", status: "installed", is_active: false },
      ],
      () => true,
    );
    expect(result.active.map((app) => app.key)).not.toContain("payroll");
    expect(result.disabled.map((app) => app.key)).toContain("payroll");
  });

  it("n'invente pas de tuile à activer tant que la ligne module est absente", () => {
    const result = partitionAppTiles([CORE_AND_PAYROLL[0]], () => true);
    expect(result.active.map((app) => app.key)).not.toContain("payroll");
    expect(result.disabled.map((app) => app.key)).not.toContain("payroll");
  });

  it("conserve la tuile permanente si aucun module métier n'est renseigné", () => {
    const result = partitionAppTiles([], (app) => !app.permission);
    expect(result.active.map((app) => app.key)).toContain("dashboard");
    expect(result.active.map((app) => app.key)).not.toContain("payroll");
    expect(result.disabled).toEqual([]);
  });
});
