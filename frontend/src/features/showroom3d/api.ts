import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/http";

import type { CarViewModel } from "./carGeometry";

export type CarBodyType = "hatchback" | "sedan" | "wagon" | "suv" | "coupe";

export interface CarModel extends CarViewModel {
  id: string;
  slug: string;
  body_type: CarBodyType;
  vehicle_model: { id: string; name: string; make: string } | null;
}

const carModelApi = {
  list: () => apiClient<CarModel[]>({ url: "/api/v1/catalog/car-models/", method: "GET" }),
};

export function useCarModels() {
  return useQuery({
    queryKey: ["catalog", "car-models"],
    queryFn: carModelApi.list,
    staleTime: 60 * 60_000,
  });
}
