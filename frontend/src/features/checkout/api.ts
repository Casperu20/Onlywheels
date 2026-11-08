import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/http";
import type { DeliveryMethod, OrderDetail, PaymentMethod } from "@/features/orders";

export interface Quote {
  subtotal: string;
  discount: string;
  shipping: string;
  fitting: string;
  total: string;
  vat: string;
  voucher_code: string | null;
}

export interface QuoteRequest {
  delivery_method: DeliveryMethod;
  garage_id?: string;
  voucher_code?: string;
}

export interface CheckoutRequest extends QuoteRequest {
  payment_method?: PaymentMethod;
  email: string;
  full_name: string;
  phone: string;
  line1: string;
  line2?: string;
  city: string;
  county: string;
  postal_code: string;
  notes?: string;
  slot_start?: string;
  accept_terms: boolean;
}

export interface Address {
  id: string;
  full_name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  county: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export const checkoutApi = {
  preview: (data: QuoteRequest) =>
    apiClient<Quote>({ url: "/api/v1/checkout/preview/", method: "POST", data }),
  createOrder: (data: CheckoutRequest) =>
    apiClient<OrderDetail>({ url: "/api/v1/orders/", method: "POST", data }),
  addresses: () => apiClient<Address[]>({ url: "/api/v1/accounts/addresses/", method: "GET" }),
  saveAddress: (data: Omit<Address, "id" | "country">) =>
    apiClient<Address>({ url: "/api/v1/accounts/addresses/", method: "POST", data }),
  updateAddress: ({ id, ...data }: Partial<Address> & { id: string }) =>
    apiClient<Address>({ url: `/api/v1/accounts/addresses/${id}/`, method: "PATCH", data }),
  deleteAddress: (id: string) =>
    apiClient<void>({ url: `/api/v1/accounts/addresses/${id}/`, method: "DELETE" }),
};

export function useQuote(request: QuoteRequest, enabled: boolean) {
  return useQuery({
    queryKey: ["checkout", "quote", request],
    queryFn: () => checkoutApi.preview(request),
    enabled,
    retry: false,
  });
}

export function useAddresses() {
  return useQuery({ queryKey: ["addresses"], queryFn: checkoutApi.addresses });
}
