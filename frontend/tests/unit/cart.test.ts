import type { Variant } from "@/features/catalog/api";
import { fromGuest, summarize } from "@/features/cart/hooks";
import { useGuestCart, type GuestLine } from "@/features/cart/store";

const variant = { id: "v1", price: "250.00", available: 8 } as Variant;
const line = (quantity: number, variantId = "v1"): GuestLine => ({
  variantId,
  quantity,
  product: { id: "p1", slug: "bbs-ch-r", name: "CH-R", type: "wheel", brand: "BBS" },
  variant: { ...variant, id: variantId },
});

describe("guest cart store", () => {
  beforeEach(() => useGuestCart.getState().clear());

  it("merges the same variant and caps the quantity", () => {
    const { add } = useGuestCart.getState();
    add(line(4));
    add(line(18));
    const { lines } = useGuestCart.getState();
    expect(lines).toHaveLength(1);
    expect(lines[0].quantity).toBe(20);
  });

  it("updates and removes lines", () => {
    const store = useGuestCart.getState();
    store.add(line(4));
    store.add(line(1, "v2"));
    store.setQuantity("v1", 2);
    store.remove("v2");
    expect(useGuestCart.getState().lines.map((l) => [l.variantId, l.quantity])).toEqual([["v1", 2]]);
  });
});

describe("summarize", () => {
  it("adds up subtotal and pieces", () => {
    expect(summarize(fromGuest([line(4), line(2, "v2")]))).toEqual({ subtotal: 1500, count: 6 });
  });
});
