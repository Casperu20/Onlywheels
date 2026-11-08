/** Dimensions (metres) of the code-drawn wheel used when a product has no licensed GLB. No three.js here. */
export interface WheelSpec {
  rimRadius: number;
  rimWidth: number;
  tireOuter: number;
  tireWidth: number;
  spokes: number;
  spokeWidth: number;
  lugs: number;
  lugCircle: number;
}

export interface WheelSize {
  diameterIn?: number | null;
  widthIn?: string | number | null;
  pcd?: string;
}

export const SPOKE_OPTIONS = [5, 6, 7, 9, 10] as const;

const INCH = 0.0254;
const DEFAULTS = { diameter: 18, width: 8, lugs: 5, pcdMm: 112 };

function inRange(value: unknown, min: number, max: number, fallback: number) {
  const number = typeof value === "string" ? Number.parseFloat(value) : Number(value);
  return Number.isFinite(number) && number > 0 ? Math.min(max, Math.max(min, number)) : fallback;
}

/** Stable per-product variety: the same slug always gets the same spoke count. */
function hash(seed: string) {
  let h = 2166136261;
  for (const char of seed) h = Math.imul(h ^ char.charCodeAt(0), 16777619);
  return h >>> 0;
}

export function wheelSpec({ diameterIn, widthIn, pcd, seed }: WheelSize & { seed: string }): WheelSpec {
  const diameter = inRange(diameterIn, 13, 24, DEFAULTS.diameter);
  const width = inRange(widthIn, 5, 13, DEFAULTS.width);
  const match = /^(\d+)x(\d+(?:\.\d+)?)$/i.exec((pcd ?? "").trim());
  const valid = match && Number(match[1]) >= 3 && Number(match[1]) <= 8;
  const lugs = valid ? Number(match[1]) : DEFAULTS.lugs;
  const pcdMm = valid ? inRange(match[2], 90, 210, DEFAULTS.pcdMm) : DEFAULTS.pcdMm;

  const rimRadius = (diameter * INCH) / 2;
  const rimWidth = width * INCH;
  // Bigger rims usually carry lower-profile tires.
  const sidewall = Math.min(0.12, Math.max(0.06, 0.1 - (diameter - 17) * 0.006));
  const spokes = SPOKE_OPTIONS[hash(seed) % SPOKE_OPTIONS.length];

  return {
    rimRadius,
    rimWidth,
    tireOuter: rimRadius + sidewall,
    tireWidth: rimWidth + 0.025,
    spokes,
    spokeWidth: Math.min(0.045, 0.2 / spokes),
    lugs,
    lugCircle: pcdMm / 2000,
  };
}
