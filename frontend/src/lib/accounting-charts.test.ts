import {
  CHART_OPTIONS,
  DEFAULT_CHART,
  chartLabel,
  chartOption,
  isChartOfAccounts,
} from "./accounting-charts";

describe("accounting-charts", () => {
  it("propose exactement les deux référentiels OHADA", () => {
    expect(CHART_OPTIONS.map((option) => option.value)).toEqual([
      "SYSCOHADA",
      "SYCEBNL",
    ]);
  });

  it("décrit chaque référentiel pour l'interface", () => {
    for (const option of CHART_OPTIONS) {
      expect(option.label).toBeTruthy();
      expect(option.summary).toBeTruthy();
      expect(option.highlights.length).toBeGreaterThan(0);
    }
  });

  it("applique le plan commercial par défaut", () => {
    expect(DEFAULT_CHART).toBe("SYSCOHADA");
    expect(chartLabel(undefined)).toBe("SYSCOHADA");
    expect(chartLabel(null)).toBe("SYSCOHADA");
    expect(chartLabel("plan-inconnu")).toBe("SYSCOHADA");
  });

  it("nomme les référentiels gérés", () => {
    expect(chartLabel("SYCEBNL")).toBe("SYCEBNL");
    expect(chartLabel("SYSCOHADA")).toBe("SYSCOHADA");
  });

  it("reconnaît une valeur servie par l'API", () => {
    expect(isChartOfAccounts("SYCEBNL")).toBe(true);
    expect(isChartOfAccounts("SYSCOHADA")).toBe(true);
    expect(isChartOfAccounts("PLAN-INEXISTANT")).toBe(false);
    expect(isChartOfAccounts(undefined)).toBe(false);
    expect(isChartOfAccounts(null)).toBe(false);
  });

  it("retrouve une option par sa valeur", () => {
    expect(chartOption("SYCEBNL")?.label).toBe("SYCEBNL");
    expect(chartOption("inconnu")).toBeUndefined();
  });
});
