import { describe, expect, it } from "vitest";

import { wheelSpec } from "@/features/showroom3d/procedural";
import {
  fitCarToLength,
  frontDirection,
  wheelModelScale,
  wheelMounts,
} from "@/features/showroom3d/carGeometry";

const bounds = {
  min: { x: -2, y: -0.5, z: -0.9 },
  max: { x: 2, y: 1, z: 0.9 },
};

const anchors = {
  axis: "x" as const,
  wheels: [
    { x: -1.2, y: 0.3, z: -0.7 },
    { x: -1.2, y: 0.3, z: 0.7 },
    { x: 1.2, y: 0.3, z: -0.7 },
    { x: 1.2, y: 0.3, z: 0.7 },
  ],
};

describe("car showroom geometry", () => {
  it("scales a car to its real length and grounds and centres it", () => {
    expect(fitCarToLength(bounds, 4.2, "x")).toEqual({
      scale: 1.05,
      offset: { x: 0, y: 0.525, z: 0 },
      lengthAxis: "x",
    });
  });

  it("uses the Z dimension when Z is the car length axis", () => {
    const transform = fitCarToLength(bounds, 3.6, "z");
    expect(transform.scale).toBe(2);
    expect(transform.offset).toEqual({ x: 0, y: 1, z: 0 });
    expect(transform.lengthAxis).toBe("z");
  });

  it("places four wheels at scaled anchors and faces each wheel outward", () => {
    const transform = fitCarToLength(bounds, 4.2, "x");
    const mounts = wheelMounts(anchors, transform);

    expect(mounts).toHaveLength(4);
    expect(mounts[0]).toEqual({
      position: { x: -1.26, y: 0.84, z: -0.735 },
      rotationY: Math.PI,
    });
    expect(mounts[1].rotationY).toBe(0);
    expect(mounts[2].rotationY).toBe(Math.PI);
    expect(mounts[3].rotationY).toBe(0);
  });

  it("faces wheels outward when the GLB anchors are offset from the origin", () => {
    const offsetAnchors = {
      ...anchors,
      wheels: anchors.wheels.map((wheel) => ({ ...wheel, z: wheel.z + 2.5 })),
    };
    const offsetBounds = {
      min: { ...bounds.min, z: bounds.min.z + 2.5 },
      max: { ...bounds.max, z: bounds.max.z + 2.5 },
    };
    const transform = fitCarToLength(offsetBounds, 4.2, "x");

    expect(wheelMounts(offsetAnchors, transform).map((mount) => mount.rotationY)).toEqual([
      Math.PI,
      0,
      Math.PI,
      0,
    ]);
  });

  it.each([
    ["+x", { x: 1, y: 0, z: 0 }],
    ["-x", { x: -1, y: 0, z: 0 }],
    ["+z", { x: 0, y: 0, z: 1 }],
    ["-z", { x: 0, y: 0, z: -1 }],
  ] as const)("maps front direction %s", (front, expected) => {
    expect(frontDirection(front)).toEqual(expected);
  });

  it("rotates the wheel axle when the car length axis is Z", () => {
    const transform = fitCarToLength(bounds, 4.2, "z");
    const mounts = wheelMounts(
      { axis: "z", wheels: anchors.wheels.map((wheel) => ({ ...wheel, x: wheel.z, z: wheel.x })) },
      transform,
    );

    expect(mounts.map((mount) => mount.rotationY)).toEqual([
      -Math.PI / 2,
      Math.PI / 2,
      -Math.PI / 2,
      Math.PI / 2,
    ]);
  });

  it("scales uploaded wheels by the selected tyre outer diameter", () => {
    const wheelBounds = { min: { x: -0.5, y: -0.5, z: -0.1 }, max: { x: 0.5, y: 0.5, z: 0.1 } };
    const size17 = wheelSpec({ diameterIn: 17, seed: "wheel" });
    const size19 = wheelSpec({ diameterIn: 19, seed: "wheel" });

    expect(wheelModelScale(wheelBounds, size17)).toBeCloseTo(2 * size17.tireOuter);
    expect(wheelModelScale(wheelBounds, size19) / wheelModelScale(wheelBounds, size17)).toBeCloseTo(
      size19.tireOuter / size17.tireOuter,
    );
  });
});
