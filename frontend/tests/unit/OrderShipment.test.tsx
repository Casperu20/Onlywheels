import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { OrderShipment } from "@/features/orders";
import { OrderDetailPage } from "@/routes/OrderPages";

const state = vi.hoisted(() => ({
  shipment: null as OrderShipment | null,
}));

vi.mock("@/features/orders", () => ({
  OrderStatusBadge: () => null,
  TotalsTable: () => null,
  useCancelOrder: () => ({ isPending: false, mutate: vi.fn() }),
  useDownloadInvoice: () => ({ isPending: false, mutate: vi.fn() }),
  useOrder: () => ({
    data: {
      number: "OWTEST-2",
      status: "shipped",
      delivery_method: "courier",
      total: "100.00",
      currency: "RON",
      item_count: 1,
      created_at: "2026-01-01T12:00:00Z",
      paid_at: "2026-01-01T12:00:00Z",
      reserved_until: null,
      can_pay: false,
      can_cancel: false,
      email: "customer@example.test",
      full_name: "Customer",
      phone: "0712345678",
      line1: "Example street 1",
      line2: "",
      city: "Cluj-Napoca",
      county: "Cluj",
      postal_code: "400000",
      notes: "",
      subtotal: "100.00",
      discount: "0.00",
      shipping: "0.00",
      fitting: "0.00",
      vat: "17.36",
      voucher_code: "",
      items: [],
      appointment: null,
      status_changes: [],
      invoice: null,
      shipment: state.shipment,
    },
    isPending: false,
    isError: false,
  }),
  usePayOrder: () => ({ isPending: false, mutate: vi.fn() }),
}));

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/account/orders/OWTEST-2"]}>
      <Routes>
        <Route path="/account/orders/:number" element={<OrderDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("OrderDetailPage shipment", () => {
  it("shows the carrier, AWB, status and an external tracking link", () => {
    state.shipment = {
      carrier: "sameday",
      carrier_display: "Sameday",
      awb: "1ONB123",
      tracking_url: "https://track.example/1ONB123",
      status: "in_transit",
    };
    renderPage();

    expect(screen.getByRole("heading", { name: "Livrare prin curier" })).toBeInTheDocument();
    expect(screen.getByText(/Sameday · AWB 1ONB123/)).toBeInTheDocument();
    expect(screen.getByText("În tranzit")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Urmărește coletul" });
    expect(link).toHaveAttribute("href", "https://track.example/1ONB123");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("hides the tracking block when there is no shipment", () => {
    state.shipment = null;
    renderPage();
    expect(screen.queryByRole("heading", { name: "Livrare prin curier" })).not.toBeInTheDocument();
  });

  it("omits the link when the carrier gave no tracking URL", () => {
    state.shipment = {
      carrier: "fan_courier",
      carrier_display: "Fan Courier",
      awb: "2400000123",
      tracking_url: "",
      status: "created",
    };
    renderPage();
    expect(screen.getByText(/AWB 2400000123/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Urmărește coletul" })).not.toBeInTheDocument();
  });
});
