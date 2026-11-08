import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { http } from "@/api/http";
import type { Paginated } from "@/features/catalog/api";

// Mirrors apps/ai_studio/serializers.py.
export type GenerationStatus = "queued" | "running" | "done" | "failed" | "cancelled";

export interface ChoiceOption {
  value: string;
  label: string;
}

export interface StudioInfo {
  enabled: boolean;
  daily_limit: number;
  remaining_today: number;
  max_upload_bytes: number;
  retention_days: number;
  scenes: ChoiceOption[];
  styles: ChoiceOption[];
}

export interface Generation {
  id: string;
  status: GenerationStatus;
  scene: string;
  style: string;
  variant: string | null;
  variant_name: string | null;
  error: string;
  input_url: string | null;
  result_url: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface NewGeneration {
  image: File;
  scene: string;
  style: string;
  variant?: string | null;
}

const BASE = "/api/v1/ai";

export const aiStudioApi = {
  studio: () => http.get<StudioInfo>(`${BASE}/studio/`).then((r) => r.data),
  list: () => http.get<Paginated<Generation>>(`${BASE}/generations/`).then((r) => r.data.results),
  create: ({ image, scene, style, variant }: NewGeneration) => {
    const form = new FormData();
    form.append("image", image);
    form.append("scene", scene);
    form.append("style", style);
    if (variant) form.append("variant", variant);
    return http.post<Generation>(`${BASE}/generations/`, form).then((r) => r.data);
  },
  remove: (id: string) => http.delete(`${BASE}/generations/${id}/`).then(() => undefined),
  retry: (id: string) => http.post<Generation>(`${BASE}/generations/${id}/retry/`).then((r) => r.data),
  // Images are private: fetched with the session cookie and shown through object URLs.
  image: (url: string) => http.get<Blob>(url, { responseType: "blob" }).then((r) => r.data),
};

const keys = {
  studio: ["ai-studio", "info"] as const,
  generations: ["ai-studio", "generations"] as const,
};

export const isActive = (status: GenerationStatus) => status === "queued" || status === "running";

export function useStudioInfo() {
  return useQuery({ queryKey: keys.studio, queryFn: aiStudioApi.studio });
}

export function useGenerations() {
  return useQuery({
    queryKey: keys.generations,
    queryFn: aiStudioApi.list,
    placeholderData: keepPreviousData,
    // Poll only while something is still being generated.
    refetchInterval: (query) => (query.state.data?.some((g) => isActive(g.status)) ? 2000 : false),
  });
}

function useInvalidateStudio() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: keys.generations });
    void queryClient.invalidateQueries({ queryKey: keys.studio });
  };
}

export function useCreateGeneration() {
  const invalidate = useInvalidateStudio();
  return useMutation({ mutationFn: aiStudioApi.create, onSettled: invalidate });
}

export function useDeleteGeneration() {
  const invalidate = useInvalidateStudio();
  return useMutation({ mutationFn: aiStudioApi.remove, onSettled: invalidate });
}

export function useRetryGeneration() {
  const invalidate = useInvalidateStudio();
  return useMutation({ mutationFn: aiStudioApi.retry, onSettled: invalidate });
}

/** Object URL for a private image; revoked when the URL changes or the component unmounts. */
export function usePrivateImage(url: string | null) {
  const { data: blob, isError } = useQuery({
    queryKey: ["ai-studio", "image", url],
    queryFn: () => aiStudioApi.image(url as string),
    enabled: Boolean(url),
    staleTime: Infinity,
    gcTime: 60_000,
  });
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!blob) {
      setObjectUrl(null);
      return;
    }
    const created = URL.createObjectURL(blob);
    setObjectUrl(created);
    return () => URL.revokeObjectURL(created);
  }, [blob]);
  return { src: objectUrl, isError };
}
