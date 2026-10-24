import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { vehicleApi } from "./api";

const STATIC = 60 * 60_000; // vehicle data changes rarely

export const vehicleKeys = {
  makes: ["vehicles", "makes"] as const,
  models: (make: string) => ["vehicles", "models", make] as const,
  generations: (model: string) => ["vehicles", "generations", model] as const,
  generation: (id: string) => ["vehicles", "generation", id] as const,
  mine: ["vehicles", "mine"] as const,
};

export function useMakes() {
  return useQuery({ queryKey: vehicleKeys.makes, queryFn: vehicleApi.makes, staleTime: STATIC });
}

export function useModels(makeId: string) {
  return useQuery({
    queryKey: vehicleKeys.models(makeId),
    queryFn: () => vehicleApi.models(makeId),
    enabled: Boolean(makeId),
    staleTime: STATIC,
  });
}

export function useGenerations(modelId: string) {
  return useQuery({
    queryKey: vehicleKeys.generations(modelId),
    queryFn: () => vehicleApi.generations(modelId),
    enabled: Boolean(modelId),
    staleTime: STATIC,
  });
}

export function useGeneration(id: string | undefined) {
  return useQuery({
    queryKey: vehicleKeys.generation(id ?? ""),
    queryFn: () => vehicleApi.generation(id!),
    enabled: Boolean(id),
    staleTime: STATIC,
  });
}

export function useMyVehicles(enabled = true) {
  return useQuery({ queryKey: vehicleKeys.mine, queryFn: vehicleApi.myVehicles, enabled });
}

export function useAddMyVehicle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: vehicleApi.addMyVehicle,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vehicleKeys.mine }),
  });
}

export function useRemoveMyVehicle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: vehicleApi.removeMyVehicle,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vehicleKeys.mine }),
  });
}
