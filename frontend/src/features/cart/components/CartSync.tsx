import { useCartSync } from "../hooks";

/** Mounted once in the layout; merges the guest cart into the account after login. */
export function CartSync() {
  useCartSync();
  return null;
}
