import { filtersToParams, parseFilters, toggleValue } from "@/features/catalog/filters";

describe("parseFilters", () => {
  it("returns defaults for an empty query", () => {
    expect(parseFilters(new URLSearchParams())).toEqual({
      type: undefined,
      brand: [],
      diameter: [],
      finish: [],
      search: "",
      price_min: undefined,
      price_max: undefined,
      in_stock: false,
      vehicle: undefined,
      ordering: "",
      page: 1,
    });
  });

  it("parses lists and ignores invalid values", () => {
    const filters = parseFilters(
      new URLSearchParams("type=wheel&brand=bbs,oz-racing&diameter=18,abc,19&finish=black,purple&ordering=-price&page=3"),
    );
    expect(filters.type).toBe("wheel");
    expect(filters.brand).toEqual(["bbs", "oz-racing"]);
    expect(filters.diameter).toEqual([18, 19]);
    expect(filters.finish).toEqual(["black"]);
    expect(filters.ordering).toBe("-price");
    expect(filters.page).toBe(3);
  });

  it("rejects unknown type and ordering", () => {
    const filters = parseFilters(new URLSearchParams("type=boat&ordering=drop table"));
    expect(filters.type).toBeUndefined();
    expect(filters.ordering).toBe("");
  });
});

describe("filtersToParams", () => {
  it("round-trips through the URL and omits defaults", () => {
    const query = "type=tire&brand=michelin&diameter=18&in_stock=true&vehicle=abc&page=2";
    const params = filtersToParams(parseFilters(new URLSearchParams(query)));
    expect(params).toEqual({
      type: "tire",
      brand: "michelin",
      diameter: "18",
      in_stock: "true",
      vehicle: "abc",
      page: "2",
    });
  });
});

describe("toggleValue", () => {
  it("adds and removes", () => {
    expect(toggleValue([1, 2], 3)).toEqual([1, 2, 3]);
    expect(toggleValue([1, 2], 2)).toEqual([1]);
  });
});
