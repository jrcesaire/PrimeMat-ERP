import { asNomenclatureMap } from "./useNomenclature";

const VALID = {
  quote: {
    prefix: "DEV",
    padding: 6,
    reset: "year",
    suffix_type: "none",
    suffix_custom: "",
  },
} as const;

describe("asNomenclatureMap", () => {
  it("conserve un objet JSON valide et ses règles personnalisées", () => {
    expect(asNomenclatureMap(VALID)).toEqual(VALID);
    expect(asNomenclatureMap({ custom: VALID.quote })).toEqual({
      custom: VALID.quote,
    });
  });

  it.each([1, 2])("décode une chaîne JSON encodée %i fois", (times) => {
    let raw: unknown = VALID;
    for (let index = 0; index < times; index += 1) {
      raw = JSON.stringify(raw);
    }
    expect(asNomenclatureMap(raw)).toEqual(VALID);
  });

  it("ignore une map de caractères indexés, même doublement encodée", () => {
    const corrupted = { "0": "{", "1": '"', "2": "0" };
    expect(asNomenclatureMap(corrupted)).toEqual({});
    expect(asNomenclatureMap(JSON.stringify(JSON.stringify(corrupted)))).toEqual(
      {},
    );
  });

  it.each([null, undefined, "", "{cassé", "texte", 42, [], ["quote"]])(
    "retourne un objet vide pour une valeur inexploitable (%j)",
    (value) => {
      expect(asNomenclatureMap(value)).toEqual({});
    },
  );
});
