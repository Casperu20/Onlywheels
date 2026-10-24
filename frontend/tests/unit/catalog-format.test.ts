import type { Variant } from "@/features/catalog/api";
import { defaultQuantity, variantSummary } from "@/features/catalog/format";

const base: Variant = {
  id: "1",
  sku: "SKU",
  label: "",
  price: "1000.00",
  old_price: null,
  finish: "silver",
  diameter_in: 19,
  width_in: "8.5",
  et_mm: 35,
  pcd: "5x112",
  center_bore_mm: "66.6",
  tire_size: "",
  tire_width_mm: null,
  tire_aspect: null,
  load_index: null,
  speed_rating: "",
  season: "",
  thread_size: "",
  available: 4,
  fitment: null,
};

describe("variantSummary", () => {
  it("formats wheels", () => {
    expect(variantSummary(base, "wheel")).toBe('19" · 8.5J · 5×112 · ET35');
    expect(variantSummary({ ...base, width_in: "8.0" }, "wheel")).toBe('19" · 8J · 5×112 · ET35');
  });

  it("formats tires", () => {
    const tire = { ...base, tire_size: "225/45 R18", load_index: 95, speed_rating: "Y" };
    expect(variantSummary(tire, "tire")).toBe("225/45 R18 95Y");
  });

  it("formats sets with the tire size", () => {
    expect(variantSummary({ ...base, tire_size: "225/40 R19" }, "set")).toBe(
      '19" · 8.5J · 5×112 · ET35 · 225/40 R19',
    );
  });

  it("uses the label for accessories", () => {
    expect(variantSummary({ ...base, label: "20 buc · M14×1.5" }, "accessory")).toBe("20 buc · M14×1.5");
  });
});

describe("defaultQuantity", () => {
  it("defaults to a set of 4 for wheels and tires", () => {
    expect(defaultQuantity("wheel")).toBe(4);
    expect(defaultQuantity("tire")).toBe(4);
    expect(defaultQuantity("set")).toBe(1);
  });
});
