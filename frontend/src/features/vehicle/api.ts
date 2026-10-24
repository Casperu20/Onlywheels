import { apiClient } from "@/api/http";

// Hand-written until the orval client is generated; mirrors apps/vehicles/serializers.py.
export interface Make {
  id: string;
  name: string;
  slug: string;
}

export interface VehicleModel {
  id: string;
  name: string;
  slug: string;
  make: string;
}

export interface FitmentSpec {
  pcd: string;
  center_bore_mm: string;
  et_min: number;
  et_max: number;
  diameter_min: number;
  diameter_max: number;
  width_min: string;
  width_max: string;
  thread_size: string;
  tire_sizes: string[];
}

export interface Generation {
  id: string;
  name: string;
  year_from: number;
  year_to: number | null;
  make: Make;
  model: VehicleModel;
  has_fitment: boolean;
}

export interface GenerationDetail extends Generation {
  fitment: FitmentSpec | null;
}

export interface UserVehicle {
  id: string;
  generation: Generation;
  nickname: string;
  is_default: boolean;
  created_at: string;
}

const BASE = "/api/v1/vehicles";

export const vehicleApi = {
  makes: () => apiClient<Make[]>({ url: `${BASE}/makes/`, method: "GET" }),
  models: (make: string) =>
    apiClient<VehicleModel[]>({ url: `${BASE}/models/`, method: "GET", params: { make } }),
  generations: (model: string) =>
    apiClient<Generation[]>({ url: `${BASE}/generations/`, method: "GET", params: { model } }),
  generation: (id: string) =>
    apiClient<GenerationDetail>({ url: `${BASE}/generations/${id}/`, method: "GET" }),
  myVehicles: () => apiClient<UserVehicle[]>({ url: `${BASE}/my/`, method: "GET" }),
  addMyVehicle: (data: { generation_id: string; nickname?: string; is_default?: boolean }) =>
    apiClient<UserVehicle>({ url: `${BASE}/my/`, method: "POST", data }),
  removeMyVehicle: (id: string) => apiClient<void>({ url: `${BASE}/my/${id}/`, method: "DELETE" }),
};
