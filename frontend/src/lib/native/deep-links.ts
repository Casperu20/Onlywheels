import { App } from "@capacitor/app";
import { AppLauncher } from "@capacitor/app-launcher";

import { isNativePlatform } from "./auth-storage";

const ORDER_NUMBER_PATTERN = /^[A-Z0-9-]{1,32}$/i;
const SUCCESS_SCHEME = "onlywheels:";
const SUCCESS_HOST = "checkout";

export function parseCheckoutSuccessUrl(rawUrl: string): string | null {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return null;
  }

  const orders = url.searchParams.getAll("order");
  const orderNumber = orders[0];
  if (
    url.protocol !== SUCCESS_SCHEME ||
    url.hostname !== SUCCESS_HOST ||
    url.pathname !== "/success" ||
    url.port ||
    url.username ||
    url.password ||
    url.hash ||
    orders.length !== 1 ||
    !orderNumber ||
    !ORDER_NUMBER_PATTERN.test(orderNumber)
  ) {
    return null;
  }

  return `/checkout/success?order=${encodeURIComponent(orderNumber)}`;
}

export function handleCheckoutDeepLink(url: string, navigate: (path: string) => void): void {
  const path = parseCheckoutSuccessUrl(url);
  if (path) navigate(path);
}

export async function registerDeepLinkListener(
  navigate: (path: string) => void,
): Promise<() => Promise<void>> {
  if (!isNativePlatform()) return async () => undefined;

  const listener = await App.addListener("appUrlOpen", ({ url }) => handleCheckoutDeepLink(url, navigate));
  try {
    const launch = await App.getLaunchUrl();
    if (launch?.url) handleCheckoutDeepLink(launch.url, navigate);
  } catch (error) {
    await listener.remove();
    throw error;
  }
  return () => listener.remove();
}

export function getNativeFakePaymentPath(checkoutUrl: string, orderNumber: string): string | null {
  if (!ORDER_NUMBER_PATTERN.test(orderNumber)) {
    throw new Error("The checkout response contains an invalid order number.");
  }
  const url = new URL(checkoutUrl);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
    throw new Error("The checkout response contains an invalid payment URL.");
  }
  if (url.pathname !== "/checkout/fake-pay") return null;

  const orders = url.searchParams.getAll("order");
  if (orders.length !== 1 || orders[0] !== orderNumber) {
    throw new Error("The fake checkout URL does not match the created order.");
  }
  return `/checkout/fake-pay?order=${encodeURIComponent(orderNumber)}`;
}

export async function openNativeCheckout(checkoutUrl: string): Promise<void> {
  if (!isNativePlatform()) throw new Error("External checkout can only be opened from the native app.");
  const url = new URL(checkoutUrl);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
    throw new Error("The checkout response contains an invalid payment URL.");
  }
  await AppLauncher.openUrl({ url: checkoutUrl });
}

export async function openCheckoutSuccessLink(orderNumber: string): Promise<void> {
  if (!isNativePlatform()) throw new Error("Checkout return links can only be opened from the native app.");
  if (!ORDER_NUMBER_PATTERN.test(orderNumber)) {
    throw new Error("Cannot open a checkout return link for an invalid order number.");
  }
  await AppLauncher.openUrl({
    url: `${SUCCESS_SCHEME}//${SUCCESS_HOST}/success?order=${encodeURIComponent(orderNumber)}`,
  });
}
