import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useMe } from "@/features/auth";
import type { Variant } from "@/features/catalog/api";

import { cartApi, type CartProduct, type ServerCart } from "./api";
import { useGuestCart, type GuestLine } from "./store";

export const cartKey = ["cart"] as const;

/** One shape for both the server cart (logged in) and the browser cart (guest). */
export interface CartLine {
  key: string;
  itemId?: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
  available: number;
  product: CartProduct;
  variant: Variant;
}

export interface CartView {
  lines: CartLine[];
  subtotal: number;
  count: number;
  isGuest: boolean;
  isLoading: boolean;
}

export function fromServer(cart: ServerCart): CartLine[] {
  return cart.items.map((item) => ({
    key: item.id,
    itemId: item.id,
    quantity: item.quantity,
    unitPrice: Number(item.unit_price),
    lineTotal: Number(item.line_total),
    available: item.available,
    product: item.product,
    variant: item.variant,
  }));
}

export function fromGuest(lines: GuestLine[]): CartLine[] {
  return lines.map((line) => ({
    key: line.variantId,
    quantity: line.quantity,
    unitPrice: Number(line.variant.price),
    lineTotal: Number(line.variant.price) * line.quantity,
    available: line.variant.available,
    product: line.product,
    variant: line.variant,
  }));
}

export function summarize(lines: CartLine[]) {
  return {
    subtotal: lines.reduce((sum, l) => sum + l.lineTotal, 0),
    count: lines.reduce((sum, l) => sum + l.quantity, 0),
  };
}

export function useCart(): CartView {
  const { data: user, isPending: authPending } = useMe();
  const guestLines = useGuestCart((s) => s.lines);
  const server = useQuery({ queryKey: cartKey, queryFn: cartApi.get, enabled: Boolean(user) });

  const lines = user ? (server.data ? fromServer(server.data) : []) : fromGuest(guestLines);
  return {
    lines,
    ...summarize(lines),
    isGuest: !user,
    isLoading: authPending || (Boolean(user) && server.isPending),
  };
}

export function useCartActions() {
  const { data: user } = useMe();
  const queryClient = useQueryClient();
  const guest = useGuestCart();
  const onServerCart = (cart: ServerCart) => queryClient.setQueryData(cartKey, cart);

  const add = useMutation({
    mutationFn: async (line: GuestLine) => {
      if (!user) {
        guest.add(line);
        return;
      }
      onServerCart(await cartApi.add(line.variantId, line.quantity));
    },
  });

  const setQuantity = useMutation({
    mutationFn: async ({ line, quantity }: { line: CartLine; quantity: number }) => {
      if (!user || !line.itemId) {
        guest.setQuantity(line.key, quantity);
        return;
      }
      onServerCart(await cartApi.update(line.itemId, quantity));
    },
  });

  const remove = useMutation({
    mutationFn: async (line: CartLine) => {
      if (!user || !line.itemId) {
        guest.remove(line.key);
        return;
      }
      onServerCart(await cartApi.remove(line.itemId));
    },
  });

  return { add, setQuantity, remove };
}

/** After login, move the guest's browser cart into the server cart (once). */
export function useCartSync() {
  const { data: user } = useMe();
  const queryClient = useQueryClient();
  const { lines, clear } = useGuestCart();
  const syncing = useRef(false);

  useEffect(() => {
    if (!user || lines.length === 0 || syncing.current) return;
    syncing.current = true;
    cartApi
      .merge(lines.map((l) => ({ variant_id: l.variantId, quantity: l.quantity })))
      .then((cart) => {
        queryClient.setQueryData(cartKey, cart);
        clear();
      })
      .catch(() => undefined)
      .finally(() => {
        syncing.current = false;
      });
  }, [user, lines, clear, queryClient]);
}
