import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { Header } from "@/app/layout/Header";
import { meQueryKey } from "@/features/auth";

function renderHeader(user: unknown = null) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
  client.setQueryData(meQueryKey, user);
  client.setQueryData(["cart"], { items: [], subtotal: "0.00", item_count: 0 });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Header />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Header", () => {
  it("shows the main navigation", () => {
    renderHeader();
    const nav = screen.getByRole("navigation", { name: "Navigare principală" });
    expect(nav).toHaveTextContent("Catalog");
    expect(nav).toHaveTextContent("AI Studio");
  });

  it("sends guests to the login page from the account button", () => {
    renderHeader(null);
    expect(screen.getByRole("link", { name: "Contul meu" })).toHaveAttribute("href", "/login");
  });

  it("sends logged-in users to their account", () => {
    renderHeader({ id: "1", email: "ana@example.com" });
    expect(screen.getByRole("link", { name: "Contul meu" })).toHaveAttribute("href", "/account");
  });
});
