import { apiClient } from "@/api/http";
import type { ProductType, Variant } from "@/features/catalog/api";

// Mirrors apps/cart/serializers.py.
export interface CartProduct {
  id: string;
  slug: string;
  name: string;
  type: ProductType;
  brand: string;
}

export interface ServerCartItem {
  id: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  available: number;
  product: CartProduct;
  variant: Variant;
}

export interface ServerCart {
  items: ServerCartItem[];
  subtotal: string;
  item_count: number;
}

const BASE = "/api/v1/cart";

export const cartApi = {
  get: () => apiClient<ServerCart>({ url: `${BASE}/`, method: "GET" }),
  add: (variantId: string, quantity: number) =>
    apiClient<ServerCart>({ url: `${BASE}/items/`, method: "POST", data: { variant_id: variantId, quantity } }),
  update: (itemId: string, quantity: number) =>
    apiClient<ServerCart>({ url: `${BASE}/items/${itemId}/`, method: "PATCH", data: { quantity } }),
  remove: (itemId: string) => apiClient<ServerCart>({ url: `${BASE}/items/${itemId}/`, method: "DELETE" }),
  clear: () => apiClient<ServerCart>({ url: `${BASE}/`, method: "DELETE" }),
  merge: (items: { variant_id: string; quantity: number }[]) =>
    apiClient<ServerCart>({ url: `${BASE}/merge/`, method: "POST", data: { items } }),
};
