import { apiClient } from "@/api/http";
import type { Paginated, ProductListItem } from "@/features/catalog/api";

const BASE = "/api/v1/favorites";

export const favoritesApi = {
  list: (page = 1) =>
    apiClient<Paginated<ProductListItem>>({ url: `${BASE}/`, method: "GET", params: { page } }),
  add: (productId: string) => apiClient<void>({ url: `${BASE}/${productId}/`, method: "PUT" }),
  remove: (productId: string) => apiClient<void>({ url: `${BASE}/${productId}/`, method: "DELETE" }),
};
