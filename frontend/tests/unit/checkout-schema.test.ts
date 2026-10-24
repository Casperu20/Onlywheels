import { checkoutSchema } from "@/features/checkout/schema";

const valid = {
  delivery_method: "courier",
  email: "ana@example.com",
  full_name: "Ana Pop",
  phone: "0712 345 678",
  line1: "Str. Exemplu 1",
  city: "Cluj-Napoca",
  county: "Cluj",
  postal_code: "400000",
  save_address: true,
  accept_terms: true,
};

describe("checkoutSchema", () => {
  it("accepts a valid form", () => {
    expect(checkoutSchema.safeParse(valid).success).toBe(true);
  });

  it.each([
    ["postal_code", "4000", "validation.postalCode"],
    ["phone", "abc", "validation.phone"],
    ["email", "nope", "validation.email"],
    ["accept_terms", false, "validation.acceptTerms"],
  ])("rejects invalid %s", (field, value, message) => {
    const result = checkoutSchema.safeParse({ ...valid, [field]: value });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe(message);
  });
});
