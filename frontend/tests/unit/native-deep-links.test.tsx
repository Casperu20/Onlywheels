import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import { ordersApi, type OrderDetail } from "@/features/orders";
import { CheckoutSuccessPage } from "@/routes/OrderPages";
import {
  getNativeFakePaymentPath,
  openCheckoutSuccessLink,
  parseCheckoutSuccessUrl,
  registerDeepLinkListener,
} from "@/lib/native/deep-links";

const mocks = vi.hoisted(() => ({
  isNativePlatform: vi.fn(),
  addListener: vi.fn(),
  getLaunchUrl: vi.fn(),
  openUrl: vi.fn(),
}));

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: mocks.isNativePlatform },
}));

vi.mock("@capacitor/app", () => ({
  App: { addListener: mocks.addListener, getLaunchUrl: mocks.getLaunchUrl },
}));

vi.mock("@capacitor/app-launcher", () => ({
  AppLauncher: { openUrl: mocks.openUrl },
}));

const orderNumber = "OW260615-ABC123";
let openListener: ((event: { url: string }) => void) | undefined;
let removeListener: ReturnType<typeof vi.fn>;

const pendingOrder: OrderDetail = {
  number: orderNumber,
  status: "pending_payment",
  delivery_method: "courier",
  payment_method: "card_online",
  total: "120.00",
  currency: "RON",
  item_count: 1,
  created_at: "2026-06-15T10:00:00Z",
  paid_at: null,
  reserved_until: null,
  can_pay: true,
  can_cancel: true,
  email: "customer@example.com",
  full_name: "Ana Pop",
  phone: "0700000000",
  line1: "Main Street 1",
  line2: "",
  city: "Bucharest",
  county: "Bucharest",
  postal_code: "010101",
  notes: "",
  subtotal: "120.00",
  discount: "0.00",
  shipping: "0.00",
  fitting: "0.00",
  vat: "19.16",
  voucher_code: "",
  items: [],
  appointment: null,
  status_changes: [],
  invoice: null,
  shipment: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.isNativePlatform.mockReturnValue(true);
  openListener = undefined;
  removeListener = vi.fn().mockResolvedValue(undefined);
  mocks.addListener.mockImplementation(async (_event, listener) => {
    openListener = listener;
    return { remove: removeListener };
  });
  mocks.getLaunchUrl.mockResolvedValue(undefined);
  mocks.openUrl.mockResolvedValue({ completed: true });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("native checkout deep links", () => {
  it("accepts only a well-formed checkout success link and maps it to the app route", () => {
    expect(parseCheckoutSuccessUrl(`onlywheels://checkout/success?order=${orderNumber}`)).toBe(
      `/checkout/success?order=${orderNumber}`,
    );
  });

  it.each([
    `https://checkout/success?order=${orderNumber}`,
    `onlywheels://orders/success?order=${orderNumber}`,
    `onlywheels://checkout/fake-pay?order=${orderNumber}`,
    "onlywheels://checkout/success",
    `onlywheels://checkout/success?order=${orderNumber}&order=OW260616-DEF456`,
    "onlywheels://checkout/success?order=invalid%20order",
  ])("rejects an unrelated or invalid link: %s", (url) => {
    expect(parseCheckoutSuccessUrl(url)).toBeNull();
  });

  it("handles both cold-start launch URLs and warm appUrlOpen events", async () => {
    const navigate = vi.fn();
    mocks.getLaunchUrl.mockResolvedValue({ url: `onlywheels://checkout/success?order=${orderNumber}` });

    const remove = await registerDeepLinkListener(navigate);

    expect(navigate).toHaveBeenCalledWith(`/checkout/success?order=${orderNumber}`);
    openListener?.({ url: "https://unrelated.example/" });
    openListener?.({ url: `onlywheels://checkout/success?order=${orderNumber}` });
    expect(navigate).toHaveBeenCalledTimes(2);
    remove();
    expect(removeListener).toHaveBeenCalledOnce();
  });

  it("routes fake checkout into the bundled page only for the matching order", () => {
    expect(
      getNativeFakePaymentPath(`https://shop.example/checkout/fake-pay?order=${orderNumber}`, orderNumber),
    ).toBe(`/checkout/fake-pay?order=${orderNumber}`);
    expect(getNativeFakePaymentPath("https://pay.example/session/123", orderNumber)).toBeNull();
    expect(() =>
      getNativeFakePaymentPath("https://shop.example/checkout/fake-pay?order=OW260616-DEF456", orderNumber),
    ).toThrow();
  });

  it("opens a validated custom-scheme return link through App Launcher", async () => {
    await openCheckoutSuccessLink(orderNumber);

    expect(mocks.openUrl).toHaveBeenCalledWith({
      url: `onlywheels://checkout/success?order=${orderNumber}`,
    });
  });

  it("renders the backend order state instead of inferring payment from the link", async () => {
    vi.spyOn(ordersApi, "get").mockResolvedValue(pendingOrder);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/checkout/success?order=${orderNumber}`]}>
          <Routes>
            <Route path="/checkout/success" element={<CheckoutSuccessPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText(i18n.t("checkout.waitingTitle"))).toBeInTheDocument();
    expect(screen.queryByText(i18n.t("checkout.successTitle"))).not.toBeInTheDocument();
    expect(ordersApi.get).toHaveBeenCalledWith(orderNumber);
  });
});
