import type { Finish } from "@/features/catalog/api";

export interface FinishMaterial {
  color: string;
  metalness: number;
  roughness: number;
}

type MaterialConfig = Record<string, { color?: unknown; metalness?: unknown; roughness?: unknown }>;

export const DEFAULT_MATERIALS: Record<Finish, FinishMaterial> = {
  silver: { color: "#c9ccd1", metalness: 0.9, roughness: 0.25 },
  black: { color: "#1d1f22", metalness: 0.6, roughness: 0.35 },
  bronze: { color: "#8c6a43", metalness: 0.85, roughness: 0.3 },
  gunmetal: { color: "#4a4f55", metalness: 0.8, roughness: 0.3 },
  chrome: { color: "#e8eaed", metalness: 1, roughness: 0.05 },
  white: { color: "#f2f2f2", metalness: 0.2, roughness: 0.3 },
};

const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

const unit = (value: unknown, fallback: number) =>
  typeof value === "number" && Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : fallback;

/** Admin-entered `finish_materials` may be missing, partial or wrong: fall back per field. */
export function finishMaterial(materials: MaterialConfig | null | undefined, finish: string): FinishMaterial {
  const base = DEFAULT_MATERIALS[finish as Finish] ?? DEFAULT_MATERIALS.silver;
  const custom = materials?.[finish];
  return {
    color: typeof custom?.color === "string" && HEX_COLOR.test(custom.color) ? custom.color : base.color,
    metalness: unit(custom?.metalness, base.metalness),
    roughness: unit(custom?.roughness, base.roughness),
  };
}
