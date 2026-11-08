import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AppointmentStatusEnum,
  DeliveryMethodEnum,
  OrderItem as GeneratedOrderItem,
  OrderPaymentMethodEnum,
  OrderStatusEnum,
} from "@/api/generated/model";
import { apiClient } from "@/api/http";
import type { Paginated } from "@/features/catalog/api";

// Canonical types derived from the OpenAPI schema (src/api/generated/model).
export type OrderStatus = OrderStatusEnum;
export type DeliveryMethod = DeliveryMethodEnum;
export type PaymentMethod = OrderPaymentMethodEnum;
export type OrderItem = GeneratedOrderItem;

export type InvoiceStatus =
  | "pending"
  | "issuing"
  | "pdf_pending"
  | "issued"
  | "failed"
  | "review_required";

export interface OrderInvoice {
  status: InvoiceStatus;
  series: string;
  number: string;
  issued_at: string | null;
  total: string;
  efactura_status: "not_sent" | "sent" | "validated" | "rejected";
  pdf_url: string | null;
  is_demo: boolean;
}

export type ShipmentStatus = "created" | "picked_up" | "in_transit" | "delivered" | "returned";

export interface OrderShipment {
  carrier: "sameday" | "fan_courier" | "demo";
  carrier_display: string;
  awb: string;
  tracking_url: string;
  status: ShipmentStatus;
}

export interface OrderSummary {
  number: string;
  status: OrderStatus;
  delivery_method: DeliveryMethod;
  payment_method: PaymentMethod;
  total: string;
  currency: string;
  item_count: number;
  created_at: string;
  paid_at: string | null;
  reserved_until: string | null;
  can_pay: boolean;
  can_cancel: boolean;
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
    status: AppointmentStatusEnum;
  } | null;
  status_changes: { status: OrderStatus; note: string; created_at: string }[];
  invoice: OrderInvoice | null;
  shipment: OrderShipment | null;
}

const BASE = "/api/v1/orders";
const INVOICE_BASE = "/api/v1/invoices";

export const ordersApi = {
  list: (page = 1) => apiClient<Paginated<OrderSummary>>({ url: `${BASE}/`, method: "GET", params: { page } }),
  get: (number: string) => apiClient<OrderDetail>({ url: `${BASE}/${number}/`, method: "GET" }),
  pay: (number: string) => apiClient<{ checkout_url: string }>({ url: `${BASE}/${number}/pay/`, method: "POST" }),
  cancel: (number: string) => apiClient<OrderDetail>({ url: `${BASE}/${number}/cancel/`, method: "POST" }),
  downloadInvoice: (number: string) =>
    apiClient<Blob>({
      url: `${INVOICE_BASE}/${number}/pdf/`,
      method: "GET",
      responseType: "blob",
    }),
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

export function useDownloadInvoice() {
  return useMutation({
    mutationFn: ordersApi.downloadInvoice,
    onSuccess: (pdf, orderNumber) => {
      const url = URL.createObjectURL(pdf);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${orderNumber}-invoice.pdf`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
}
