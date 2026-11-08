import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OrderDetailPage } from "@/routes/OrderPages";

const { order, downloadInvoice } = vi.hoisted(() => ({
  order: {
    number: "OWTEST-1",
    status: "paid",
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
    invoice: {
      status: "issued",
      series: "TEST",
      number: "1001",
      issued_at: "2026-01-01T12:00:00Z",
      total: "100.00",
      efactura_status: "not_sent",
      pdf_url: "/api/v1/invoices/OWTEST-1/pdf/",
      is_demo: false,
    },
  },
  downloadInvoice: vi.fn(),
}));

vi.mock("@/features/orders", () => ({
  OrderStatusBadge: () => null,
  TotalsTable: () => null,
  useCancelOrder: () => ({ isPending: false, mutate: vi.fn() }),
  useDownloadInvoice: () => ({ isPending: false, mutate: downloadInvoice }),
  useOrder: () => ({ data: order, isPending: false, isError: false }),
  usePayOrder: () => ({ isPending: false, mutate: vi.fn() }),
}));

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/account/orders/OWTEST-1"]}>
      <Routes>
        <Route path="/account/orders/:number" element={<OrderDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("OrderDetailPage invoice", () => {
  beforeEach(() => {
    downloadInvoice.mockReset();
    order.invoice.is_demo = false;
  });

  it("explains that a demo invoice is not a fiscal document", () => {
    order.invoice.is_demo = true;
    renderPage();

    expect(screen.getByText(/API-ul oficial SmartBill este dezactivat/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descarcă factura (PDF)" })).toBeInTheDocument();
  });

  it("does not show the demo note for a real invoice", () => {
    renderPage();

    expect(screen.queryByText(/API-ul oficial SmartBill este dezactivat/)).not.toBeInTheDocument();
  });

  it("offers the issued PDF and starts its download", async () => {
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Descarcă factura (PDF)" }));

    expect(screen.getByText("TEST-1001")).toBeInTheDocument();
    expect(downloadInvoice).toHaveBeenCalledWith(
      "OWTEST-1",
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });
});
