import type { ProductType, Variant } from "./api";

/** "8.0" -> "8", "8.5" -> "8.5" */
const trimDecimal = (value: string) => String(Number(value));

/** Short technical line for cards and variant pickers, e.g. 19" · 8.5J · 5×112 · ET35. */
export function variantSummary(variant: Variant, type: ProductType): string {
  if (type === "accessory") return variant.label;

  const tire = [variant.tire_size, variant.load_index ? `${variant.load_index}${variant.speed_rating}` : ""]
    .filter(Boolean)
    .join(" ");
  if (type === "tire") return tire;

  const wheel = [
    variant.diameter_in ? `${variant.diameter_in}"` : "",
    variant.width_in ? `${trimDecimal(variant.width_in)}J` : "",
    variant.pcd.replace("x", "×"),
    variant.et_mm !== null ? `ET${variant.et_mm}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return type === "set" && variant.tire_size ? `${wheel} · ${variant.tire_size}` : wheel;
}

/** Wheels and tires are sold per piece (usually 4), sets and accessories per unit. */
export function defaultQuantity(type: ProductType): number {
  return type === "wheel" || type === "tire" ? 4 : 1;
}
