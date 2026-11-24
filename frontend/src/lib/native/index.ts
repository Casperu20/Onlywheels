/** Native platform integrations are exposed here so app features do not import Capacitor directly. */
export { pickPhoto } from "./camera";
export {
  clearNativeTokens,
  getNativeTokens,
  isNativePlatform,
  resetNativeTokenCacheForTests,
  setNativeTokens,
  type AuthTokens,
} from "./auth-storage";
export {
  getNativeFakePaymentPath,
  handleCheckoutDeepLink,
  openCheckoutSuccessLink,
  openNativeCheckout,
  parseCheckoutSuccessUrl,
  registerDeepLinkListener,
  startCheckoutNavigation,
} from "./deep-links";
export { requestPushPermission } from "./push";
export { share } from "./share";
export { storage } from "./storage";
