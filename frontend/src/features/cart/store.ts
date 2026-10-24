import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Variant } from "@/features/catalog/api";

import type { CartProduct } from "./api";

export const MAX_QUANTITY = 20;

/** Snapshot of what a guest added, so the cart can be shown without calling the API. */
export interface GuestLine {
  variantId: string;
  quantity: number;
  product: CartProduct;
  variant: Variant;
}

interface GuestCartState {
  lines: GuestLine[];
  add: (line: GuestLine) => void;
  setQuantity: (variantId: string, quantity: number) => void;
  remove: (variantId: string) => void;
  clear: () => void;
}

const clamp = (quantity: number) => Math.max(1, Math.min(MAX_QUANTITY, quantity));

export const useGuestCart = create<GuestCartState>()(
  persist(
    (set) => ({
      lines: [],
      add: (line) =>
        set((state) => {
          const existing = state.lines.find((l) => l.variantId === line.variantId);
          if (!existing) return { lines: [...state.lines, { ...line, quantity: clamp(line.quantity) }] };
          return {
            lines: state.lines.map((l) =>
              l.variantId === line.variantId ? { ...l, quantity: clamp(l.quantity + line.quantity) } : l,
            ),
          };
        }),
      setQuantity: (variantId, quantity) =>
        set((state) => ({
          lines: state.lines.map((l) => (l.variantId === variantId ? { ...l, quantity: clamp(quantity) } : l)),
        })),
      remove: (variantId) => set((state) => ({ lines: state.lines.filter((l) => l.variantId !== variantId) })),
      clear: () => set({ lines: [] }),
    }),
    { name: "ow-guest-cart" },
  ),
);
