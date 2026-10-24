import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { PrivacySection, type User } from "@/features/auth";

const baseUser: User = {
  id: "1",
  email: "ana@example.com",
  first_name: "Ana",
  last_name: "",
  phone: "",
  preferred_language: "ro",
  date_joined: "2025-01-01T00:00:00Z",
  has_password: true,
};

function renderSection(user: User) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <PrivacySection user={user} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PrivacySection", () => {
  it("asks for the password before deleting a normal account", async () => {
    renderSection(baseUser);
    await userEvent.click(screen.getByRole("button", { name: /Șterge contul/ }));

    const field = screen.getByLabelText("Parolă");
    expect(field).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Șterge definitiv" })).toBeDisabled();
    await userEvent.type(field, "secret");
    expect(screen.getByRole("button", { name: "Șterge definitiv" })).toBeEnabled();
  });

  it("asks Google-only users to type their email", async () => {
    renderSection({ ...baseUser, has_password: false });
    await userEvent.click(screen.getByRole("button", { name: /Șterge contul/ }));

    expect(screen.getByLabelText("Scrie adresa de email pentru confirmare")).toHaveAttribute("type", "email");
  });
});
