import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { apiClient } from "@/api/http";
import type { Paginated } from "@/features/catalog/api";

export interface Review {
  id: string;
  rating: number;
  title: string;
  body: string;
  author: string;
  is_verified_purchase: boolean;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export const reviewsApi = {
  list: (product: string) =>
    apiClient<Paginated<Review>>({ url: "/api/v1/reviews/", method: "GET", params: { product } }),
  mine: (product: string) => apiClient<Review>({ url: "/api/v1/reviews/mine/", method: "GET", params: { product } }),
  create: (data: { product_id: string; rating: number; title: string; body: string }) =>
    apiClient<Review>({ url: "/api/v1/reviews/", method: "POST", data }),
};

export function useReviews(productSlug: string) {
  return useQuery({ queryKey: ["reviews", productSlug], queryFn: () => reviewsApi.list(productSlug) });
}

export function useMyReview(productSlug: string, enabled: boolean) {
  return useQuery({
    queryKey: ["reviews", productSlug, "mine"],
    queryFn: async () => {
      try {
        return await reviewsApi.mine(productSlug);
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) return null;
        throw error;
      }
    },
    enabled,
  });
}

export function useCreateReview(productSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reviewsApi.create,
    onSuccess: (review) => queryClient.setQueryData(["reviews", productSlug, "mine"], review),
  });
}
