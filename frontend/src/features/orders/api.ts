import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/api/http";
import type { Paginated, ProductType } from "@/features/catalog/api";

// Mirrors apps/orders/serializers.py.
export type OrderStatus =
  | "pending_payment"
  | "paid"
  | "processing"
  | "shipped"
  | "ready_for_fitting"
  | "completed"
  | "cancelled";
export type DeliveryMethod = "courier" | "garage_fitting";

export interface OrderSummary {
  number: string;
  status: OrderStatus;
  delivery_method: DeliveryMethod;
  total: string;
  currency: string;
  item_count: number;
  created_at: string;
  paid_at: string | null;
  reserved_until: string | null;
  can_pay: boolean;
  can_cancel: boolean;
}

export interface OrderItem {
  id: string;
  product_name: string;
  product_slug: string;
  product_type: ProductType;
  sku: string;
  description: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface OrderDetail extends OrderSummary {
  email: string;
  full_name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  county: string;
  postal_code: string;
  notes: string;
  subtotal: string;
  discount: string;
  shipping: string;
  fitting: string;
  vat: string;
  voucher_code: string;
  items: OrderItem[];
  appointment: {
    garage: { name: string; slug: string; city: string; address: string; phone: string };
    slot_start: string;
    slot_end: string;
    status: "held" | "booked" | "confirmed" | "completed" | "cancelled";
  } | null;
  status_changes: { status: OrderStatus; note: string; created_at: string }[];
}

const BASE = "/api/v1/orders";

export const ordersApi = {
  list: (page = 1) => apiClient<Paginated<OrderSummary>>({ url: `${BASE}/`, method: "GET", params: { page } }),
  get: (number: string) => apiClient<OrderDetail>({ url: `${BASE}/${number}/`, method: "GET" }),
  pay: (number: string) => apiClient<{ checkout_url: string }>({ url: `${BASE}/${number}/pay/`, method: "POST" }),
  cancel: (number: string) => apiClient<OrderDetail>({ url: `${BASE}/${number}/cancel/`, method: "POST" }),
  fakeComplete: (number: string) =>
    apiClient<{ status: OrderStatus }>({
      url: "/api/v1/payments/fake/complete/",
      method: "POST",
      data: { order_number: number },
    }),
};

export const orderKeys = {
  list: (page: number) => ["orders", "list", page] as const,
  detail: (number: string) => ["orders", "detail", number] as const,
};

export function useOrders(page = 1) {
  return useQuery({ queryKey: orderKeys.list(page), queryFn: () => ordersApi.list(page) });
}

/** `pollWhilePending` keeps refreshing while the payment webhook has not arrived yet. */
export function useOrder(number: string, { pollWhilePending = false } = {}) {
  return useQuery({
    queryKey: orderKeys.detail(number),
    queryFn: () => ordersApi.get(number),
    refetchInterval: (query) =>
      pollWhilePending && query.state.data?.status === "pending_payment" ? 2000 : false,
  });
}

/** Starts the online payment and sends the browser to the payment page. */
export function usePayOrder() {
  return useMutation({
    mutationFn: ordersApi.pay,
    onSuccess: ({ checkout_url }) => window.location.assign(checkout_url),
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ordersApi.cancel,
    onSuccess: (order) => {
      queryClient.setQueryData(orderKeys.detail(order.number), order);
      return queryClient.invalidateQueries({ queryKey: ["orders", "list"] });
    },
  });
}
