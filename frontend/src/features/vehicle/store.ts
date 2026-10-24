import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ActiveVehicle {
  id: string;
  label: string;
}

interface VehicleState {
  active: ActiveVehicle | null;
  setActive: (vehicle: ActiveVehicle) => void;
  clear: () => void;
}

/** The car the customer is shopping for. Persisted so it survives reloads (also for guests). */
export const useVehicleStore = create<VehicleState>()(
  persist(
    (set) => ({
      active: null,
      setActive: (active) => set({ active }),
      clear: () => set({ active: null }),
    }),
    { name: "ow-active-vehicle" },
  ),
);
