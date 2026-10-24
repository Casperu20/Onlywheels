import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { favoritesApi } from "./api";

export const favoritesKey = ["favorites"] as const;

export function useFavorites(page = 1) {
  return useQuery({ queryKey: [...favoritesKey, page], queryFn: () => favoritesApi.list(page) });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, favorite }: { productId: string; favorite: boolean }) =>
      favorite ? favoritesApi.add(productId) : favoritesApi.remove(productId),
    // Awaited, so the caller's onSettled runs after fresh data is in the cache.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["catalog"] }),
        queryClient.invalidateQueries({ queryKey: favoritesKey }),
      ]),
  });
}
