const priceFormatters = new Map<string, Intl.NumberFormat>();

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
