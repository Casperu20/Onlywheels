import { describe, expect, it } from "vitest";

import { SPOKE_OPTIONS, wheelSpec } from "@/features/showroom3d/procedural";

describe("wheelSpec", () => {
  it("sizes the generic wheel from the variant in metres", () => {
    const spec = wheelSpec({ diameterIn: 18, widthIn: "8.0", pcd: "5x112", seed: "bbs-ch-r" });
    expect(spec.rimRadius).toBeCloseTo(0.2286, 4);
    expect(spec.rimWidth).toBeCloseTo(0.2032, 4);
    expect(spec.lugs).toBe(5);
    expect(spec.lugCircle).toBeCloseTo(0.056, 4);
    expect(spec.tireOuter).toBeGreaterThan(spec.rimRadius + 0.05);
    expect(spec.tireWidth).toBeGreaterThan(spec.rimWidth);
  });

  it("gives larger rims a lower tire profile", () => {
    const small = wheelSpec({ diameterIn: 16, seed: "x" });
    const large = wheelSpec({ diameterIn: 22, seed: "x" });
    expect(large.tireOuter - large.rimRadius).toBeLessThan(small.tireOuter - small.rimRadius);
  });

  it("picks a stable spoke count per product so different wheels look different", () => {
    expect(wheelSpec({ seed: "vossen-hf-5" }).spokes).toBe(wheelSpec({ seed: "vossen-hf-5" }).spokes);
    const counts = new Set(["a", "b", "c", "d", "e", "f", "g", "h"].map((seed) => wheelSpec({ seed }).spokes));
    expect(counts.size).toBeGreaterThan(1);
    for (const count of counts) expect(SPOKE_OPTIONS).toContain(count);
  });

  it("falls back to safe defaults for missing or nonsense sizes", () => {
    const spec = wheelSpec({ diameterIn: null, widthIn: "abc", pcd: "", seed: "" });
    expect(spec).toMatchObject(wheelSpec({ diameterIn: 18, widthIn: 8, pcd: "5x112", seed: "" }));
    expect(wheelSpec({ diameterIn: 99, widthIn: 40, pcd: "12x400", seed: "" })).toMatchObject({
      rimRadius: (24 * 0.0254) / 2,
      rimWidth: 13 * 0.0254,
      lugs: 5,
    });
    expect(wheelSpec({ pcd: "4X100", seed: "" })).toMatchObject({ lugs: 4, lugCircle: 0.05 });
  });
});
