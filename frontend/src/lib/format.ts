const priceFormatters = new Map<string, Intl.NumberFormat>();

/** Convert a RON amount (decimal string or number) into integer minor units (bani) to avoid float drift. */
export function toBani(value: string | number): number {
  return Math.round(Number(value) * 100);
}

/** Convert integer minor units (bani) back to a 2-decimal RON number. */
export function fromBani(bani: number): number {
  return bani / 100;
}

/** Multiply a unit price by an integer quantity using exact integer bani arithmetic. */
export function multiplyPrice(unitPrice: string | number, quantity: number): number {
  return fromBani(toBani(unitPrice) * quantity);
}

/** Prices come from the API as decimal strings (e.g. "1890.00"), always in RON. */
export function formatPrice(value: string | number, locale = "ro-RO"): string {
  let formatter = priceFormatters.get(locale);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, {
      style: "currency",
      currency: "RON",
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    });
    priceFormatters.set(locale, formatter);
  }
  return formatter.format(typeof value === "string" ? Number(value) : value);
}
