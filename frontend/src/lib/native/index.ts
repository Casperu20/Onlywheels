/**
 * Native adapters: the rest of the app imports only from here, never from Capacitor directly.
 * Today every adapter uses Web APIs. In phase 3 (Android) each function checks
 * `Capacitor.isNativePlatform()` and calls the matching plugin instead
 * (@capacitor/camera, @capacitor/share, @capacitor/push-notifications, @capacitor/preferences).
 */
export { pickPhoto } from "./camera";
export { requestPushPermission } from "./push";
export { share } from "./share";
export { storage } from "./storage";
