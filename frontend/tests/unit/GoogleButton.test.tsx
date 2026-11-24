import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "@/features/auth/api";
import { GoogleButton } from "@/features/auth/components/GoogleButton";
import { OrDivider } from "@/features/auth/components/LoginForm";
import i18n from "@/i18n";

const mocks = vi.hoisted(() => ({
  isNativePlatform: vi.fn(),
}));

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: mocks.isNativePlatform },
}));

describe("Google Sign-In native guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    document.head.querySelectorAll('script[src*="accounts.google.com/gsi/client"]').forEach((el) => el.remove());
  });

  it("hides GoogleButton and OrDivider on native even when VITE_GOOGLE_CLIENT_ID is set", () => {
    mocks.isNativePlatform.mockReturnValue(true);

    const { container } = render(
      <>
        <OrDivider />
        <GoogleButton onCredential={vi.fn()} />
      </>,
    );

    expect(container).toBeEmptyDOMElement();
    expect(document.head.querySelector('script[src*="accounts.google.com/gsi/client"]')).toBeNull();
  });

  it("renders OrDivider and GoogleButton on web when VITE_GOOGLE_CLIENT_ID is set", () => {
    mocks.isNativePlatform.mockReturnValue(false);

    const { container } = render(
      <>
        <OrDivider />
        <GoogleButton onCredential={vi.fn()} />
      </>,
    );

    expect(screen.getByText(i18n.t("auth.or"))).toBeInTheDocument();
    expect(container.querySelector(".min-h-11")).not.toBeNull();
  });

  it("rejects authApi.google calls on native platforms", async () => {
    mocks.isNativePlatform.mockReturnValue(true);

    await expect(authApi.google("fake-credential")).rejects.toThrow(/not available/i);
  });
});
