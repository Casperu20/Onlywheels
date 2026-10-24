import { apiClient } from "@/api/http";

// Hand-written until the orval client is generated; mirrors apps/catalog/serializers.py.
export type ProductType = "wheel" | "tire" | "set" | "accessory";
export type Finish = "silver" | "black" | "bronze" | "gunmetal" | "chrome" | "white";
export type Season = "summer" | "winter" | "all_season";

export const PRODUCT_TYPES: ProductType[] = ["wheel", "tire", "set", "accessory"];
export const FINISHES: Finish[] = ["silver", "black", "bronze", "gunmetal", "chrome", "white"];

export interface FitmentResult {
  fits: boolean;
  needs_hub_rings: boolean;
  issues: string[];
}

export interface Variant {
  id: string;
  sku: string;
  label: string;
  price: string;
  old_price: string | null;
  finish: Finish | "";
  diameter_in: number | null;
  width_in: string | null;
  et_mm: number | null;
  pcd: string;
  center_bore_mm: string | null;
  tire_size: string;
  tire_width_mm: number | null;
  tire_aspect: number | null;
  load_index: number | null;
  speed_rating: string;
  season: Season | "";
  thread_size: string;
  available: number;
  fitment: FitmentResult | null;
}

export interface BrandMini {
  name: string;
  slug: string;
}

export interface Brand extends BrandMini {
  id: string;
  logo: string | null;
}

export interface ProductListItem {
  id: string;
  slug: string;
  type: ProductType;
  name: string;
  brand: BrandMini;
  style: string;
  badge: string;
  rating_avg: string;
  rating_count: number;
  min_price: string;
  old_price: string | null;
  in_stock: boolean;
  is_favorite: boolean;
  image: string | null;
  finishes: Finish[];
  diameters: number[];
  cheapest_variant: Variant | null;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  category: { id: string; name: string; slug: string; product_type: ProductType } | null;
  media: { id: string; image: string; alt: string }[];
  variants: Variant[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const BASE = "/api/v1/catalog";

export const catalogApi = {
  products: (params: Record<string, string>) =>
    apiClient<Paginated<ProductListItem>>({ url: `${BASE}/products/`, method: "GET", params }),
  product: (slug: string, vehicle?: string) =>
    apiClient<ProductDetail>({
      url: `${BASE}/products/${encodeURIComponent(slug)}/`,
      method: "GET",
      params: vehicle ? { vehicle } : undefined,
    }),
  brands: () => apiClient<Brand[]>({ url: `${BASE}/brands/`, method: "GET" }),
};
