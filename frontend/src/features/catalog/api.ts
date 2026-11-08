import type {
  BadgeEnum,
  Brand,
  BrandMini,
  FinishEnum,
  FitmentResult,
  ProductTypeEnum,
  SeasonEnum,
  WheelStyleEnum,
} from "@/api/generated/model";
import {
  FinishEnum as FinishValues,
  ProductTypeEnum as ProductTypeValues,
} from "@/api/generated/model";
import { apiClient } from "@/api/http";

export type ProductType = ProductTypeEnum;
export type Finish = FinishEnum;
export type Season = SeasonEnum;
export type WheelStyle = WheelStyleEnum;
export type Badge = BadgeEnum;
export type { Brand, BrandMini, FitmentResult };

export const PRODUCT_TYPES: ProductType[] = Object.values(ProductTypeValues);
export const FINISHES: Finish[] = Object.values(FinishValues);

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

export interface ProductListItem {
  id: string;
  slug: string;
  type: ProductType;
  name: string;
  brand: BrandMini;
  style: WheelStyle | "";
  badge: Badge | "";
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
  media: { id: string; image: string; alt: string; credit: string; credit_url: string }[];
  variants: Variant[];
  /** Phase 2 3D showroom; null until a GLB is uploaded in admin */
  model_3d: {
    glb_file: string;
    thumbnail: string | null;
    finish_materials: Record<string, { color?: string; metalness?: number; roughness?: number }>;
  } | null;
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
