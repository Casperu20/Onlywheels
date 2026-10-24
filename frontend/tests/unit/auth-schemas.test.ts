import { loginSchema, registerSchema, safeNextPath } from "@/features/auth/schemas";

describe("loginSchema", () => {
  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe("validation.email");
  });

  it("trims the email", () => {
    const result = loginSchema.parse({ email: "  ana@example.com ", password: "x" });
    expect(result.email).toBe("ana@example.com");
  });
});

describe("registerSchema", () => {
  const valid = { email: "ana@example.com", password: "Str0ng-Pass", confirmPassword: "Str0ng-Pass" };

  it("accepts matching passwords", () => {
    expect(registerSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects mismatched passwords on confirmPassword", () => {
    const result = registerSchema.safeParse({ ...valid, confirmPassword: "other" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["confirmPassword"]);
  });

  it("rejects short passwords", () => {
    const result = registerSchema.safeParse({ ...valid, password: "short", confirmPassword: "short" });
    expect(result.error?.issues.some((i) => i.message === "validation.passwordMin")).toBe(true);
  });
});

describe("safeNextPath", () => {
  it.each([
    [null, "/account"],
    ["/cart", "/cart"],
    ["/catalog?x=1", "/catalog?x=1"],
    ["https://evil.example", "/account"],
    ["//evil.example", "/account"],
    ["/\\evil.example", "/account"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});
