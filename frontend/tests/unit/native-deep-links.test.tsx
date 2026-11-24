import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import { ordersApi, type OrderDetail } from "@/features/orders";
import { CheckoutSuccessPage, FakePayPage, OrderDetailPage } from "@/routes/OrderPages";
import {
  getNativeFakePaymentPath,
  openCheckoutSuccessLink,
  parseCheckoutSuccessUrl,
  registerDeepLinkListener,
  startCheckoutNavigation,
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
    expect(getNativeFakePaymentPath(`/checkout/fake-pay?order=${orderNumber}`, orderNumber)).toBe(
      `/checkout/fake-pay?order=${orderNumber}`,
    );
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

  it("routes startCheckoutNavigation via window.location.assign on web", async () => {
    mocks.isNativePlatform.mockReturnValue(false);
    const assign = vi.fn();
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, assign },
    });
    const navigate = vi.fn();

    try {
      await startCheckoutNavigation(`http://localhost:5173/checkout/fake-pay?order=${orderNumber}`, orderNumber, navigate);
      expect(assign).toHaveBeenCalledWith(`http://localhost:5173/checkout/fake-pay?order=${orderNumber}`);
      expect(navigate).not.toHaveBeenCalled();
      expect(mocks.openUrl).not.toHaveBeenCalled();
    } finally {
      Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
    }
  });

  it("keeps fake checkout inside the Capacitor WebView on native", async () => {
    const navigate = vi.fn();
    const result = await startCheckoutNavigation(
      `http://localhost:5173/checkout/fake-pay?order=${orderNumber}`,
      orderNumber,
      navigate,
    );

    expect(result).toBe("fake");
    expect(navigate).toHaveBeenCalledWith(`/checkout/fake-pay?order=${orderNumber}`, { replace: true });
    expect(mocks.openUrl).not.toHaveBeenCalled();
  });

  it("opens external checkout URLs via AppLauncher on native", async () => {
    const navigate = vi.fn();
    const result = await startCheckoutNavigation(
      "https://checkout.stripe.com/c/pay/cs_test_123",
      orderNumber,
      navigate,
    );

    expect(result).toBe("external");
    expect(mocks.openUrl).toHaveBeenCalledWith({ url: "https://checkout.stripe.com/c/pay/cs_test_123" });
    expect(navigate).not.toHaveBeenCalled();
  });

  it("dispatches openCheckoutSuccessLink and falls back to router navigation on FakePayPage (native)", async () => {
    vi.spyOn(ordersApi, "get").mockResolvedValue(pendingOrder);
    vi.spyOn(ordersApi, "fakeComplete").mockResolvedValue({ status: "paid" });
    mocks.openUrl.mockRejectedValueOnce(new Error("self-intent suppressed"));

    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/checkout/fake-pay?order=${orderNumber}`]}>
          <Routes>
            <Route path="/checkout/fake-pay" element={<FakePayPage />} />
            <Route path="/checkout/success" element={<div>Success route reached</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: i18n.t("fakePay.success") }));

    expect(ordersApi.fakeComplete).toHaveBeenCalledWith(orderNumber);
    expect(mocks.openUrl).toHaveBeenCalledWith({
      url: `onlywheels://checkout/success?order=${orderNumber}`,
    });
    expect(await screen.findByText("Success route reached")).toBeInTheDocument();
  });

  it("routes OrderDetailPage retry payment in-app on native when FakeProvider is active", async () => {
    vi.spyOn(ordersApi, "get").mockResolvedValue({
      ...pendingOrder,
      reserved_until: "2026-06-15T10:30:00Z",
    });
    vi.spyOn(ordersApi, "pay").mockResolvedValue({
      checkout_url: `http://localhost:5173/checkout/fake-pay?order=${orderNumber}`,
    });

    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/account/orders/${orderNumber}`]}>
          <Routes>
            <Route path="/account/orders/:number" element={<OrderDetailPage />} />
            <Route path="/checkout/fake-pay" element={<div>Bundled fake pay route</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: i18n.t("checkout.pay") }));

    await waitFor(() => {
      expect(screen.getByText("Bundled fake pay route")).toBeInTheDocument();
    });
    expect(mocks.openUrl).not.toHaveBeenCalled();
  });
});
