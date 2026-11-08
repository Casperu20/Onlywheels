import type { WheelSpec } from "./procedural";

export type CarAxis = "x" | "z";
export type CarFront = "+x" | "-x" | "+z" | "-z";

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Bounds3 {
  min: Vector3;
  max: Vector3;
}

export interface WheelAnchors {
  axis: CarAxis;
  wheels: Vector3[];
}

export interface CarViewModel {
  name: string;
  glb_file: string;
  length_m: number | string;
  front: CarFront;
  wheel_anchors: WheelAnchors;
  attribution: string;
  source_url: string;
}

export interface CarTransform {
  scale: number;
  offset: Vector3;
  lengthAxis: CarAxis;
}

export interface WheelMount {
  position: Vector3;
  rotationY: number;
}

const COMPONENTS = ["x", "y", "z"] as const;

export function fitCarToLength(bounds: Bounds3, lengthM: number, axis: CarAxis): CarTransform {
  const spans = COMPONENTS.map((component) => bounds.max[component] - bounds.min[component]);
  const lengthIndex = axis === "x" ? 0 : 2;
  const sourceLength = spans[lengthIndex];
  if (!Number.isFinite(sourceLength) || sourceLength <= 0 || !Number.isFinite(lengthM) || lengthM <= 0) {
    throw new RangeError("Car model bounds and real length must be positive finite values.");
  }

  const scale = lengthM / sourceLength;
  return {
    scale,
    offset: {
      x: round(-((bounds.min.x + bounds.max.x) / 2) * scale),
      y: round(-bounds.min.y * scale),
      z: round(-((bounds.min.z + bounds.max.z) / 2) * scale),
    },
    lengthAxis: axis,
  };
}

export function wheelMounts(anchors: WheelAnchors, transform: CarTransform): WheelMount[] {
  if (anchors.wheels.length !== 4) {
    throw new RangeError("A car model requires exactly four wheel anchors.");
  }
  const sideAxis = anchors.axis === "x" ? "z" : "x";
  return anchors.wheels.map((wheel) => {
    const side = wheel[sideAxis] * transform.scale + transform.offset[sideAxis];
    const rotationY =
      anchors.axis === "x"
        ? side < 0
          ? Math.PI
          : 0
        : side < 0
          ? -Math.PI / 2
          : Math.PI / 2;
    return {
      position: {
        x: round(wheel.x * transform.scale + transform.offset.x),
        y: round(wheel.y * transform.scale + transform.offset.y),
        z: round(wheel.z * transform.scale + transform.offset.z),
      },
      rotationY,
    };
  });
}

export function wheelModelScale(wheelBounds: Bounds3, spec: WheelSpec): number {
  const diameter = Math.max(
    wheelBounds.max.x - wheelBounds.min.x,
    wheelBounds.max.y - wheelBounds.min.y,
  );
  if (!Number.isFinite(diameter) || diameter <= 0 || !Number.isFinite(spec.tireOuter) || spec.tireOuter <= 0) {
    throw new RangeError("Wheel GLB radial bounds and tyre radius must be positive finite values.");
  }
  return (2 * spec.tireOuter) / diameter;
}

export function frontDirection(front: CarFront): Vector3 {
  switch (front) {
    case "+x":
      return { x: 1, y: 0, z: 0 };
    case "-x":
      return { x: -1, y: 0, z: 0 };
    case "+z":
      return { x: 0, y: 0, z: 1 };
    case "-z":
      return { x: 0, y: 0, z: -1 };
  }
}

function round(value: number): number {
  const rounded = Math.round(value * 1_000_000) / 1_000_000;
  return Object.is(rounded, -0) ? 0 : rounded;
}
