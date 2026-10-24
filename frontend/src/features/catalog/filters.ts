import { FINISHES, PRODUCT_TYPES, type Finish, type ProductType } from "./api";

export const SORT_OPTIONS = ["", "price", "-price", "-newest", "-rating"] as const;
export type SortOption = (typeof SORT_OPTIONS)[number];

/** Catalog state. The URL query string is the source of truth (shareable, back button works). */
export interface ProductFilters {
  type?: ProductType;
  brand: string[];
  diameter: number[];
  finish: Finish[];
  search: string;
  price_min?: number;
  price_max?: number;
  in_stock: boolean;
  vehicle?: string;
  ordering: SortOption;
  page: number;
}

const list = (value: string | null) =>
  (value ?? "")
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);

const positiveNumber = (value: string | null) => {
  const n = Number(value);
  return value && Number.isFinite(n) && n >= 0 ? n : undefined;
};

export function parseFilters(params: URLSearchParams): ProductFilters {
  const type = params.get("type");
  const ordering = params.get("ordering") ?? "";
  const page = Number(params.get("page"));

  return {
    type: PRODUCT_TYPES.includes(type as ProductType) ? (type as ProductType) : undefined,
    brand: list(params.get("brand")),
    diameter: list(params.get("diameter"))
      .map(Number)
      .filter((n) => Number.isInteger(n) && n > 0),
    finish: list(params.get("finish")).filter((f): f is Finish => FINISHES.includes(f as Finish)),
    search: params.get("search") ?? "",
    price_min: positiveNumber(params.get("price_min")),
    price_max: positiveNumber(params.get("price_max")),
    in_stock: params.get("in_stock") === "true",
    vehicle: params.get("vehicle") || undefined,
    ordering: (SORT_OPTIONS as readonly string[]).includes(ordering) ? (ordering as SortOption) : "",
    page: Number.isInteger(page) && page > 1 ? page : 1,
  };
}

/** Same keys for the browser URL and the API request; defaults are omitted. */
export function filtersToParams(filters: ProductFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.type) params.type = filters.type;
  if (filters.brand.length) params.brand = filters.brand.join(",");
  if (filters.diameter.length) params.diameter = filters.diameter.join(",");
  if (filters.finish.length) params.finish = filters.finish.join(",");
  if (filters.search.trim()) params.search = filters.search.trim();
  if (filters.price_min !== undefined) params.price_min = String(filters.price_min);
  if (filters.price_max !== undefined) params.price_max = String(filters.price_max);
  if (filters.in_stock) params.in_stock = "true";
  if (filters.vehicle) params.vehicle = filters.vehicle;
  if (filters.ordering) params.ordering = filters.ordering;
  if (filters.page > 1) params.page = String(filters.page);
  return params;
}

export function toggleValue<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}
