import {
  COUNTRIES,
  CURRENCIES,
  countryByCode,
  currencyByCode,
  currencyForCountry,
  currencyLabel,
} from "./countries-currencies";

describe("countries-currencies", () => {
  it("couvre l'essentiel du monde", () => {
    expect(COUNTRIES.length).toBeGreaterThan(200);
    expect(CURRENCIES.length).toBeGreaterThan(140);
  });

  it("n'expose que des codes et des libellés valides", () => {
    for (const country of COUNTRIES) {
      expect(country.code).toMatch(/^[A-Z]{2}$/);
      expect(country.name.trim()).not.toBe("");
    }
    for (const currency of CURRENCIES) {
      expect(currency.code).toMatch(/^[A-Z]{3}$/);
      expect(currency.name.trim()).not.toBe("");
      expect(currency.symbol.trim()).not.toBe("");
      expect(currency.decimals).toBeGreaterThanOrEqual(0);
    }
  });

  it("ne contient aucun doublon de code", () => {
    expect(new Set(COUNTRIES.map((c) => c.code)).size).toBe(COUNTRIES.length);
    expect(new Set(CURRENCIES.map((c) => c.code)).size).toBe(CURRENCIES.length);
  });

  it("ne référence que des devises présentes dans la liste", () => {
    const known = new Set(CURRENCIES.map((c) => c.code));
    const orphans = COUNTRIES.filter(
      (c) => c.currency !== "" && !known.has(c.currency),
    );
    expect(orphans).toEqual([]);
  });

  it("nomme correctement les pays témoins", () => {
    expect(countryByCode("CI")?.name).toContain("Ivoire");
    expect(countryByCode("CI")?.currency).toBe("XOF");
    expect(countryByCode("ES")?.name).toBe("Espagne");
    expect(countryByCode("ES")?.currency).toBe("EUR");
    // Insensible à la casse
    expect(countryByCode("ci")?.code).toBe("CI");
  });

  it("porte les décimales de la norme ISO 4217", () => {
    expect(currencyByCode("XOF")?.decimals).toBe(0);
    expect(currencyByCode("XOF")?.symbol).toContain("CFA");
    expect(currencyByCode("EUR")?.symbol).toBe("€");
    expect(currencyByCode("EUR")?.decimals).toBe(2);
    expect(currencyByCode("JPY")?.decimals).toBe(0);
    expect(currencyByCode("BHD")?.decimals).toBe(3);
  });

  it("déduit la devise ayant cours dans un pays", () => {
    expect(currencyForCountry("CI")?.code).toBe("XOF");
    expect(currencyForCountry("CM")?.code).toBe("XAF");
    expect(currencyForCountry("US")?.code).toBe("USD");
    expect(currencyForCountry("CH")?.code).toBe("CHF");
  });

  it("tolère les valeurs absentes ou inconnues", () => {
    expect(countryByCode("ZZZ")).toBeUndefined();
    expect(countryByCode(null)).toBeUndefined();
    expect(currencyByCode(undefined)).toBeUndefined();
    expect(currencyForCountry("")).toBeUndefined();
    // Le Zimbabwe est bien dans la liste, mais pas « zzz ».
    expect(currencyForCountry("ZZZ")).toBeUndefined();
  });

  it("signale les pays déclarés sans devise", () => {
    // L'Antarctique et les territoires palestiniens : présents en tant que pays,
    // sans devise associée — la déduction doit rester sûre.
    expect(countryByCode("AQ")).toBeDefined();
    expect(currencyForCountry("AQ")).toBeUndefined();
    expect(countryByCode("PS")).toBeDefined();
    expect(currencyForCountry("PS")).toBeUndefined();
  });

  it("compose un libellé lisible pour une liste déroulante", () => {
    expect(currencyLabel("XOF")).toMatch(/\(XOF\)$/);
    expect(currencyLabel("eur")).toContain("(EUR)");
    expect(currencyLabel("EUR")).toContain("Euro");
    // Une devise inconnue reste visible plutôt que d'être masquée.
    expect(currencyLabel("ZZZ")).toBe("ZZZ");
    expect(currencyLabel(null)).toBe("");
  });

  it("retient la devise ayant cours, pas celle de l'extrait de 2019", () => {
    // L'extrait déclaratif a figé des devises remplacées depuis ; le générateur
    // les corrige (voir COUNTRY_CURRENCY_FIXES dans le script de génération).
    expect(countryByCode("BG")?.currency).toBe("EUR");
    expect(countryByCode("HR")?.currency).toBe("EUR");
    expect(countryByCode("CW")?.currency).toBe("XCG");
    expect(countryByCode("SX")?.currency).toBe("XCG");
    expect(countryByCode("SL")?.currency).toBe("SLE");
    expect(countryByCode("ZW")?.currency).toBe("ZWG");
    expect(countryByCode("VE")?.currency).toBe("VES");
    expect(countryByCode("CU")?.currency).toBe("CUP");
    expect(countryByCode("CL")?.currency).toBe("CLP");
    expect(countryByCode("SV")?.currency).toBe("USD");
    expect(countryByCode("VG")?.currency).toBe("USD");
    expect(countryByCode("TL")?.currency).toBe("USD");
  });

  it("n'expose ni devise sans cours ni code hors norme", () => {
    // Remplacements : aucune de ces devises n'a plus de territoire, et aucune
    // ne doit donc être proposée à une installation neuve.
    const obsolete = [
      "ANG", "BGN", "CLF", "CUC", "HRK", "SLL", "SVC", "VEF", "ZWL",
      // Agrégat de la Banque de France et métal précieux, hors ISO 4217.
      "CFA", "XAU",
    ];
    for (const code of obsolete) {
      expect(currencyByCode(code)).toBeUndefined();
    }
    for (const country of COUNTRIES) {
      expect(obsolete).not.toContain(country.currency);
    }
    // Codes internes à la Banque de France, absents de la norme ISO 3166-1.
    expect(countryByCode("XG")).toBeUndefined();
    expect(countryByCode("XZ")).toBeUndefined();
  });

  it("complète les territoires rattachés à la France par l'extrait", () => {
    for (const code of ["GF", "GP", "MQ", "YT", "RE", "PM", "MC"]) {
      expect(countryByCode(code)?.currency).toBe("EUR");
    }
  });

  it("nomme les devises créées après l'extrait", () => {
    expect(currencyByCode("SLE")?.name).toBe("Leone");
    expect(currencyByCode("XCG")?.name).toBe("Florin caribéen");
    expect(currencyByCode("ZWG")?.name).toBe("Zimbabwe Gold");
    // Le bolívar soberano, lui, est libellé par l'extrait lui-même.
    expect(currencyByCode("VES")?.name).toContain("Bolivar");
  });
});
