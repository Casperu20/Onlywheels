import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/http";

// Mirrors apps/garages/serializers.py.
export interface Garage {
  id: string;
  slug: string;
  name: string;
  city: string;
  county: string;
  address: string;
  phone: string;
  description: string;
  latitude: string | null;
  longitude: string | null;
  opens_at: string;
  closes_at: string;
  working_days: number[];
  fitting_price: string;
}

export interface Slot {
  start: string;
  end: string;
}

export const garagesApi = {
  list: () => apiClient<Garage[]>({ url: "/api/v1/garages/", method: "GET" }),
  slots: (slug: string, date: string) =>
    apiClient<Slot[]>({ url: `/api/v1/garages/${slug}/slots/`, method: "GET", params: { date } }),
};

export function useGarages() {
  return useQuery({ queryKey: ["garages"], queryFn: garagesApi.list, staleTime: 10 * 60_000 });
}

export function useSlots(slug: string | undefined, date: string) {
  return useQuery({
    queryKey: ["garages", slug, "slots", date],
    queryFn: () => garagesApi.slots(slug!, date),
    enabled: Boolean(slug && date),
  });
}

/** "YYYY-MM-DD" in local time, `offsetDays` from today. */
export function isoDate(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
