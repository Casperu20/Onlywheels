import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { catalogApi } from "./api";

export const catalogKeys = {
  products: (params: Record<string, string>) => ["catalog", "products", params] as const,
  product: (slug: string, vehicle?: string) => ["catalog", "product", slug, vehicle ?? null] as const,
  brands: ["catalog", "brands"] as const,
};

export function useProducts(params: Record<string, string>) {
  return useQuery({
    queryKey: catalogKeys.products(params),
    queryFn: () => catalogApi.products(params),
    placeholderData: keepPreviousData,
  });
}

export function useProduct(slug: string, vehicle?: string) {
  return useQuery({
    queryKey: catalogKeys.product(slug, vehicle),
    queryFn: () => catalogApi.product(slug, vehicle),
  });
}

export function useBrands() {
  return useQuery({ queryKey: catalogKeys.brands, queryFn: catalogApi.brands, staleTime: 30 * 60_000 });
}
